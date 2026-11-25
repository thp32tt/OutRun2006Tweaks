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
import math
import re
import struct
from collections import Counter
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


def material_number(value: object, label: str, bounded: bool = True) -> float:
    require(type(value) in (int, float) and math.isfinite(value) and
            (not bounded or 0 <= value <= 1), "GLB invalid material factor: " + label)
    return float(value)


def material_vector(value: object, length: int, label: str) -> tuple:
    require(isinstance(value, list) and len(value) == length,
            "GLB invalid material factor: " + label)
    return tuple(material_number(x, label) for x in value)


def sampler_signature(doc: dict, texture: dict) -> tuple:
    # glTF defaults to REPEAT wrapping. Omitted filters are implementation
    # choices, not aliases for a particular explicitly requested filter.
    sampler = {}
    if "sampler" in texture:
        idx = texture["sampler"]
        samplers = doc.get("samplers", [])
        require(type(idx) is int and 0 <= idx < len(samplers),
                "GLB sampler reference")
        sampler = samplers[idx]
        require(isinstance(sampler, dict), "GLB sampler object")
    wrap_s, wrap_t = sampler.get("wrapS", 10497), sampler.get("wrapT", 10497)
    mag, minify = sampler.get("magFilter"), sampler.get("minFilter")
    for value in (wrap_s, wrap_t):
        require(type(value) is int and value in (33071, 33648, 10497),
                "GLB sampler wrap")
    for key, value, allowed in (
            ("magFilter", mag, (9728, 9729)),
            ("minFilter", minify, (9728, 9729, 9984, 9985, 9986, 9987))):
        require(key not in sampler or (type(value) is int and value in allowed),
                "GLB sampler filter")
    return wrap_s, wrap_t, mag, minify


