from __future__ import annotations

# Runtime asset semantic inventory derived from the original mod's documented
# XST / XMT / PMT layouts in docs/file_formats. No game asset is modified.
import argparse
import gzip
import json
import struct
from pathlib import Path

MAX_OBJECTS = 4096
MAX_TABLE = 1_000_000


def _u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise ValueError(f"u32 OOB @{off:#x}")
    return struct.unpack_from("<I", data, off)[0]


def _i32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise ValueError(f"i32 OOB @{off:#x}")
    return struct.unpack_from("<i", data, off)[0]


def _f32(data: bytes, off: int) -> float:
    if off < 0 or off + 4 > len(data):
        raise ValueError(f"f32 OOB @{off:#x}")
    return struct.unpack_from("<f", data, off)[0]


def _valid(data: bytes, off: int, size: int) -> bool:
    return 0 <= off <= len(data) and 0 <= size <= len(data) - off


def _vertex_format(word: int) -> dict:
    xyz_type = (word >> 1) & 0x7
    return {
        "raw": word,
        "xyz_type": xyz_type,
        "xyzrhw": xyz_type == 2,
        "normal": bool(word & (1 << 4)),
        "diffuse": bool(word & (1 << 5)),
        "specular": bool(word & (1 << 6)),
        "tex_count": (word >> 8) & 0xF,
    }


def _mat_attr(word: int) -> dict:
    return {
        "raw": word,
        "specular": bool(word & 0x1),
        "double_side": bool(word & 0x2),
        "double_side_lighting": bool(word & 0x4),
        "z_bias": bool(word & 0x8),
        "no_fog": bool(word & 0x10),
        "src_blend": (word >> 8) & 0xF,
        "dst_blend": (word >> 12) & 0xF,
        "blend_op": (word >> 16) & 0x7,
        "pixelshader": (word >> 19) & 0xF,
        "z_bias_value": (word >> 23) & 0xF,
        "ftype": (word >> 27) & 0x3,
    }


def _tex_attr(word: int) -> dict:
    flags = word & 0x3FF
    return {
        "raw": word,
        "specular_map": bool(flags & 0x1),
        "envmap_lighting": bool(flags & 0x2),
        "envmap_sphere": bool(flags & 0x4),
        "envmap_cube": bool(flags & 0x8),
        "volume": bool(flags & 0x10),
        "bump_sphere": bool(flags & 0x20),
        "projection": bool(flags & 0x40),
        "fresnel": bool(flags & 0x80),
        "addr_u": (word >> 10) & 0x7,
        "addr_v": (word >> 13) & 0x7,
        "filter": (word >> 16) & 0x7,
        "mipmap": (word >> 19) & 0x3,
        "blend": (word >> 21) & 0x1F,
        "alpha_blend": (word >> 26) & 0x3,
        "coord_index": (word >> 28) & 0xF,
    }


def _read_file(path: Path) -> bytes:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def parse_xst(data: bytes, source: str = "<memory>") -> dict:
    base = 0
    if len(data) >= 8:
        sysmem, vidmem = struct.unpack_from("<II", data, 0)
        if sysmem + vidmem + 8 == len(data):
            base = 8
    if not _valid(data, base, 32):
        raise ValueError("XST header too small")

    flag, tex_ofs, nb_tex, dummy, nb_dsptbl, dsptbl, nb_scrtbl, scrtbl =         struct.unpack_from("<8I", data, base)
    if max(nb_tex, nb_dsptbl, nb_scrtbl) > MAX_TABLE:
        raise ValueError("XST unreasonable counts")

    displays = []
    if _valid(data, base + dsptbl, nb_dsptbl * 8):
        for i in range(nb_dsptbl):
            count, rel = struct.unpack_from("<II", data, base + dsptbl + i * 8)
            items = []
            if count < 100000 and _valid(data, base + rel, count * 16):
                for j in range(min(count, 4096)):
                    scr_idx, sx, sy, rot, flip, scale = struct.unpack_from(
                        "<IHHHHf", data, base + rel + j * 16)
                    items.append({
                        "scr_idx": scr_idx, "sx": sx, "sy": sy,
                        "rot": rot, "flip": flip, "scale": scale,
                    })
            displays.append({"index": i, "count": count, "offset": rel, "items": items})

    sprites = []
    if _valid(data, base + scrtbl, nb_scrtbl * 28):
        for i in range(min(nb_scrtbl, 200000)):
            spr_idx, su, sv, eu, ev, sx, sy, ex, ey = struct.unpack_from(
                "<IffffHHHH", data, base + scrtbl + i * 28)
            sprites.append({
                "index": i, "spr_idx": spr_idx,
                "uv": [su, sv, eu, ev], "rect": [sx, sy, ex, ey],
            })

    return {
        "format": "XST", "source": str(source), "base_offset": base,
        "flag": flag, "texture_count": nb_tex,
        "display_table_count": nb_dsptbl, "sprite_count": nb_scrtbl,
        "display_tables": displays, "sprites": sprites,
    }


