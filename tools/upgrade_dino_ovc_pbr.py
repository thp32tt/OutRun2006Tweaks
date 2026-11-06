#!/usr/bin/env python3
"""Upgrade a Dino HQ OVC2 sidecar to backward-compatible OVC3 PBR sidecar.

Read-only OVC2 input; emits a new file (never overwrites input).
Material JSON: {"materials":[{"index":0,"roughness":0.65,"metallic":0.0,
                                "normalScale":1.0,"normal":"seat_normal.png",
                                "orm":"seat_orm.png"}]}
Normal textures use tangent-space XYZ RGB. ORM uses AO/Roughness/Metallic RGB.
Maps can be DDS (BC1/BC3/BGRA32) or PNG (Pillow required; output BGRA32+mips).
OVC3 keeps the original OVC2 mesh/UV/index/albedo binary unmodified.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path

MAX_FILE = 128 * 1024 * 1024
MAX_GPU = 112 * 1024 * 1024
MAX_DIM = 2048


def u32(b: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(b):
        raise ValueError("truncated OVC")
    return struct.unpack_from("<I", b, off)[0]


def validate_dds(data: bytes) -> None:
    if len(data) < 128 or data[:4] != b"DDS " or u32(data, 4) != 124 or u32(data, 76) != 32:
        raise ValueError("unsupported DDS header")
    height, width, levels = u32(data, 12), u32(data, 16), u32(data, 28)
    if not width or not height or max(width, height) > MAX_DIM or (
        width & (width - 1)) or (height & (height - 1)):
        raise ValueError("DDS dimensions must be powers of two <=2048")
    if not 1 <= levels <= max(width, height).bit_length():
        raise ValueError("invalid DDS mip count")
    fourcc = data[84:88]
    if fourcc == b"DXT1":
        block = 8
    elif fourcc == b"DXT5":
        block = 16
    elif (u32(data, 84) == 0 and u32(data, 88) == 32 and
          tuple(u32(data, i) for i in (92, 96, 100, 104)) ==
          (0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000)):
        block = 0
    else:
        raise ValueError("unsupported DDS format")
    expected = 128
    for level in range(levels):
        w = max(width >> level, 1)
        h = max(height >> level, 1)
        expected += (((w + 3) // 4) * ((h + 3) // 4) * block
                     if block else w * h * 4)
    if expected != len(data):
        raise ValueError("DDS mip payload/trailing data mismatch")


def png_to_dds(path: Path) -> bytes:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("PNG requires Pillow; use DDS or install Pillow") from exc
    with Image.open(path) as source:
        image = source.convert("RGBA")
    width, height = image.size
    if not width or not height or max(width, height) > MAX_DIM or (
        width & (width - 1)) or (height & (height - 1)):
        raise ValueError("PNG dimensions must be powers of two <=2048")
    levels = max(width, height).bit_length()
    dds = bytearray(128)
    dds[:4] = b"DDS "
    for offset, value in ((4,124),(8,0x2100F),(12,height),(16,width),
                          (20,width*4),(28,levels),(76,32),(80,0x41),(88,32),
                          (92,0x00ff0000),(96,0x0000ff00),(100,0x000000ff),
                          (104,0xff000000),(108,0x401008)):
        struct.pack_into("<I",dds,offset,value)
    for _ in range(levels):
        dds.extend(image.tobytes("raw","BGRA"))
        if image.width == 1 and image.height == 1:
            continue
        image = image.resize((max(1,image.width//2),max(1,image.height//2)),
                             Image.Resampling.BILINEAR)
    return bytes(dds)


def load_map(root: Path, name: str | None) -> bytes:
    if not name:
        return b""
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError("material texture is missing or escapes the manifest directory")
    if target.suffix.lower() == ".png":
        result = png_to_dds(target)
    elif target.suffix.lower() == ".dds":
        result = target.read_bytes()
    else:
        raise ValueError("material texture must be PNG or DDS")
    validate_dds(result)
    return result


def validate_base_ovc2(data: bytes) -> tuple[int, int]:
    if not 36 <= len(data) <= MAX_FILE or data[:8] != b"OVRCABH2" or u32(data,8) != 2:
        raise ValueError("input must be an OVC2 file")
    groups, materials = u32(data,12), u32(data,16)
    if not 1 <= groups <= 512 or not 1 <= materials <= 64:
        raise ValueError("invalid group/material count")
    if u32(data,28) != len(data)-36 or u32(data,32) != zlib.crc32(data[36:]):
        raise ValueError("input header/CRC mismatch")
    pos = 36
    gpu = 0
    for _ in range(groups):
        if pos + 16 > len(data):
            raise ValueError("truncated group")
        name_len, material, count, indices, index_size = struct.unpack_from("<HHIII",data,pos)
        pos += 16
        if not 1 <= name_len <= 256 or material >= materials or (
            index_size not in (2,4)) or count < 3 or indices < 3 or indices % 3:
            raise ValueError("invalid group")
        payload = name_len + count*32 + indices*index_size
        gpu += count*32 + indices*index_size
        pos += payload
        if pos > len(data) or gpu > MAX_GPU:
            raise ValueError("group bounds/budget")
    for _ in range(materials):
        length = u32(data,pos)
        pos += 4
        if pos+length > len(data):
            raise ValueError("truncated albedo")
        validate_dds(data[pos:pos+length])
        gpu += length
        pos += length
    if pos != len(data) or gpu > MAX_GPU:
        raise ValueError("OVC2 trailing bytes/budget")
    return materials, gpu


def upgrade(input_bytes: bytes, manifest: dict, root: Path) -> bytes:
    materials, gpu = validate_base_ovc2(input_bytes)
    entries = manifest.get("materials")
    if not isinstance(entries,list):
        raise ValueError("manifest must contain materials array")
    per_material = {}
    for entry in entries:
        if not isinstance(entry,dict) or type(entry.get("index")) is not int:
            raise ValueError("material index must be an integer")
        i = entry["index"]
        if i < 0 or i >= materials or i in per_material:
            raise ValueError("material index out of range or repeated")
        per_material[i] = entry
    body = bytearray(input_bytes[36:])
    body.extend(b"OVCPBR3!")
    for i in range(materials):
        entry = per_material.get(i,{})
        # glTF-style packed ORM masks store the actual per-pixel metal and
        # roughness values. Their material factors must default to 1.0;
        # otherwise the former 0.04 metallic default quietly turned even
        # 100%-metal ORM pixels into dielectrics.
        has_orm = bool(entry.get("orm"))
        factors = tuple(float(entry.get(k,d)) for k,d in (
            ("roughness",1.0 if has_orm else 0.75),
            ("metallic",1.0 if has_orm else 0.0),
            ("normalScale",1.0)))
        if not (math.isfinite(factors[0]) and 0.04 <= factors[0] <= 1 and
                math.isfinite(factors[1]) and 0 <= factors[1] <= 1 and
                math.isfinite(factors[2]) and 0 <= factors[2] <= 2):
            raise ValueError("invalid material factors")
        body.extend(struct.pack("<3f",*factors))
        for key in ("normal","orm"):
            data = load_map(root,entry.get(key))
            gpu += len(data)
            if gpu > MAX_GPU:
                raise ValueError("OVC3 GPU payload budget exceeded")
            body.extend(struct.pack("<I",len(data)))
            body.extend(data)
    if len(body)+36 > MAX_FILE:
        raise ValueError("OVC3 file budget exceeded")
    header = bytearray(input_bytes[:36])
    header[:8] = b"OVRCABH3"
    struct.pack_into("<I",header,8,3)
    struct.pack_into("<I",header,28,len(body))
    struct.pack_into("<I",header,32,zlib.crc32(body))
    return bytes(header)+bytes(body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-ovc",type=Path,required=True)
    parser.add_argument("--materials-json",type=Path,required=True)
    parser.add_argument("--output-ovc",type=Path,required=True)
    args = parser.parse_args()
    if args.input_ovc.resolve() == args.output_ovc.resolve():
        parser.error("input/output must differ; original asset must not be overwritten")
    manifest_path = args.materials_json.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = upgrade(args.input_ovc.read_bytes(),manifest,manifest_path.parent)
    args.output_ovc.parent.mkdir(parents=True,exist_ok=True)
    # Stage then publish, never expose partially written OVC.
    staging = args.output_ovc.with_suffix(args.output_ovc.suffix+".pending")
    staging.write_bytes(output)
    staging.replace(args.output_ovc)
    print(json.dumps({"format":"OVC3","output":str(args.output_ovc),
                      "bytes":len(output),"crc32":f"{zlib.crc32(output[36:]):08x}"}))


if __name__=="__main__":
    main()
