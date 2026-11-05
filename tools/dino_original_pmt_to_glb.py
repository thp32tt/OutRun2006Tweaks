#!/usr/bin/env python3
"""Dino/OutRun 2006 PC .sz PMT -> standalone glTF 2.0 GLB preview.

Read-only input. Preserves original per-object geometry, topology and UVs.
Upsampling textures is NOT AI reconstruction and does not add missing details.
This preview exporter does not replace the R26 .ovc runtime sidecar.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageFilter

MAX_PMT_BYTES = 128 * 1024 * 1024
MAX_VERTEX_BYTES = 64 * 1024 * 1024
MAX_TEXTURE_SIDE = 4096


def u16(data, off):
    if off < 0 or off + 2 > len(data):
        raise ValueError("u16 out of bounds")
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    if off < 0 or off + 4 > len(data):
        raise ValueError("u32 out of bounds")
    return struct.unpack_from("<I", data, off)[0]


def i32(data, off):
    if off < 0 or off + 4 > len(data):
        raise ValueError("i32 out of bounds")
    return struct.unpack_from("<i", data, off)[0]


def bounds(data, off, length):
    if off < 0 or length < 0 or off + length > len(data):
        raise ValueError("PMT segment out of bounds")
    return off


def unpack(data, fmt, off):
    bounds(data, off, struct.calcsize(fmt))
    return struct.unpack_from(fmt, data, off)


def open_pmt(path):
    raw = path.read_bytes()
    if raw[:2] not in (bytes((0x78,0x9c)), bytes((0x78,0xda)), bytes((0x78,0x01))):
        raise ValueError("expected zlib-compressed .sz")
    d = zlib.decompress(raw, max_length=MAX_PMT_BYTES) if hasattr(zlib, "max_length") else zlib.decompress(raw)
    if len(d) > MAX_PMT_BYTES:
        raise ValueError("expanded PMT exceeds budget")
    obj_count, tex_count, syslen, vidlen = unpack(d, "<4I", 0)
    if obj_count > 4096 or tex_count > 4096 or syslen + vidlen + 16 != len(d):
        raise ValueError("invalid PMT header")
    system, video = d[16:16 + syslen], d[16 + syslen:]
    if u32(system, 4) != obj_count or u32(system, 8) != tex_count:
        raise ValueError("PMT counts disagree")
    xpr_off = 24 + 60 * obj_count + 4 * (tex_count + 1)
    if system[xpr_off:xpr_off + 4] != b"XPR0":
        raise ValueError("missing XPR0")
    data_size = u32(system, xpr_off + 4) - u32(system, xpr_off + 8)
    offsets = [u32(system, xpr_off + 12 + 20 * i + 4) for i in range(tex_count)]
    if any(off > data_size for off in offsets):
        raise ValueError("invalid XPR texture offset")
    return {"obj_count": obj_count, "tex_count": tex_count,
            "system": system, "video": video, "offsets": offsets,
            "data_size": data_size}


def decode_dds(asset, index, scale):
    off = asset["offsets"][index]
    next_offsets = [q for q in asset["offsets"] if q > off]
    end = min(next_offsets) if next_offsets else asset["data_size"]
    if end <= off or asset["video"][off:off + 4] != b"DDS ":
        raise ValueError("texture %s not a DDS" % index)
    data = asset["video"][off:end]
    with Image.open(io.BytesIO(data)) as dds:
        dds.load()
        img = dds.convert("RGBA")
    w, h = img.size
    if not w or not h or w > MAX_TEXTURE_SIDE or h > MAX_TEXTURE_SIDE:
        raise ValueError("unsupported DDS image dimensions")
    if scale > 1:
        if w * scale > MAX_TEXTURE_SIDE or h * scale > MAX_TEXTURE_SIDE:
            raise ValueError("upsampled texture exceeds max size")
        img = img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=65, threshold=3))
    p = io.BytesIO()
    img.save(p, "PNG", optimize=True)
    return p.getvalue(), [w, h], list(img.size)


def triangulate(raw, topology):
    out = []
    def emit(a, b, c):
        if a != b and b != c and a != c:
            out.extend((a, b, c))
    if topology == 5:
        for i in range(0, len(raw), 3):
            emit(*raw[i:i + 3])
    elif topology == 6:
        for i in range(len(raw) - 2):
            a, b, c = raw[i:i + 3]
            emit(b, a, c) if i % 2 else emit(a, b, c)
    elif topology == 8:
        for i in range(0, len(raw), 4):
            a, b, c, d = raw[i:i + 4]
            emit(a, b, c)
            emit(a, c, d)
    else:
        raise ValueError("unsupported primitive topology %s" % topology)
    return out


def decode_object(asset, oi):
    sys, vid = asset["system"], asset["video"]
    if oi < 0 or oi >= asset["obj_count"]:
        raise ValueError("object index out of range")
    q = unpack(sys, "<15I", 24 + oi * 60)
    h = unpack(sys, "<13I", q[5])
    fmts = []
    for j in range(h[9]):
        fs = unpack(sys, "<11I", q[12] + j * 44)
        stream, vf, stride, shader = fs[0], fs[8], fs[9], fs[10]
        if stream != 1 or shader != 0 or (vf, stride) not in ((0x12, 24), (0x112, 32)):
            raise ValueError("unsupported Dino FVF/stride/shader: %s" % ((stream, vf, stride, shader),))
        ip = u32(sys, q[1] + j * 4)
        ixoff = u32(sys, ip + 4)
        vp = u32(sys, q[2] + j * 16)
        voff = u32(sys, vp + 4)
        bounds(sys, ixoff, fs[6])
        bounds(vid, voff, fs[7])
        if fs[7] > MAX_VERTEX_BYTES or fs[7] % stride or fs[6] % 2:
            raise ValueError("invalid format buffers")
        fmts.append((vf, stride, ixoff, voff, fs[6] // 2, fs[7] // stride))
    result = []
    if (q[10] - q[9]) % 20 or q[10] < q[9]:
        raise ValueError("invalid vertex group table")
    for gi, goff in enumerate(range(q[9], q[10], 20)):
        fidx, first0, first1, count0, count1 = unpack(sys, "<5I", goff)
        if fidx >= len(fmts):
            raise ValueError("invalid format index")
        vf, stride, ixoff, voff, nic, nvert = fmts[fidx]
        for alpha, first, count in ((0, first0, count0), (1, first1, count1)):
            if count and first + count > h[10]:
                raise ValueError("invalid material group interval")
            for mgi in range(first, first + count):
                mg = unpack(sys, "<8I", q[10] + mgi * 32)
                base, mat, prstart, prcount = mg[:4]
                if mat >= h[11]:
                    raise ValueError("invalid material index")
                global_ids = []
                for pj in range(prcount):
                    pr = unpack(sys, "<4I", q[11] + (prstart + pj) * 16)
                    top, istart, icount = pr[0], pr[1], pr[2]
                    n = icount * 3 if top == 5 else icount + 2 if top == 6 else icount * 4 if top == 8 else 0
                    if n <= 0 or istart + n > nic:
                        raise ValueError("invalid primitive index interval")
                    ids = [base + u16(sys, ixoff + 2 * (istart + i)) for i in range(n)]
                    if any(v >= nvert for v in ids):
                        raise ValueError("primitive index exceeds vertices")
                    global_ids.extend(triangulate(ids, top))
                if not global_ids:
                    continue
                mapping = {}
                positions, normals, uvs, indices = [], [], [], []
                for old in global_ids:
                    if old not in mapping:
                        off = voff + old * stride
                        v = unpack(vid, "<6f", off)
                        if not all(math.isfinite(x) and abs(x) <= 10000 for x in v):
                            raise ValueError("invalid vertex float")
                        pos, norm = v[:3], v[3:6]
                        uv = unpack(vid, "<2f", off + 24) if vf == 0x112 else (0., 0.)
                        if not all(math.isfinite(x) and abs(x) <= 10000 for x in uv):
                            raise ValueError("invalid UV")
                        mapping[old] = len(positions)
                        positions.append(tuple(pos))
                        normals.append(tuple(norm))
                        uvs.append(tuple(uv))
                    indices.append(mapping[old])
                moff = q[13] + mat * 88
                tex_index = i32(sys, moff + 24)
                if tex_index < 0 or tex_index >= asset["tex_count"]:
                    tex_index = None
                colorid = i32(sys, moff)
                c = unpack(sys, "<4f", q[14] + 72 * colorid) if 0 <= colorid < h[12] else (1., 1., 1., 1.)
                if not all(math.isfinite(x) for x in c):
                    c = (1., 1., 1., 1.)
                result.append({
                    "name": "object%02d_group%02d_material%03d_a%d" % (oi, gi, mgi, alpha),
                    "object": oi, "group": gi, "material_group": mgi,
                    "tex_index": tex_index, "color": [min(1, max(0, float(x))) for x in c],
                    "alpha": alpha, "vertices": positions, "normals": normals,
                    "uvs": uvs, "indices": indices
                })
    return result


class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.views = []
        self.accessors = []

    def append(self, data, target=None):
        self.bin.extend(bytes((-len(self.bin)) % 4))
        off = len(self.bin)
        self.bin.extend(data)
        view = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            view["target"] = target
        self.views.append(view)
        return len(self.views) - 1

    def accessor(self, view, count, typ, component=5126, lo=None, hi=None):
        item = {"bufferView": view, "componentType": component,
                "count": count, "type": typ}
        if lo is not None:
            item["min"] = lo
            item["max"] = hi
        self.accessors.append(item)
        return len(self.accessors) - 1


def build_glb(asset, parts, scale, output):
    buf = Glb()
    meshes, nodes, materials, imgs, texs = [], [], [], [], []
    tex_cache = {}
    notes = []
    for p in parts:
        ti = p["tex_index"]
        material = {"name": p["name"] + "_pbr", "doubleSided": True,
                    "pbrMetallicRoughness": {
                       "baseColorFactor": p["color"], "metallicFactor": 0.04,
                       "roughnessFactor": 0.78
                    }}
        if ti is not None:
            if ti not in tex_cache:
                try:
                    png, original, after = decode_dds(asset, ti, scale)
                    v = buf.append(png)
                    img = len(imgs)
                    imgs.append({"name": "original_dds_%02d_%dx%d_to_%dx%d" %
                                 (ti, *original, *after), "mimeType": "image/png",
                                 "bufferView": v})
                    tex_cache[ti] = len(texs)
                    texs.append({"source": img})
                except Exception as exc:
                    tex_cache[ti] = None
                    notes.append("DDS %s: %s" % (ti, exc))
            if tex_cache[ti] is not None:
                material["pbrMetallicRoughness"]["baseColorTexture"] = {
                    "index": tex_cache[ti]
                }
        materials.append(material)
        pos = p["vertices"]
        lo = [min(row[i] for row in pos) for i in range(3)]
        hi = [max(row[i] for row in pos) for i in range(3)]
        def fblock(rows, fmt):
            return b"".join(struct.pack(fmt, *r) for r in rows)
        apos = buf.accessor(buf.append(fblock(pos, "<3f"), 34962), len(pos), "VEC3", lo=lo, hi=hi)
        anor = buf.accessor(buf.append(fblock(p["normals"], "<3f"), 34962), len(pos), "VEC3")
        auv = buf.accessor(buf.append(fblock(p["uvs"], "<2f"), 34962), len(pos), "VEC2")
        face = p["indices"]
        aid = buf.accessor(buf.append(fblock(((x,) for x in face), "<I"), 34963),
                           len(face), "SCALAR", component=5125, lo=[min(face)], hi=[max(face)])
        meshes.append({"name": p["name"], "primitives": [{
            "attributes": {"POSITION": apos, "NORMAL": anor, "TEXCOORD_0": auv},
            "indices": aid, "material": len(materials) - 1, "mode": 4
        }]})
        nodes.append({"name": p["name"], "mesh": len(meshes) - 1})
    gltf = {
      "asset": {"version": "2.0", "generator": "OutRun PC PMT original Dino preview v1"},
      "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}],
      "nodes": nodes, "meshes": meshes, "accessors": buf.accessors,
      "bufferViews": buf.views, "buffers": [{"byteLength": len(buf.bin)}],
      "materials": materials, "images": imgs, "textures": texs,
      "extras": {"note": "Original PMT geometry. 2x texture interpolation is not added art detail.",
                 "runtime": "GLB preview only, not R26 OVC loader compatible"}
    }
    j = json.dumps(gltf, separators=(",", ":"), ensure_ascii=True).encode()
    j += b" " * (-len(j) % 4)
    b = bytes(buf.bin)
    b += bytes(-len(b) % 4)
    header = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(j) + 8 + len(b))
    output.write_bytes(header + struct.pack("<I4s", len(j), b"JSON") + j +
                       struct.pack("<I4s", len(b), b"BIN" + bytes((0,))) + b)
    return {"sourceObjects": sorted(set(p["object"] for p in parts)),
            "meshes": len(meshes), "vertices": sum(len(p["vertices"]) for p in parts),
            "triangles": sum(len(p["indices"]) // 3 for p in parts),
            "textures": len(imgs), "imageNotes": notes, "bytes": output.stat().st_size}


def main():
    pa = argparse.ArgumentParser(description=__doc__)
    pa.add_argument("--game-dir", type=Path, required=True)
    pa.add_argument("--asset", choices=("obj_plcar_dino_pmt.sz", "obj_rc_dino_pmt.sz",
                                        "obj_plcar_dino_t_pmt.sz", "obj_rc_dino_t_pmt.sz"),
                    default="obj_plcar_dino_pmt.sz")
    pa.add_argument("--object", type=int, default=0,
                    help="PMT object number, not a cockpit semantic selector")
    pa.add_argument("--texture-scale", type=int, choices=(1, 2), default=2)
    pa.add_argument("--output-dir", type=Path, required=True)
    ar = pa.parse_args()
    p = ar.game_dir / "Cars" / ar.asset
    if not p.is_file():
        pa.error("not found: " + str(p))
    asset = open_pmt(p)
    parts = decode_object(asset, ar.object)
    if not parts:
        pa.error("object has no static geometry")
    ar.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "Dino246_%s_object%02d_TEX%dx" % (
        "PLCAR" if "plcar" in ar.asset else "RC", ar.object, ar.texture_scale)
    output = ar.output_dir / (stem + ".glb")
    stats = build_glb(asset, parts, ar.texture_scale, output)
    report = {"source": p.name, "inputBytes": p.stat().st_size,
              "originalUnmodified": True, "objectCount": asset["obj_count"],
              "textureCount": asset["tex_count"], "object": ar.object,
              "textureScale": ar.texture_scale, "results": stats,
              "warnings": ["Not a VR-ready R26 .ovc file",
                           "Object identity and transform must be checked against real car",
                           "Upscale does not recover missing original texture detail"]}
    (ar.output_dir / (stem + ".json")).write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