def _object_header(data: bytes, pos: int) -> dict:
    if not _valid(data, pos, 52):
        raise ValueError("object header OOB")
    values = struct.unpack_from("<13I", data, pos)
    keys = [
        "offset_cull_nodes", "offset_matrices", "offset_models",
        "offset_vtx_groups", "offset_mat_groups", "offset_primitives",
        "offset_vtx_formats", "offset_materials", "offset_mat_colors",
        "num_vtx_formats", "num_mat_groups", "num_materials",
        "num_mat_colors",
    ]
    return dict(zip(keys, values))


def _vertex_formats(data: bytes, base: int, header: dict) -> list:
    result = []
    pos = base + header["offset_vtx_formats"]
    for index in range(min(header["num_vtx_formats"], 16384)):
        off = pos + index * 44
        if not _valid(data, off, 44):
            break
        values = struct.unpack_from("<11I", data, off)
        result.append({
            "index": index,
            "num_stream": values[0],
            "index_buffer_size": values[6],
            "vertex_buffer_size": values[7],
            "vertex_format": _vertex_format(values[8]),
            "vertex_stride": values[9],
            "vertex_shader_type": values[10],
        })
    return result


def _materials(data: bytes, base: int, header: dict) -> list:
    result = []
    pos = base + header["offset_materials"]
    for index in range(min(header["num_materials"], 16384)):
        off = pos + index * 88
        if not _valid(data, off, 88):
            break
        attr = _mat_attr(_u32(data, off + 4))
        textures = []
        for slot in range(4):
            toff = off + 8 + slot * 20
            textures.append({
                "slot": slot,
                "attrib": _tex_attr(_u32(data, toff)),
                "blendcolor": _u32(data, toff + 4),
                "mipmap_bias": _f32(data, toff + 8),
                "bump_depth": _f32(data, toff + 12),
                "texture_index": _i32(data, toff + 16),
            })

        tags = []
        if attr["double_side"]:
            tags.append("DOUBLE_SIDED")
        if attr["z_bias"]:
            tags.append("Z_BIAS")
        if attr["no_fog"]:
            tags.append("NO_FOG")
        if any(x["attrib"]["envmap_cube"] for x in textures):
            tags.append("CUBEMAP")
        if any(x["attrib"]["envmap_sphere"] for x in textures):
            tags.append("SPHEREMAP")
        if any(x["attrib"]["projection"] for x in textures):
            tags.append("PROJECTION")
        if any(x["attrib"]["fresnel"] for x in textures):
            tags.append("FRESNEL")

        result.append({
            "index": index, "color_index": _u32(data, off),
            "attrib": attr, "textures": textures, "semantic_tags": tags,
        })
    return result


def _cstring(data: bytes, off: int, max_len: int = 512) -> str:
    if not _valid(data, off, 1):
        return ""
    end = data.find(b"\0", off, min(len(data), off + max_len))
    if end < 0:
        end = min(len(data), off + max_len)
    return data[off:end].decode("utf-8", "replace")