def material_binding(doc: dict, primitive: dict) -> tuple:
    """Resolve actual used texture roles, not the inventory of embedded images.

    The OVC vertex ABI has one UV pair. Unsupported UV sets/transforms need
    explicit baking evidence; this offline gate cannot certify them.
    """
    materials = doc.get("materials", [])
    textures = doc.get("textures", [])
    images = doc.get("images", [])
    index = primitive.get("material")
    require(type(index) is int and 0 <= index < len(materials),
            "GLB primitive material reference")
    material = materials[index]
    alpha = material.get("alphaMode", "OPAQUE")
    require(alpha in ("OPAQUE", "MASK", "BLEND"), "GLB material alpha mode")
    # The native OVC draw path disables ALPHATESTENABLE and only has
    # opaque and tagged source-over passes. Do not certify cutout loss.
    require(alpha != "MASK", "GLB alpha MASK unsupported by OVC draw passes")
    pbr = material.get("pbrMetallicRoughness", {})
    roles = (
        ("albedo", pbr.get("baseColorTexture")),
        ("normal", material.get("normalTexture")),
        ("metallic_roughness", pbr.get("metallicRoughnessTexture")),
        ("occlusion", material.get("occlusionTexture")),
        ("emissive", material.get("emissiveTexture")),
    )
    # Texture inventory and role names alone miss scalar/color edits. Compare
    # the effective core material parameters (explicit defaults == omitted).
    double_sided = material.get("doubleSided", False)
    require(type(double_sided) is bool, "GLB invalid material doubleSided")
    factors = (
        material_vector(pbr.get("baseColorFactor", [1, 1, 1, 1]), 4, "baseColor"),
        material_number(pbr.get("metallicFactor", 1), "metallic"),
        material_number(pbr.get("roughnessFactor", 1), "roughness"),
        material_vector(material.get("emissiveFactor", [0, 0, 0]), 3, "emissive"),
        double_sided,
    )
    bindings = [("factors", factors)]
    for role, info in roles:
        if info is None:
            require(alpha == "BLEND" or role not in ("normal", "metallic_roughness"),
                    "GLB opaque material missing " + role + " binding")
            bindings.append((role, None))
            continue
        require(isinstance(info, dict), "GLB texture info: " + role)
        uv = info.get("texCoord", 0)
        require(type(uv) is int and uv == 0 and
                "TEXCOORD_0" in primitive.get("attributes", {}) and
                "KHR_texture_transform" not in info.get("extensions", {}),
                "GLB unsupported texture UV mapping: " + role)
        texture_index = info.get("index")
        require(type(texture_index) is int and 0 <= texture_index < len(textures),
                "GLB texture reference: " + role)
        texture = textures[texture_index]
        image_index = texture.get("source")
        require(type(image_index) is int and 0 <= image_index < len(images) and
                not texture.get("extensions"),
                "GLB texture image reference: " + role)
        name = images[image_index].get("name")
        require(isinstance(name, str) and bool(name), "GLB texture image name")
        strength = None
        if role == "normal":
            strength = material_number(info.get("scale", 1), "normal scale", False)
        elif role == "occlusion":
            strength = material_number(info.get("strength", 1), "occlusion strength")
        bindings.append((role, name, strength, sampler_signature(doc, texture)))
    return alpha, tuple(bindings)


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
                type(buffers[0].get("byteLength")) is int and
                0 < buffers[0]["byteLength"] <= bin_length,
                "GLB external buffers unsupported")
        buffer_bytes = buffers[0]["byteLength"]
        views = doc.get("bufferViews", [])
        accessors = doc.get("accessors", [])

        def view_bounds(idx: object) -> tuple[dict, int, int]:
            require(type(idx) is int and 0 <= idx < len(views),
                    "GLB bufferView reference")
            view = views[idx]
            start, count = view.get("byteOffset", 0), view.get("byteLength", -1)
            require(type(view.get("buffer")) is int and view["buffer"] == 0 and
                    type(start) is int and type(count) is int and
                    start >= 0 and count > 0 and start + count <= buffer_bytes,
                    "GLB bufferView bounds")
            return view, start, count

        checked_float_accessors = set()

        def accessor(idx: object, semantic: str) -> tuple[int, int, int, int]:
            require(type(idx) is int and 0 <= idx < len(accessors),
                    "GLB accessor reference: " + semantic)
            a = accessors[idx]
            count, component = a.get("count"), a.get("componentType")
            require(type(count) is int and 0 < count <= 6000000 and
                    type(component) is int and "sparse" not in a,
                    "GLB unsupported accessor: " + semantic)
            normalized = a.get("normalized", False)
            require(type(normalized) is bool, "GLB accessor normalized flag")
            # This offline approval gate supports core, directly backed
            # glTF attributes. Sparse/compressed/quantized geometry must be
            # decoded before approval, not certified from metadata alone.
            if semantic in ("POSITION", "NORMAL"):
                require(a.get("type") == "VEC3" and component == 5126 and
                        not normalized, "GLB attribute format: " + semantic)
                element = 12
            elif semantic == "TEXCOORD_0":
                require(a.get("type") == "VEC2" and
                        ((component == 5126 and not normalized) or
                         (component in (5121, 5123) and normalized)),
                        "GLB attribute format: " + semantic)
                element = {5126: 8, 5121: 2, 5123: 4}[component]
            else:
                require(a.get("type") == "SCALAR" and
                        component in (5121, 5123, 5125) and not normalized,
                        "GLB index format")
                element = {5121: 1, 5123: 2, 5125: 4}[component]
            view, start, size = view_bounds(a.get("bufferView"))
            offset = a.get("byteOffset", 0)
            stride = view.get("byteStride", element)
            alignment = {5121: 1, 5123: 2, 5125: 4, 5126: 4}[component]
            require(type(offset) is int and offset >= 0 and
                    type(stride) is int and element <= stride <= 252 and
                    stride % alignment == 0 and offset % alignment == 0 and
                    (start + offset) % alignment == 0 and
                    offset + (count - 1) * stride + element <= size,
                    "GLB accessor byte bounds: " + semantic)
            if semantic == "indices":
                require("byteStride" not in view, "GLB strided index accessor")
            elif "byteStride" in view:
                require(stride % 4 == 0, "GLB vertex stride alignment")
            # Bounds and matching counts do not establish that vertex values
            # are usable. Check core float attributes in bounded batches,
            # respecting interleaved strides and avoiding repeat shared reads.
            key = (idx, semantic)
            if component == 5126 and key not in checked_float_accessors:
                f.seek(bin_base + start + offset)
                fmt = "<2f" if semantic == "TEXCOORD_0" else "<3f"
                remaining = count
                while remaining:
                    batch = min(remaining, 4096)
                    span = (batch - 1) * stride + element
                    data = f.read(span)
                    require(len(data) == span, "GLB truncated vertex data: " + semantic)
                    for i in range(batch):
                        values = struct.unpack_from(fmt, data, i * stride)
                        require(all(map(math.isfinite, values)),
                                "GLB nonfinite vertex attribute: " + semantic)
                        if semantic == "NORMAL":
                            require(sum(n * n for n in values) > 1e-12,
                                    "GLB zero-length normal")
                    remaining -= batch
                    if remaining:
                        f.seek(stride - element, 1)
                checked_float_accessors.add(key)
            return count, start + offset, component, element
        triangles = 0
        material_triangles = Counter()
        for mesh in doc.get("meshes", []):
            for p in mesh.get("primitives", []):
                require(p.get("mode", 4) == 4, "non-triangle GLB primitive")
                attributes = p.get("attributes", {})
                require(all(k in attributes for k in ("POSITION", "NORMAL", "TEXCOORD_0")),
                        "GLB missing position/normal/UV attributes")
                position_count = accessor(attributes["POSITION"], "POSITION")[0]
                for semantic in ("NORMAL", "TEXCOORD_0"):
                    require(accessor(attributes[semantic], semantic)[0] == position_count,
                            "GLB vertex attribute count mismatch")
                count = position_count
                if "indices" in p:
                    count, start, component, element = accessor(p["indices"], "indices")
                    # Stream index bytes in bounded chunks. A CRC/hash-valid
                    # file can still reference nonexistent vertices.
                    f.seek(bin_base + start)
                    fmt = {5121: "<B", 5123: "<H", 5125: "<I"}[component]
                    remaining = count
                    while remaining:
                        batch = min(remaining, 16384)
                        data = f.read(batch * element)
                        require(len(data) == batch * element and
                                all(i[0] < position_count for i in struct.iter_unpack(fmt, data)),
                                "GLB index out of bounds")
                        remaining -= batch
                require(count % 3 == 0, "GLB triangle index count")
                triangles += count // 3
                material_triangles[material_binding(doc, p)] += count // 3
        require(triangles > 0, "GLB contains no mesh triangles")
        images = {}
        for img in doc.get("images", []):
            name = img.get("name")
            idx = img.get("bufferView")
            require(isinstance(name, str) and name and name not in images,
                    "GLB embedded texture names must be unique")
            view, start, count = view_bounds(idx)
            require(count <= 32 * 1024 * 1024 and "byteStride" not in view,
                    "GLB image bufferView bounds")
            f.seek(bin_base + start)
            images[name] = image_dimensions(f.read(count))
        require(images, "GLB has no named embedded textures")
        return {"triangles": triangles, "textures": images,
                "material_triangles": material_triangles}


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
    require(a["material_triangles"] == b["material_triangles"],
            "source-to-converted GLB material texture binding/triangle mismatch")
    o = inspect(final)
    require(o["version"] == 4 and o["triangles"] == b["triangles"],
            "OVC4 missing / triangle decimation or non-equivalent mesh")
    # OVC runtime chooses blend/depth-write policy from the mesh name,
    # not from the source material. Equal total triangles and PBR counts
    # do not prove that transparent faces survive the conversion.
    blend_triangles = sum(count for (alpha, _), count in
                          b["material_triangles"].items() if alpha == "BLEND")
    require(o["glass_triangles"] == blend_triangles and
            o["opaque_triangles"] == b["triangles"] - blend_triangles,
            "OVC4 alpha draw-pass triangle mismatch")
    require(pbr_map_coverage(o) and o["zero_normal_vertices"] == 0,
            "OVC4 opaque material PBR/normal coverage failed")
    return {"id": cid, "variant": expected, "status": "PASS_STATIC_SOURCE_ONLY",
            "glb_triangles": a["triangles"], "ovc_sha256": o["ovc_sha256"],
            "glass_triangles": o["glass_triangles"],
            "opaque_triangles": o["opaque_triangles"],
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
