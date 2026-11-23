#!/usr/bin/env python3
"""Fail-closed, offline provenance and conversion quality gate for four exact Ferraris.

No network access, paid downloads, asset redistribution, or game-file changes.
Evidence remains owner-private. PASS is a static source/metadata gate only,
not proof of physical likeness, legal rights, or headset performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from urllib.parse import urlparse

from verify_all_car_ovc import inspect, pbr_map_coverage

# Retail slot 6 uses Testarossa, but a promoted external Spider is the
# specific 1986 Agnelli open-top body, NOT a renamed production coupe.
EXACT = {
    5: ("575 Superamerica", "revolving-roof"),
    6: ("Testarossa Spider", "open-top-one-off-1986"),
    8: ("328 GTS", "removable-targa"),
    28: ("F430 Spider", "convertible-soft-top"),
}
SHA = re.compile(r"^[0-9a-f]{64}$")
PNG = b"\x89PNG\r\n\x1a\n"


class GateError(ValueError):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise GateError(why)


def https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    u = urlparse(value)
    return u.scheme == "https" and bool(u.netloc) and not u.username and not u.password


def evidence_file(root: Path, item: object, suffixes: tuple[str, ...]) -> Path:
    require(isinstance(item, dict), "missing evidence file object")
    relative, digest = item.get("path"), item.get("sha256")
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(),
            "invalid private relative evidence path")
    require(isinstance(digest, str) and bool(SHA.fullmatch(digest)),
            "missing/invalid private evidence SHA256")
    path = root / relative
    # Reject symlink escapes and paths outside the private evidence root.
    require(path.resolve().is_relative_to(root.resolve()), "evidence path escapes root")
    require(not path.is_symlink() and path.is_file(), "missing or symlink evidence file")
    require(path.suffix.lower() in suffixes, "evidence file type mismatch")
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    require(h.hexdigest() == digest, "evidence SHA256 mismatch: " + relative)
    return path


def image_dimensions(data: bytes) -> tuple[int, int]:
    if data.startswith(PNG):
        require(len(data) >= 24 and data[12:16] == b"IHDR", "invalid PNG header")
        w, h = struct.unpack_from(">II", data, 16)
        require(0 < w <= 16384 and 0 < h <= 16384, "invalid PNG dimensions")
        return w, h
    if data.startswith(b"\xff\xd8"):
        at = 2
        while at + 4 <= len(data):
            require(data[at] == 0xff, "invalid JPEG marker")
            while at < len(data) and data[at] == 0xff:
                at += 1
            require(at < len(data), "truncated JPEG marker")
            marker = data[at]
            at += 1
            if marker in (0xd8, 0xd9, 0x01) or 0xd0 <= marker <= 0xd7:
                continue
            require(at + 2 <= len(data), "truncated JPEG segment")
            length = struct.unpack_from(">H", data, at)[0]
            require(length >= 2 and at + length <= len(data), "JPEG segment bounds")
            if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb):
                require(length >= 7, "JPEG SOF short")
                h, w = struct.unpack_from(">HH", data, at + 3)
                require(0 < w <= 16384 and 0 < h <= 16384, "invalid JPEG dimensions")
                return w, h
            at += length
    raise GateError("unsupported/malformed embedded image (PNG/JPEG required)")


def glb_stats(path: Path) -> dict:
    with path.open("rb") as f:
        header = f.read(20)
        require(len(header) == 20, "GLB header truncated")
        magic, version, length, json_bytes, chunk_type = struct.unpack("<4s4I", header)
        require(magic == b"glTF" and version == 2 and
                length == path.stat().st_size and
                chunk_type == 0x4e4f534a and 0 < json_bytes <= 8 * 1024 * 1024,
                "GLB v2 / JSON chunk header")
        doc = json.loads(f.read(json_bytes))
        f.seek(12 + 8 + json_bytes)
        chunk = f.read(8)
        require(len(chunk) == 8, "GLB embedded BIN missing")
        bin_length, bin_type = struct.unpack("<2I", chunk)
        require(bin_type == 0x004e4942 and
                12 + 8 + json_bytes + 8 + bin_length == length,
                "GLB embedded BIN bounds")
        # Only the embedded texture portions are read. No full GLB is uploaded.
        bin_base = f.tell()
        buffers = doc.get("buffers", [])
        require(len(buffers) == 1 and not buffers[0].get("uri") and
                buffers[0].get("byteLength", -1) <= bin_length,
                "GLB external buffers unsupported")
        accessors = doc.get("accessors", [])
        triangles = 0
        for mesh in doc.get("meshes", []):
            for p in mesh.get("primitives", []):
                require(p.get("mode", 4) == 4, "non-triangle GLB primitive")
                attributes = p.get("attributes", {})
                require(all(k in attributes for k in ("POSITION", "NORMAL", "TEXCOORD_0")),
                        "GLB missing position/normal/UV attributes")
                a = p.get("indices", attributes["POSITION"])
                require(isinstance(a, int) and 0 <= a < len(accessors),
                        "GLB primitive accessor")
                count = accessors[a].get("count", -1)
                require(isinstance(count, int) and count > 0 and count % 3 == 0,
                        "GLB triangle index count")
                triangles += count // 3
        require(triangles > 0, "GLB contains no mesh triangles")
        images = {}
        for img in doc.get("images", []):
            name = img.get("name")
            idx = img.get("bufferView")
            views = doc.get("bufferViews", [])
            require(isinstance(name, str) and name and name not in images,
                    "GLB embedded texture names must be unique")
            require(isinstance(idx, int) and 0 <= idx < len(views),
                    "GLB texture must be embedded")
            view = views[idx]
            start, count = view.get("byteOffset", 0), view.get("byteLength", -1)
            require(isinstance(start, int) and isinstance(count, int) and
                    start >= 0 and 0 < count <= 32 * 1024 * 1024 and
                    start + count <= buffers[0]["byteLength"],
                    "GLB image bufferView bounds")
            f.seek(bin_base + start)
            images[name] = image_dimensions(f.read(count))
        require(images, "GLB has no named embedded textures")
        return {"triangles": triangles, "textures": images}


def validate_one(entry: dict, root: Path) -> dict:
    cid = entry.get("car_id")
    require(cid in EXACT, "unexpected Ferrari slot ID")
    expected, roof = EXACT[cid]
    require(entry.get("variant") == expected and entry.get("roof") == roof,
            "wrong exact body/roof variant for slot")
    require(https_url(entry.get("vehicle_reference_url")) and
            https_url(entry.get("asset_provenance_url")),
            "missing independent vehicle/source provenance HTTPS URLs")
    require(entry.get("authorized_use") == "PRIVATE_MODDING_DOCUMENTED",
            "model usage rights not documented")
    require(entry.get("redistribution_allowed") is False,
            "public asset shipping is prohibited by this private gate")
    if cid == 6:
        require(entry.get("one_off_chassis") == "62897",
                "Testarossa Spider one-off chassis evidence missing")
    checks = entry.get("manual_review", {})
    require(isinstance(checks, dict) and all(checks.get(k) is True for k in (
        "body_variant", "interior", "four_wheels", "materials_uv",
        "normal_orm", "side_by_side_preview")),
        "mandatory visual/quality review missing")
    evidence_file(root, entry.get("rights_record"), (".txt", ".pdf", ".md"))
    evidence_file(root, entry.get("source_preview"), (".png", ".jpg", ".jpeg"))
    evidence_file(root, entry.get("converted_preview"), (".png", ".jpg", ".jpeg"))
    source = evidence_file(root, entry.get("source_glb"), (".glb",))
    converted = evidence_file(root, entry.get("converted_glb"), (".glb",))
    final = evidence_file(root, entry.get("ovc4"), (".ovc",))
    a, b = glb_stats(source), glb_stats(converted)
    require(a["triangles"] == b["triangles"],
            "source-to-converted GLB triangle loss/decimation")
    require(set(a["textures"]) == set(b["textures"]),
            "source-to-converted GLB embedded texture loss/renaming")
    for name, (width, height) in a["textures"].items():
        w2, h2 = b["textures"][name]
        require(w2 >= width and h2 >= height,
                "silent texture downscale: " + name)
    o = inspect(final)
    require(o["version"] == 4 and o["triangles"] == b["triangles"],
            "OVC4 missing / triangle decimation or non-equivalent mesh")
    require(pbr_map_coverage(o) and o["zero_normal_vertices"] == 0,
            "OVC4 opaque material PBR/normal coverage failed")
    return {"id": cid, "variant": expected, "status": "PASS_STATIC_SOURCE_ONLY",
            "glb_triangles": a["triangles"], "ovc_sha256": o["ovc_sha256"],
            "source_texture_dimensions": a["textures"]}


def audit_manifest(manifest: Path) -> list[dict]:
    document = json.loads(manifest.read_text(encoding="utf-8"))
    require(document.get("schema_version") == 1 and
            isinstance(document.get("cars"), list),
            "invalid source manifest schema")
    entries = document["cars"]
    require(all(isinstance(e, dict) for e in entries), "invalid car records")
    ids = [e.get("car_id") for e in entries]
    require(len(ids) == len(set(ids)) and set(ids) <= set(EXACT),
            "duplicate/unsupported car slot in quality manifest")
    by_id = {e["car_id"]: e for e in entries}
    rows = []
    for cid, (variant, _) in EXACT.items():
        if cid not in by_id:
            rows.append({"id": cid, "variant": variant, "status": "BLOCKED",
                         "reason": "private licensed exact-variant record missing"})
            continue
        try:
            rows.append(validate_one(by_id[cid], manifest.parent))
        except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
            rows.append({"id": cid, "variant": variant, "status": "BLOCKED",
                         "reason": str(exc)})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        rows = audit_manifest(args.manifest)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("FERRARI16_EXACT_VARIANT_GATE_BLOCKED:", str(exc))
        return 2
    if args.json_out:
        args.json_out.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    for row in rows:
        print(f"{row['id']:02d} {row['variant']:<20} {row['status']}"
              + (f": {row['reason']}" if "reason" in row else ""))
    return 0 if all(row["status"] == "PASS_STATIC_SOURCE_ONLY" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