def parse_xmt(data: bytes, source: str = "<memory>") -> dict:
    if not _valid(data, 0, 16):
        raise ValueError("XMT header too small")
    flag, model_count, data_table, name_table = struct.unpack_from("<4I", data, 0)
    if model_count == 0 or model_count > MAX_OBJECTS:
        raise ValueError("XMT unreasonable model count")
    if not _valid(data, data_table, model_count * 4) or             not _valid(data, name_table, model_count * 4):
        raise ValueError("XMT tables OOB")

    objects = []
    for index in range(model_count):
        obj_pos = _u32(data, data_table + index * 4)
        name_pos = _u32(data, name_table + index * 4)
        if not _valid(data, obj_pos, 52):
            continue
        header = _object_header(data, obj_pos)
        objects.append({
            "index": index, "name": _cstring(data, name_pos),
            "offset": obj_pos, "header": header,
            "vertex_formats": _vertex_formats(data, obj_pos, header),
            "materials": _materials(data, obj_pos, header),
        })

    return {
        "format": "XMT", "source": str(source), "flag": flag,
        "model_count": model_count, "objects": objects,
    }


def parse_pmt(data: bytes, source: str = "<memory>") -> dict:
    if not _valid(data, 0, 40):
        raise ValueError("PMT header too small")
    _, _, sysmem, vidmem = struct.unpack_from("<4I", data, 0)
    xmt_pos = 16
    _, object_count, texture_count, _, _, _ = struct.unpack_from(
        "<6I", data, xmt_pos)
    if object_count == 0 or object_count > MAX_OBJECTS:
        raise ValueError("PMT unreasonable object count")

    objects = []
    raw_pos = xmt_pos + 24
    for index in range(object_count):
        off = raw_pos + index * 60
        if not _valid(data, off, 60):
            break
        values = struct.unpack_from("<15I", data, off)
        header_pos = xmt_pos + values[6]
        if not _valid(data, header_pos, 52):
            continue
        header = _object_header(data, header_pos)
        # C2C PMT section offsets are relative to the XMT block, not the
        # ObjectHeader itself.
        objects.append({
            "index": index, "offset": off,
            "object_header_offset": header_pos, "header": header,
            "vertex_formats": _vertex_formats(data, xmt_pos, header),
            "materials": _materials(data, xmt_pos, header),
        })

    return {
        "format": "PMT", "source": str(source),
        "object_count": object_count, "texture_count": texture_count,
        "sysmem_size": sysmem, "vidmem_size": vidmem, "objects": objects,
    }


def _summary(entry: dict) -> dict:
    if entry["format"] == "XST":
        return {
            "format": "XST", "sprites": entry["sprite_count"],
            "textures": entry["texture_count"],
        }
    objects = entry.get("objects", [])
    formats = [v for obj in objects for v in obj.get("vertex_formats", [])]
    materials = [m for obj in objects for m in obj.get("materials", [])]
    tags = {}
    for material in materials:
        for tag in material.get("semantic_tags", []):
            tags[tag] = tags.get(tag, 0) + 1
    return {
        "format": entry["format"], "objects": len(objects),
        "vertex_formats": len(formats),
        "xyzrhw_formats": sum(
            1 for value in formats if value["vertex_format"]["xyzrhw"]),
        "materials": len(materials), "material_tags": tags,
    }


def _parse_path(path: Path) -> dict:
    data = _read_file(path)
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".xst":
        return parse_xst(data, str(path))
    if suffix == ".pmt":
        return parse_pmt(data, str(path))
    if suffix == ".xmt" or name == "mdl.bin":
        return parse_xmt(data, str(path))
    raise ValueError("unsupported asset extension")


def scan(root: Path, max_files: int = 5000) -> dict:
    max_files = max(0, max_files)
    candidates = []
    discovered_candidates = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if path.suffix.lower() in {".xst", ".pmt", ".xmt"} or name == "mdl.bin":
            discovered_candidates += 1
            if len(candidates) < max_files:
                candidates.append(path)

    truncated = discovered_candidates > len(candidates)
    results, errors = [], []
    for path in candidates:
        try:
            entry = _parse_path(path)
            results.append({
                "path": str(path.relative_to(root)),
                "summary": _summary(entry),
                "detail": entry,
            })
        except Exception as exc:
            errors.append({
                "path": str(path.relative_to(root)), "error": str(exc),
            })

    if errors:
        status = "PARTIAL" if results else "FAILED"
    elif truncated:
        status = "PARTIAL"
    else:
        status = "COMPLETE"

    return {
        "schema": "outrun-vr-asset-semantics-v2",
        "root": str(root),
        "status": status,
        "discovered_candidates": discovered_candidates,
        "files_scanned": len(candidates),
        "truncated": truncated,
        "parse_error_count": len(errors),
        "max_files": max_files,
        "results": results,
        "errors": errors,
    }


