"""Bounded GLB 2.0 preflight with accessor/buffer integrity checks.

No mesh is copied, converted or modified. glTF nodes may carry transforms;
accessor coordinates here are LOCAL bounds, not a world-space car bounding box.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import re
import struct

MAX_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_GEOMETRY_VERTICES = 4_000_000
_MAX_NODES = 100_000


class InvalidModel(ValueError):
    """Fail-closed when the file is incomplete, unsupported or structurally invalid."""


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_accessor(g: dict, idx: int, views: list, buffers: list, bin_length: int):
    if not isinstance(idx, int) or idx < 0 or idx >= len(g.get("accessors", [])):
        raise InvalidModel("Mesh references invalid accessor")
    acc = g["accessors"][idx]
    if "sparse" in acc:
        raise InvalidModel("Sparse position/index accessors require a Blender-only import; unsupported in preflight")
    view_idx = acc.get("bufferView")
    if not isinstance(view_idx, int) or view_idx < 0 or view_idx >= len(views):
        raise InvalidModel("Accessor missing or invalid bufferView")
    view = views[view_idx]
    if not isinstance(view.get("buffer"), int) or view["buffer"] != 0 or len(buffers) != 1:
        raise InvalidModel("GLB external buffers or invalid buffer references are unsupported")
    v_start = view.get("byteOffset", 0)
    v_len = view.get("byteLength")
    if not isinstance(v_start, int) or not isinstance(v_len, int) or v_start < 0 or v_len < 0 or v_start + v_len > bin_length:
        raise InvalidModel("bufferView exceeds GLB BIN chunk")
    a_offset = acc.get("byteOffset", 0)
    count = acc.get("count")
    typ = acc.get("type")
    ctype = acc.get("componentType")
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}.get(typ)
    component_size = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}.get(ctype)
    if components is None or component_size is None or not isinstance(count, int) or count < 1 or count > MAX_GEOMETRY_VERTICES:
        raise InvalidModel("Invalid accessor metadata")
    item_size = component_size * components
    stride = view.get("byteStride", item_size)
    if not isinstance(stride, int) or stride < item_size or stride > 252 or (stride % component_size):
        raise InvalidModel("Invalid accessor stride")
    if not isinstance(a_offset, int) or a_offset < 0 or (a_offset % component_size):
        raise InvalidModel("Invalid accessor byteOffset")
    last_byte = a_offset + (count - 1) * stride + item_size
    if last_byte > v_len:
        raise InvalidModel("Accessor exceeds declared bufferView")
    return acc


def _finite_bounds(acc):
    minimum, maximum = acc.get("min"), acc.get("max")
    if minimum is None and maximum is None:
        return None
    if not isinstance(minimum, list) or not isinstance(maximum, list) or len(minimum) != 3 or len(maximum) != 3:
        raise InvalidModel("Invalid POSITION accessor bounds")
    if any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in minimum + maximum):
        raise InvalidModel("Nonfinite POSITION bounds")
    if any(a > b for a, b in zip(minimum, maximum)):
        raise InvalidModel("Inverted POSITION bounds")
    return {"min": minimum, "max": maximum}


def inspect_glb(path: str | Path) -> dict:
    p = Path(path).expanduser().resolve(strict=True)
    if not p.is_file() or p.suffix.lower() != ".glb":
        raise InvalidModel("Select a .glb file (other formats not yet enabled)")
    if not 32 <= p.stat().st_size <= MAX_BYTES:
        raise InvalidModel("GLB outside 32 byte-512 MiB safety limit")
    with p.open("rb") as f:
        magic, version, size = struct.unpack("<4sII", f.read(12))
        if magic != b"glTF" or version != 2 or size != p.stat().st_size:
            raise InvalidModel("Invalid GLB 2.0 header or declared size")
        chunks = []
        while f.tell() < size:
            header = f.read(8)
            if len(header) != 8:
                raise InvalidModel("Truncated GLB chunk header")
            length, ctype = struct.unpack("<II", header)
            if length % 4 or length > size - f.tell():
                raise InvalidModel("Invalid GLB chunk size")
            pos = f.tell()
            chunks.append((ctype, pos, length))
            f.seek(length, 1)
        if not chunks or chunks[0][0] != 0x4E4F534A or chunks[0][2] > MAX_JSON_BYTES:
            raise InvalidModel("GLB JSON missing or too large")
        if len(chunks) > 2 or (len(chunks) == 2 and chunks[1][0] != 0x004E4942):
            raise InvalidModel("Unexpected GLB chunk ordering")
        f.seek(chunks[0][1])
        try:
            g = json.loads(f.read(chunks[0][2]).decode("utf-8").rstrip(" \t\r\n\0"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidModel("Invalid GLB JSON") from exc
    if g.get("asset", {}).get("version") != "2.0":
        raise InvalidModel("GLB asset version must be 2.0")
    for key in ("meshes", "nodes", "accessors", "bufferViews", "buffers"):
        if not isinstance(g.get(key, []), list):
            raise InvalidModel(f"Invalid {key} array")
    if len(g.get("nodes", [])) > _MAX_NODES:
        raise InvalidModel("Too many nodes")
    buffers = g.get("buffers", [])
    bin_length = chunks[1][2] if len(chunks) > 1 else 0
    if len(buffers) != 1 or "uri" in buffers[0]:
        raise InvalidModel("Only single embedded BIN buffer GLBs supported")
    if not isinstance(buffers[0].get("byteLength"), int) or not 0 <= bin_length - buffers[0]["byteLength"] <= 3:
        raise InvalidModel("GLB BIN size mismatch")
    views = g.get("bufferViews", [])
    vertices = 0
    triangles = 0
    mesh_primitive_count = 0
    bounds_known = 0
    warnings = []
    all_names = []
    for mesh in g.get("meshes", []):
        all_names.append(str(mesh.get("name", "")))
        for pr in mesh.get("primitives", []):
            if "extensions" in pr and "KHR_draco_mesh_compression" in pr["extensions"]:
                raise InvalidModel("Draco-compressed GLB: geometry cannot be verified by this preflight")
            pos_idx = pr.get("attributes", {}).get("POSITION")
            acc = _check_accessor(g, pos_idx, views, buffers, bin_length)
            if acc.get("componentType") != 5126 or acc.get("type") != "VEC3":
                raise InvalidModel("POSITION accessor must be FLOAT VEC3")
            vertices += acc["count"]
            bounds_known += int(_finite_bounds(acc) is not None)
            mesh_primitive_count += 1
            mode = pr.get("mode", 4)
            if mode != 4:
                raise InvalidModel(f"Only indexed triangle meshes (mode=4) supported, got {mode}")
            if "indices" not in pr:
                raise InvalidModel("Nonindexed triangle primitive not supported for game staging")
            indices = _check_accessor(g, pr["indices"], views, buffers, bin_length)
            if indices["type"] != "SCALAR" or indices["componentType"] not in (5121, 5123, 5125) or indices["count"] % 3:
                raise InvalidModel("Invalid triangle indices")
            triangles += indices["count"] // 3
    if not vertices or not triangles or vertices > MAX_GEOMETRY_VERTICES:
        raise InvalidModel("Empty or oversized geometry")
    if bounds_known != mesh_primitive_count:
        warnings.append("Some POSITION bounds absent: Blender must calculate actual world-space bounds")
    if len(g.get("nodes", [])) > 500 or mesh_primitive_count > 300:
        warnings.append("High object count: game draw-call optimization required")
    if triangles > 100_000:
        warnings.append("High triangle count: create LODs before VR runtime deployment")
    extras = g.get("asset", {}).get("extras", {})
    if not isinstance(extras, dict):
        extras = {}
    names = " ".join(all_names[:5000])
    if re.search(r"crew.?recycl|forza|ripp?ed|csr.?2|from.?game", names, re.IGNORECASE):
        warnings.append("Asset names suggest possible third-party game provenance; verify underlying rights")
    license_claim = str(extras.get("license", ""))[:500]
    if license_claim:
        warnings.append("Embedded license metadata is a claim, not verified ownership or game-porting permission")
    return {
        "status": "PREFLIGHT_PASS_NOT_GAME_READY",
        "file_name": p.name,
        "sha256": file_hash(p),
        "size_bytes": p.stat().st_size,
        "meshes": len(g["meshes"]),
        "primitives": mesh_primitive_count,
        "nodes": len(g.get("nodes", [])),
        "vertices": vertices,
        "triangles": triangles,
        "materials": len(g.get("materials", [])),
        "images": len(g.get("images", [])),
        "textures": len(g.get("textures", [])),
        "license_claim_unverified": license_claim,
        "author_claim_unverified": str(extras.get("author", ""))[:500],
        "source_claim_unverified": str(extras.get("source", ""))[:1000],
        "warnings": warnings,
        "game_installable": False,
    }