def _test_xst() -> bytes:
    data = bytearray(256)
    struct.pack_into("<8I", data, 0, 1, 200, 1, 0, 1, 32, 1, 64)
    struct.pack_into("<II", data, 32, 1, 128)
    struct.pack_into("<IHHHHf", data, 128, 7, 10, 20, 0, 0, 1.0)
    struct.pack_into("<IffffHHHH", data, 64, 3, 0.0, 0.0, 1.0, 1.0,
                     1, 2, 31, 42)
    return bytes(data)


def _test_xmt() -> bytes:
    data = bytearray(1024)
    data_table, name_table, obj, name = 32, 36, 64, 900
    struct.pack_into("<4I", data, 0, 0x1234, 1, data_table, name_table)
    struct.pack_into("<I", data, data_table, obj)
    struct.pack_into("<I", data, name_table, name)
    data[name:name + 5] = b"test\0"
    struct.pack_into("<13I", data, obj,
                     52, 52, 52, 52, 52, 52, 52, 96, 184, 1, 0, 1, 0)
    struct.pack_into("<11I", data, obj + 52,
                     1, 0, 0, 0, 0, 0, 12, 120, (2 << 1), 20, 0)
    struct.pack_into("<II", data, obj + 96, 0, 0x2)
    for slot in range(4):
        attr = 0x40 if slot == 0 else 0
        struct.pack_into("<IIffi", data, obj + 104 + slot * 20,
                         attr, 0, 0.0, 0.0, slot)
    return bytes(data)


def _test_pmt() -> bytes:
    data = bytearray(1024)
    struct.pack_into("<4I", data, 0, 1, 0, 800, 200)
    xmt = 16
    struct.pack_into("<6I", data, xmt, 0, 1, 0, 0, 0, 0)
    raw = xmt + 24
    header_rel = 128
    struct.pack_into("<15I", data, raw,
                     0, 0, 0, 0, 0, header_rel, header_rel,
                     0, 0, 0, 0, 0, 180, 224, 312)
    header = xmt + header_rel
    struct.pack_into("<13I", data, header,
                     0, 0, 0, 0, 0, 0, 180, 224, 312, 1, 0, 1, 0)
    struct.pack_into("<11I", data, xmt + 180,
                     1, 0, 0, 0, 0, 0, 12, 120, (1 << 1), 20, 3)
    struct.pack_into("<II", data, xmt + 224, 0, 0x8)
    for slot in range(4):
        attr = 0x8 if slot == 0 else 0
        struct.pack_into("<IIffi", data, xmt + 232 + slot * 20,
                         attr, 0, 0.0, 0.0, slot)
    return bytes(data)


def self_test() -> None:
    xst = parse_xst(_test_xst())
    assert xst["sprite_count"] == 1 and xst["sprites"][0]["spr_idx"] == 3

    xmt = parse_xmt(_test_xmt())
    assert xmt["objects"][0]["vertex_formats"][0]["vertex_format"]["xyzrhw"]
    assert "PROJECTION" in xmt["objects"][0]["materials"][0]["semantic_tags"]

    pmt = parse_pmt(_test_pmt())
    assert pmt["objects"][0]["vertex_formats"][0]["vertex_shader_type"] == 3
    assert "CUBEMAP" in pmt["objects"][0]["materials"][0]["semantic_tags"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an OutRun XST/PMT/XMT semantic inventory for VR diagnostics.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="VR_ASSET_SEMANTICS.json")
    parser.add_argument("--max-files", type=int, default=5000)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        if not args.quiet:
            print("asset semantic parser self-test: OK")
        return 0

    report = scan(Path(args.root), args.max_files)
    Path(args.output).write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if not args.quiet:
        print(
            f"wrote {args.output}: status={report['status']}, "
            f"{len(report['results'])} parsed, {report['parse_error_count']} errors, "
            f"{report['files_scanned']}/{report['discovered_candidates']} scanned")
    if report["status"] == "COMPLETE":
        return 0
    if report["status"] == "PARTIAL":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
