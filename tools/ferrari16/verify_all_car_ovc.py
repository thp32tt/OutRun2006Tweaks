#!/usr/bin/env python3
"""Read-only Ferrari16 OVC preflight. No game files are changed or uploaded."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import struct
import tempfile
import zlib
from pathlib import Path
from pbr_material_gate import (uncovered_pbr_materials, triangle_has_pbr_basis,
                               triangle_source_tangent_collapsed)

CARS = (
    (0, "Dino 246 GTS"), (1, "365 GTS/4 Daytona"), (2, "F50"),
    (3, "360 Spider"), (4, "F355 Spider"), (5, "575 Superamerica"),
    (6, "Testarossa"), (7, "288 GTO"), (8, "328 GTS"),
    (9, "250 GTO"), (10, "512 BB"), (11, "F40"),
    (12, "550 Barchetta"), (13, "F430 Coupe"), (14, "Enzo / FX"),
    (28, "F430 Spider"),
)
LEGACY = {7: "288gto.ovc", 11: "f40.ovc"}
MAX_FILE = 128 * 1024 * 1024
MAX_GPU = 112 * 1024 * 1024
# Match the C++ loader's 0.04f, not Python's binary64 literal 0.04.
# A correct float32 DDS/OVC field for 0.04 rounds to 0.03999999910593033.
MIN_ROUGHNESS_F32 = struct.unpack("<f", struct.pack("<f", 0.04))[0]
MAGIC = {b"OVRCAB15": 1, b"OVRCABH2": 2,
         b"OVRCABH3": 3, b"OVRCABH4": 4}


class OvcError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise OvcError(message)


def f32(value: float) -> float:
    """Round a bounded arithmetic result exactly as a float32 field."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


def u16(data: bytes, offset: int) -> int:
    require(offset + 2 <= len(data), "short u16")
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    require(offset + 4 <= len(data), "short u32")
    return struct.unpack_from("<I", data, offset)[0]


def dds_length(data: bytes, offset: int, count: int, legacy: bool) -> int:
    require(count >= 128 and offset + count <= len(data), "DDS bounds")
    d = memoryview(data)[offset:offset + count]
    require(d[:4] == b"DDS " and u32(d, 4) == 124 and u32(d, 76) == 32,
            "DDS signature/headers")
    # Native CreateTexture uploads 2D only; reject cube faces and volumes.
    require(not (u32(d, 112) & 0x0020fe00) and
            not (u32(d, 8) & 0x00800000) and u32(d, 24) <= 1,
            "DDS non-2D resource")
    height, width, mips = u32(d, 12), u32(d, 16), u32(d, 28)
    require(0 < width <= 2048 and 0 < height <= 2048 and
            width & (width - 1) == 0 and height & (height - 1) == 0,
            "DDS dimensions")
    require(1 <= mips <= max(width, height).bit_length(), "DDS mip count")
    fourcc = u32(d, 84)
    if fourcc == 0x31545844:
        block = 8
    elif fourcc == 0x35545844:
        block = 16
    else:
        require(fourcc == 0 and u32(d, 88) == 32 and
                tuple(u32(d, k) for k in (92, 96, 100, 104)) ==
                (0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000),
                "DDS unsupported format")
        block = 0
    used = 128
    for mip in range(mips):
        w = max(1, width >> mip)
        h = max(1, height >> mip)
        used += (max(1, (h + 3) // 4) *
                 max(1, (w + 3) // 4) * block if block else w * h * 4)
    if legacy:
        # Match the native V1 ParseDds contract exactly. A 11136-byte
        # container with DXT5/ARGB or the wrong 128x128 mip chain is NOT a
        # valid V1 DDS even when the outer OVC CRC has been recomputed.
        require(count == 11136 and width == 128 and height == 128 and
                mips == 8 and fourcc == 0x31545844 and
                used == 128 + 10936,
                "legacy DDS payload/layout")
    else:
        require(used == count, "DDS mip payload")
    return count


def inspect(path: Path, dashboard_overlay: bool = False) -> dict:
    require(path.is_file(), "missing file")
    require(36 <= path.stat().st_size <= MAX_FILE, "OVC size")
    data = path.read_bytes()
    version = MAGIC.get(data[:8])
    require(version is not None and u32(data, 8) == version, "OVC format/version")
    groups, materials, vertices, tris, payload, crc = struct.unpack_from(
        "<6I", data, 12)
    require(0 < groups <= 512 and 0 < materials <= 128 and
            0 < vertices <= 1000000 and 0 < tris <= 2000000,
            "OVC totals/envelope")
    require(payload == len(data) - 36, "OVC payload bytes")
    require((zlib.crc32(memoryview(data)[36:]) & 0xffffffff) == crc,
            "OVC CRC32")
    if version == 1:
        require((groups, materials, vertices, tris) ==
                (70, 19, 21100, 38992), "legacy fixed layout")
    at, gpu_bytes, total_v, total_tris = 36, 0, 0, 0
    min_y = math.inf
    zero_normals = 0
    glass_triangles = 0
    # Match the runtime's exact glass tag; all other mesh materials are
    # opaque and must own their own PBR maps for strict map certification.
    used_materials: set[int] = set()
    incomplete_albedo_mips: set[int] = set()
    opaque_materials: set[int] = set()
    usable_uv_materials: set[int] = set()
    invalid_uv_materials: set[int] = set()
    collapsed_tangent_materials: set[int] = set()
    incomplete_mips_materials: set[int] = set()
    normal_materials: set[int] = set()
    disabled_normal_strength: set[int] = set()
    orm_materials: set[int] = set()
    for _ in range(groups):
        head = 12 if version == 1 else 16
        require(at + head <= len(data), "mesh header")
        name_bytes, material, count_v, count_i = struct.unpack_from(
            "<HHII", data, at)
        width_i = 2 if version == 1 else u32(data, at + 12)
        at += head
        require(1 <= name_bytes <= 256 and material < materials and
                3 <= count_v <= 1000000 and 3 <= count_i <= 6000000 and
                count_i % 3 == 0 and width_i in (2, 4) and
                (width_i == 4 or count_v <= 65535), "mesh bounds")
        vertex_bytes, index_bytes = count_v * 32, count_i * width_i
        require(at + name_bytes + vertex_bytes + index_bytes <= len(data),
                "mesh truncated")
        name = data[at:at + name_bytes]
        require(b"\x00" not in name and (version != 1 or name[:3] == b"LHD"),
                "mesh identity")
        used_materials.add(material)
        is_glass = name.startswith((b"F50_GLASS_", b"EXT_GLASS_"))
        if is_glass:
            glass_triangles += count_i // 3
        else:
            opaque_materials.add(material)
        at += name_bytes
        vertex_start = at
        for i in range(count_v):
            values = struct.unpack_from("<8f", data, at + i * 32)
            require(all(math.isfinite(x) and abs(x) <= 10000 for x in values),
                    "nonfinite vertex/UV/normal")
            if sum(n*n for n in values[3:6]) <= 1e-12:
                zero_normals += 1
        at += vertex_bytes
        fmt = "<H" if width_i == 2 else "<I"
        has_drawable_triangle = False
        for i in range(count_i):
            idx = struct.unpack_from(fmt, data, at + i * width_i)[0]
            require(idx < count_v, "mesh index out of bounds")
            if i % 3 == 2:
                tri = tuple(struct.unpack_from(
                    fmt, data, at + j * width_i)[0] for j in (i - 2, i - 1, i))
                positions = tuple(struct.unpack_from(
                    "<3f", data, vertex_start + vertex * 32)
                    for vertex in tri)
                # Match native indexed mesh bounds; unreferenced vertices
                # remain structurally validated, but are never rasterized.
                min_y = min(min_y, *(v[1] for v in positions))
                a, b, c = positions
                ux, uy, uz = (b[j] - a[j] for j in range(3))
                vx, vy, vz = (c[j] - a[j] for j in range(3))
                if uy * vz - uz * vy or uz * vx - ux * vz or ux * vy - uy * vx:
                    has_drawable_triangle = True
                if not is_glass:
                    # Every opaque triangle must have a valid derivative TBN.
                    # Previously, one valid triangle on this material hid an
                    # arbitrary number of UV-degenerate triangles/submeshes.
                    uvs = tuple(struct.unpack_from(
                        "<2f", data, vertex_start + vertex * 32 + 24)
                        for vertex in tri)
                    if triangle_has_pbr_basis(*positions, *uvs):
                        usable_uv_materials.add(material)
                        # UV area alone does not prove that the shader's
                        # orthogonalized tangent survives the imported normal.
                        if material not in collapsed_tangent_materials:
                            normals = tuple(struct.unpack_from(
                                "<3f", data, vertex_start + vertex * 32 + 12)
                                for vertex in tri)
                            if triangle_source_tangent_collapsed(
                                    positions, uvs, normals):
                                collapsed_tangent_materials.add(material)
                    else:
                        invalid_uv_materials.add(material)
        # Match the x86 native parser's fail-closed zero-area mesh policy.
        # A CRC-valid but invisible group must not suppress the stock car.
        require(has_drawable_triangle, "mesh degenerate geometry")
        at += index_bytes
        gpu_bytes += vertex_bytes + index_bytes
        total_v += count_v
        total_tris += count_i // 3
        require(gpu_bytes <= MAX_GPU and total_v <= vertices and
                total_tris <= tris, "mesh cumulative budget")
    require(total_v == vertices and total_tris == tris, "mesh totals mismatch")
    for material_id in range(materials):
        length = u32(data, at)
        at += 4
        dds_length(data, at, length, version == 1)
        # Albedo is sampled for both opaque and glass groups. A valid
        # short mip chain can render, but must not earn strict HQ approval.
        height, width, mips = (u32(data, at + k) for k in (12, 16, 28))
        if mips != max(width, height).bit_length():
            incomplete_albedo_mips.add(material_id)
        at += length
        gpu_bytes += length
        require(gpu_bytes <= MAX_GPU, "albedo GPU budget")
    normal_maps = 0
    orm_maps = 0
    if version >= 3:
        require(data[at:at + 8] == b"OVCPBR3!", "PBR header")
        at += 8
        for material_id in range(materials):
            require(at + 12 <= len(data), "PBR factors")
            rough, metal, normal_strength = struct.unpack_from("<3f", data, at)
            require(all(map(math.isfinite, (rough, metal, normal_strength))) and
                    MIN_ROUGHNESS_F32 <= rough <= 1 and 0 <= metal <= 1 and
                    0 <= normal_strength <= 2, "PBR factor bounds")
            at += 12
            for index in range(2):
                length = u32(data, at)
                at += 4
                if length:
                    dds_length(data, at, length, False)
                    # Valid single-mip DDS is renderable, but cannot certify
                    # HQ PBR map quality. The optional strict gate requires a
                    # complete chain for every used normal/ORM material.
                    dds_height, dds_width, dds_mips = (
                        u32(data, at + 12), u32(data, at + 16),
                        u32(data, at + 28))
                    if dds_mips != max(dds_width, dds_height).bit_length():
                        incomplete_mips_materials.add(material_id)
                    at += length
                    gpu_bytes += length
                    if index == 0:
                        normal_maps += 1
                        normal_materials.add(material_id)
                        # The SM3 pixel shader only samples normalMap for
                        # factors.z > 0. Keep map counts structural, but do
                        # not certify a disabled map as functional PBR.
                        if normal_strength == 0.0:
                            disabled_normal_strength.add(material_id)
                    else:
                        orm_maps += 1
                        orm_materials.add(material_id)
                require(gpu_bytes <= MAX_GPU, "PBR GPU budget")
    dashboards = 0
    if version == 4:
        require(data[at:at + 8] == b"OVCDASH4", "dashboard header")
        dashboards = u32(data, at + 8)
        at += 12
        require(dashboards <= 512, "dashboard binding count")
        used_indices = set()
        for _ in range(dashboards):
            require(at + 56 <= len(data), "dashboard record")
            mesh_index, kind, gear, reserved = struct.unpack_from(
                "<4I", data, at)
            require(mesh_index < groups and kind in (1, 2, 3) and
                    reserved == 0 and mesh_index not in used_indices,
                    "dashboard indices/kind")
            used_indices.add(mesh_index)
            vals = struct.unpack_from("<10f", data, at + 16)
            pivot, axis = vals[:3], vals[3:6]
            # Native ValidDashboardBinding checks pivot before branching
            # on GearVisible. A CRC-valid gear record with a NaN/Inf or
            # out-of-range pivot must not earn offline approval.
            require(all(math.isfinite(x) and abs(x) <= 10000 for x in pivot),
                    "dashboard pivot bounds")
            if kind == 3:
                require(gear <= 7, "gear bound")
            else:
                # ValidDashboardBinding uses float32 constants and rounds
                # each multiply/add in its sequential axisLen2 accumulation.
                # Python binary64 comparisons reject valid boundary needles.
                require(all(math.isfinite(x) for x in vals) and
                        all(abs(x) <= f32(1.001) for x in axis),
                        "dashboard needle calibration")
                axis_len2 = 0.0
                for x in axis:
                    axis_len2 = f32(axis_len2 + f32(x * x))
                require(f32(0.9801) <= axis_len2 <= f32(1.0201) and
                        vals[7] > vals[6] and
                        abs(vals[8]) <= f32(12.566371) and
                        abs(vals[9]) <= f32(12.566371),
                        "dashboard needle calibration")
            at += 56
    require(at == len(data), "OVC trailing bytes")
    if dashboard_overlay:
        # Dashboard overlays are deliberately above the vehicle floor and
        # use the runtime's wider -10..10 meter mesh envelope.
        require(-10.0 <= min_y <= 10.0, "dashboard overlay bounds")
    else:
        require(-1.20 <= min_y <= 0.25 and
                max(0., 0.035 - min_y) <= 1.25,
                "runtime floor placement cannot accept this vehicle")
    uncovered = uncovered_pbr_materials(
        version, opaque_materials, normal_materials, orm_materials,
        usable_uv_materials, invalid_uv_materials,
        incomplete_mips_materials, disabled_normal_strength)
    uncovered["collapsed_source_tangent"] = sorted(collapsed_tangent_materials)
    uncovered["incomplete_albedo_mips"] = sorted(
        used_materials & incomplete_albedo_mips)
    return {"version": version, "groups": groups, "triangles": tris,
            "vertices": vertices, "materials": materials,
            "glass_triangles": glass_triangles,
            "opaque_triangles": tris - glass_triangles,
            "normal_maps": normal_maps, "orm_maps": orm_maps,
            "disabled_normal_strength_materials": sorted(disabled_normal_strength),
            "zero_normal_vertices": zero_normals,
            "opaque_materials": sorted(opaque_materials),
            "usable_uv_materials": sorted(usable_uv_materials),
            "invalid_uv_materials": sorted(invalid_uv_materials),
            "collapsed_tangent_materials": sorted(collapsed_tangent_materials),
            "incomplete_mips_materials": sorted(incomplete_mips_materials),
            "pbr_uncovered": uncovered,
            "pbr_all_opaque_covered": not any(uncovered.values()),
            "ovc_sha256": hashlib.sha256(data).hexdigest(),
            "dashboard_bindings": dashboards, "floor_min_y": round(min_y, 4)}


def pbr_map_coverage(details: dict) -> bool:
    # File-wide totals are insufficient: orphan maps or all-degenerate UV
    # triangles do not reach the actual opaque body PBR shader material.
    return (details.get("version", 0) >= 3 and
            details.get("pbr_all_opaque_covered", False) is True)


def audit(game_root: Path, require_pbr_maps: bool = False) -> list[dict]:
    results = []
    for car_id, name in CARS:
        canonical = game_root / "ExternalCars" / f"car_id_{car_id:02d}.ovc"
        # Same preference as the runtime: a present but corrupt canonical
        # file is NOT silently replaced with unrelated legacy contents.
        legacy = game_root / "ExternalCars" / LEGACY[car_id] if car_id in LEGACY else None
        model = canonical if canonical.exists() or legacy is None else legacy
        if model == canonical and not model.exists():
            status, details = "MISSING", {}
        else:
            try:
                details = inspect(model)
                if require_pbr_maps and not pbr_map_coverage(details):
                    status = "FAIL"
                    details["reason"] = (
                        "required per-opaque-material normal/ORM/UV/full-mip coverage: " +
                        json.dumps(details["pbr_uncovered"], sort_keys=True))
                else:
                    status = "PASS"
            except (OvcError, OSError, struct.error) as error:
                status, details = "FAIL", {"reason": str(error)}
        overlay = game_root / "ExternalCars" / "Dashboard" / f"car_id_{car_id:02d}.ovc"
        if overlay.exists():
            try:
                od = inspect(overlay, dashboard_overlay=True)
                overlay_status = f"PASS v{od['version']}"
            except (OvcError, OSError, struct.error) as error:
                overlay_status = f"FAIL: {error}"
        else:
            overlay_status = "NOT_INSTALLED"
        # A corrupt installed dashboard is a vehicle preflight failure, not
        # a successful body with an unreported sidecar error. In particular,
        # don't mask an existing body failure or a missing body candidate.
        if overlay_status.startswith("FAIL: "):
            overlay_reason = "dashboard overlay: " + overlay_status[6:]
            if status == "FAIL":
                details["reason"] = details.get("reason", "body preflight failed") + "; " + overlay_reason
            else:
                status = "FAIL"
                details = {**details, "reason": overlay_reason}
        results.append({"id": car_id, "car": name, "status": status,
                        "selected_asset": model.name, "body": details,
                        "dashboard_overlay": overlay_status})
    return results


def self_test() -> None:
    # Tiny synthetic V4, one mesh and one 1x1 ARGB albedo.
    dds = bytearray(132)
    dds[:4] = b"DDS "
    for offset, val in {4: 124, 12: 1, 16: 1, 28: 1, 76: 32,
                        80: 0x41, 88: 32, 92: 0x00ff0000,
                        96: 0x0000ff00, 100: 0x000000ff,
                        104: 0xff000000}.items():
        struct.pack_into("<I", dds, offset, val)
    verts = b"".join(struct.pack("<8f", *v) for v in (
        (0,0,0,0,1,0,0,0), (1,0,0,0,1,0,1,0),
        (0,1,0,0,1,0,0,1)))
    name = b"EXT_OPAQUE_00"
    group = struct.pack("<HHIII", len(name), 0, 3, 3, 4) + name + verts
    group += struct.pack("<3I", 0, 1, 2)
    payload = group + struct.pack("<I", len(dds)) + dds
    payload += b"OVCPBR3!" + struct.pack("<3fII", 0.5,0,1,0,0)
    payload += b"OVCDASH4" + struct.pack("<I", 0)
    header = b"OVRCABH4" + struct.pack("<7I", 4,1,1,3,1,len(payload),
                                     zlib.crc32(payload) & 0xffffffff)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "car_id_00.ovc"
        path.write_bytes(header + payload)
        assert inspect(path)["triangles"] == 1
        assert inspect(path)["zero_normal_vertices"] == 0
        # CRC-valid unused vertex must not change the drawable floor.
        # Referencing it instead must still enforce the same envelope.
        for car_id, _ in CARS:
            slot_path = Path(directory) / f"car_id_{car_id:02d}.ovc"
            for index_width, index_format in ((2, "<3H"), (4, "<3I")):
                for overlay in (False, True):
                    for referenced in (False, True):
                        outlier = struct.pack("<8f", 100, -100, 100, 0, 1, 0, 0, 0)
                        indices = (0, 2, 3) if referenced else (1, 2, 3)
                        fixture = (struct.pack("<HHIII", len(name), 0, 4, 3, index_width)
                                   + name + outlier + verts
                                   + struct.pack(index_format, *indices)
                                   + payload[len(group):])
                        fixture_header = b"OVRCABH4" + struct.pack(
                            "<7I", 4, 1, 1, 4, 1, len(fixture),
                            zlib.crc32(fixture) & 0xffffffff)
                        slot_path.write_bytes(fixture_header + fixture)
                        if referenced:
                            try:
                                inspect(slot_path, dashboard_overlay=overlay)
                            except OvcError as error:
                                assert str(error) == ("dashboard overlay bounds" if overlay
                                    else "runtime floor placement cannot accept this vehicle")
                            else:
                                raise AssertionError("referenced floor outlier accepted")
                        else:
                            assert inspect(slot_path, dashboard_overlay=overlay)["floor_min_y"] == 0
        path.write_bytes(header + payload)
        # All 16 slots, speed and RPM: valid float32 boundary values must
        # agree with native ValidDashboardBinding, not binary64 literals.
        # Preserve strict PBR/geometry checks and reject invalid axes.
        for car_id, _ in CARS:
            slot_path = Path(directory) / f"car_id_{car_id:02d}.ovc"
            for kind in (1, 2):
                for axis, expected in (
                    ((1., 0., 0.), True),
                    ((1.001, 0., 0.), True),
                    ((-1.001, 0., 0.), True),
                    ((0.001, 0.9899994730949402, 0.), True),
                    ((1.0011, 0., 0.), False),
                    ((0., 0., 0.9899), False),
                    ((0.8, 0.8, 0.), False),
                    ((float("nan"), 0., 0.), False),
                ):
                    fixture = (payload[:-4] + struct.pack("<I", 1) +
                               struct.pack("<4I10f", 0, kind, 0, 0,
                                           0., 0., 0., *axis,
                                           0., 320., -1., 1.))
                    fixture_header = b"OVRCABH4" + struct.pack(
                        "<7I", 4, 1, 1, 3, 1, len(fixture),
                        zlib.crc32(fixture) & 0xffffffff)
                    slot_path.write_bytes(fixture_header + fixture)
                    try:
                        details = inspect(slot_path)
                    except OvcError as error:
                        assert not expected and str(error) == "dashboard needle calibration", (
                            car_id, kind, axis, str(error))
                    else:
                        assert expected and details["dashboard_bindings"] == 1, (
                            car_id, kind, axis)
        path.write_bytes(header + payload)
        # Recalculate CRC to prove geometry, not corruption, rejects blank body.
        repeated = bytearray(header + payload)
        index_offset = 36 + 16 + len(name) + len(verts)
        struct.pack_into("<3I", repeated, index_offset, 0, 0, 0)
        struct.pack_into("<I", repeated, 32,
                         zlib.crc32(memoryview(repeated)[36:]) & 0xffffffff)
        path.write_bytes(repeated)
        try:
            inspect(path)
        except OvcError as error:
            assert str(error) == "mesh degenerate geometry", str(error)
        else:
            raise AssertionError("CRC-valid blank mesh was accepted")
        # Restore a valid container for existing PBR/dashboard corruption tests.
        path.write_bytes(header + payload)
        assert inspect(path)["opaque_materials"] == [0]
        assert inspect(path)["usable_uv_materials"] == [0]
        assert not pbr_map_coverage(inspect(path))
        b = bytearray(path.read_bytes())
        b[-1] ^= 1
        path.write_bytes(b)
        try:
            inspect(path)
        except OvcError as error:
            assert str(error) == "OVC CRC32", str(error)
        else:
            raise AssertionError("Corrupt CRC was accepted")
        # A formally valid V4 with zero maps is not PBR-covered; a synthetic
        # V4 with one normal and ORM DDS must pass the optional strict gate.
        mapped = group + struct.pack("<I", len(dds)) + dds
        mapped += b"OVCPBR3!" + struct.pack("<3f", 0.5, 0, 1)
        mapped += (struct.pack("<I", len(dds)) + dds) * 2
        mapped += b"OVCDASH4" + struct.pack("<I", 0)
        mapped_header = b"OVRCABH4" + struct.pack(
            "<7I", 4, 1, 1, 3, 1, len(mapped),
            zlib.crc32(mapped) & 0xffffffff)
        path.write_bytes(mapped_header + mapped)
        covered = inspect(path)
        assert covered["normal_maps"] == 1 and covered["orm_maps"] == 1
        assert covered["pbr_uncovered"]["no_normal"] == []
        assert covered["pbr_uncovered"]["no_orm"] == []
        assert pbr_map_coverage(covered)
        # Full DDS chains and nondegenerate UV are insufficient if all
        # source normals are parallel to the UV tangent. Recompute CRC so
        # that strict material QA, not container corruption, rejects it.
        for car_id, _ in CARS:
            slot_path = Path(directory) / f"car_id_{car_id:02d}.ovc"
            for normal, expected in (
                    ((0., 0., 1.), True), ((0., 0., -1.), True),
                    ((0., 0., 0.), True), ((1., 0., 0.), False),
                    ((-2., 0., 0.), False)):
                fixture = bytearray(mapped)
                for vertex in range(3):
                    struct.pack_into("<3f", fixture,
                                     16 + len(name) + vertex * 32 + 12, *normal)
                fixture_header = b"OVRCABH4" + struct.pack(
                    "<7I", 4, 1, 1, 3, 1, len(fixture),
                    zlib.crc32(fixture) & 0xffffffff)
                slot_path.write_bytes(fixture_header + fixture)
                details = inspect(slot_path)
                assert details["usable_uv_materials"] == [0]
                assert details["normal_maps"] == details["orm_maps"] == 1
                assert details["pbr_uncovered"]["collapsed_source_tangent"] == (
                    [] if expected else [0])
                assert pbr_map_coverage(details) == expected, (car_id, normal)
        # A good sibling mesh on the same material must not hide a bad one.
        broken = bytearray(group)
        for vertex in range(3):
            struct.pack_into("<3f", broken,
                             16 + len(name) + vertex * 32 + 12, 1., 0., 0.)
        mixed = group + broken + mapped[len(group):]
        mixed_header = b"OVRCABH4" + struct.pack(
            "<7I", 4, 2, 1, 6, 2, len(mixed),
            zlib.crc32(mixed) & 0xffffffff)
        path.write_bytes(mixed_header + mixed)
        assert inspect(path)["collapsed_tangent_materials"] == [0]
        assert not pbr_map_coverage(inspect(path))
        # Glass uses the separate transparent path, not strict opaque PBR.
        glass_name = b"EXT_GLASS_00"
        glass_group = (struct.pack("<HHIII", len(glass_name), 0, 3, 3, 4)
                       + glass_name + broken[16 + len(name):])
        mixed = group + glass_group + mapped[len(group):]
        mixed_header = b"OVRCABH4" + struct.pack(
            "<7I", 4, 2, 1, 6, 2, len(mixed),
            zlib.crc32(mixed) & 0xffffffff)
        path.write_bytes(mixed_header + mixed)
        assert pbr_map_coverage(inspect(path))
        # All sixteen slots and three DDS roles, with valid outer CRC.
        albedo_offset = len(group) + 4
        normal_offset = albedo_offset + len(dds) + 8 + 12 + 4
        orm_offset = normal_offset + len(dds) + 4
        for car_id, _ in CARS:
            slot_path = Path(directory) / f"car_id_{car_id:02d}.ovc"
            for texture_offset in (albedo_offset, normal_offset, orm_offset):
                for field, value, expected in (
                    (112, 0, True), (24, 1, True),
                    (112, 0x200, False), (112, 0x400, False),
                    (112, 0x8000, False), (112, 0x200000, False),
                    (8, 0x800000, False), (24, 2, False),
                ):
                    fixture = bytearray(mapped)
                    struct.pack_into("<I", fixture, texture_offset + field, value)
                    fixture_header = b"OVRCABH4" + struct.pack(
                        "<7I", 4, 1, 1, 3, 1, len(fixture),
                        zlib.crc32(fixture) & 0xffffffff)
                    slot_path.write_bytes(fixture_header + fixture)
                    try:
                        details = inspect(slot_path)
                    except OvcError as error:
                        assert not expected and str(error) == "DDS non-2D resource"
                    else:
                        assert expected and pbr_map_coverage(details), (
                            car_id, texture_offset, field, value)
        # CRC-correct OVC4 with full DDS maps but zero material strength
        # is structurally renderable, not a functioning normal-mapped body.
        # Exercise positive/negative strengths for every canonical slot.
        strength_offset = len(group) + 4 + len(dds) + 8 + 8
        for car_id, _ in CARS:
            slot_path = Path(directory) / f"car_id_{car_id:02d}.ovc"
            for strength, expected in ((0., False), (-0., False),
                                       (.25, True), (1., True), (2., True)):
                fixture = bytearray(mapped)
                struct.pack_into("<f", fixture, strength_offset, strength)
                fixture_header = b"OVRCABH4" + struct.pack(
                    "<7I", 4, 1, 1, 3, 1, len(fixture),
                    zlib.crc32(fixture) & 0xffffffff)
                slot_path.write_bytes(fixture_header + fixture)
                details = inspect(slot_path)
                assert details["normal_maps"] == 1 and details["orm_maps"] == 1
                assert details["pbr_uncovered"]["no_normal"] == []
                assert details["disabled_normal_strength_materials"] == (
                    [] if expected else [0])
                assert details["pbr_uncovered"]["disabled_normal_strength"] == (
                    [] if expected else [0])
                assert pbr_map_coverage(details) == expected, (car_id, strength)
        # Two opaque meshes share one PBR material. One mesh is UV-valid
        # while its sibling has collapsed UV. A file-wide "any UV" gate
        # incorrectly certified these CRC-valid broken normal maps.
        bad_verts = bytearray(verts)
        for vertex in range(3):
            struct.pack_into("<2f", bad_verts, vertex * 32 + 24, 0., 0.)
        bad_group = (struct.pack("<HHIII", len(name), 0, 3, 3, 4)
                     + name + bad_verts + struct.pack("<3I", 0, 1, 2))
        mixed = group + bad_group + mapped[len(group):]
        mixed_header = b"OVRCABH4" + struct.pack(
            "<7I", 4, 2, 1, 6, 2, len(mixed),
            zlib.crc32(mixed) & 0xffffffff)
        path.write_bytes(mixed_header + mixed)
        half_broken = inspect(path)
        assert half_broken["usable_uv_materials"] == [0]
        assert half_broken["invalid_uv_materials"] == [0]
        assert half_broken["pbr_uncovered"]["partially_degenerate_uv"] == [0]
        assert not pbr_map_coverage(half_broken), (
            "CRC-valid partially UV-degenerate opaque material passed")
        # A syntactically valid but single-mip 4x4 normal map cannot pass
        # the high-quality PBR map gate (even with OVC CRC recomputed).
        short_mip_dds = bytearray(128 + 4 * 4 * 4)
        short_mip_dds[:128] = dds[:128]
        struct.pack_into("<3I", short_mip_dds, 12, 4, 4, 0)
        struct.pack_into("<I", short_mip_dds, 28, 1)
        short_mip = (group + struct.pack("<I", len(dds)) + dds
                     + b"OVCPBR3!" + struct.pack("<3f", 0.5, 0, 1)
                     + struct.pack("<I", len(short_mip_dds))
                     + short_mip_dds
                     + struct.pack("<I", len(dds)) + dds
                     + b"OVCDASH4" + struct.pack("<I", 0))
        short_header = b"OVRCABH4" + struct.pack(
            "<7I", 4, 1, 1, 3, 1, len(short_mip),
            zlib.crc32(short_mip) & 0xffffffff)
        path.write_bytes(short_header + short_mip)
        short_details = inspect(path)
        assert short_details["incomplete_mips_materials"] == [0]
        assert short_details["pbr_uncovered"]["incomplete_pbr_mips"] == [0]
        assert not pbr_map_coverage(short_details), (
            "CRC-valid truncated normal DDS mip chain passed strict PBR")
        # The same valid short DDS as ALBEDO must also fail the HQ gate.
        # Complete 4x4/2x2/1x1 chain must pass with identical PBR maps.
        full_albedo = bytearray(short_mip_dds) + bytearray(20)
        struct.pack_into("<I", full_albedo, 28, 3)
        for albedo, expected in ((short_mip_dds, False), (full_albedo, True)):
            fixture = (group + struct.pack("<I", len(albedo)) + albedo
                       + mapped[len(group) + 4 + len(dds):])
            fixture_header = b"OVRCABH4" + struct.pack(
                "<7I", 4, 1, 1, 3, 1, len(fixture),
                zlib.crc32(fixture) & 0xffffffff)
            path.write_bytes(fixture_header + fixture)
            details = inspect(path)
            assert details["pbr_uncovered"]["incomplete_albedo_mips"] == (
                [] if expected else [0])
            assert pbr_map_coverage(details) == expected
        # A valid CRC and two populated PBR DDS maps are insufficient when
        # every triangle's UV determinant is zero: the shader cannot build TBN.
        no_uv = bytearray(mapped)
        vertex_start = 16 + len(name)
        for vertex in range(3):
            struct.pack_into("<2f", no_uv, vertex_start + vertex * 32 + 24, 0., 0.)
        no_uv_header = b"OVRCABH4" + struct.pack(
            "<7I", 4, 1, 1, 3, 1, len(no_uv),
            zlib.crc32(no_uv) & 0xffffffff)
        path.write_bytes(no_uv_header + no_uv)
        degraded = inspect(path)
        assert degraded["pbr_uncovered"]["degenerate_uv"] == [0]
        assert not pbr_map_coverage(degraded)
        # Python binary64 0.04 is larger than the valid D3D9 C++ 0.04f.
        # Without a float32 boundary the verifier falsely rejects genuine
        # 575 Superamerica files even though the native OVC parser accepts.
        pbr_roughness_offset = len(group) + 4 + len(dds) + 8
        exact_f32 = bytearray(mapped)
        struct.pack_into("<f", exact_f32, pbr_roughness_offset, 0.04)
        header_f32 = b"OVRCABH4" + struct.pack(
            "<7I", 4, 1, 1, 3, 1, len(exact_f32),
            zlib.crc32(exact_f32) & 0xffffffff)
        path.write_bytes(header_f32 + exact_f32)
        assert inspect(path)["version"] == 4
        assert pbr_map_coverage(inspect(path))
        below_f32 = bytearray(exact_f32)
        struct.pack_into("<f", below_f32, pbr_roughness_offset, 0.039)
        below_header = b"OVRCABH4" + struct.pack(
            "<7I", 4, 1, 1, 3, 1, len(below_f32),
            zlib.crc32(below_f32) & 0xffffffff)
        path.write_bytes(below_header + below_f32)
        try:
            inspect(path)
        except OvcError as error:
            assert str(error) == "PBR factor bounds", str(error)
        else:
            raise AssertionError("Below-0.04f PBR roughness was accepted")
    # Runtime V1 requires 128x128, 8 mips, DXT1 and the known 72-byte
    # legacy tail; simply checking the 11136-byte container is insufficient.
    legacy_dds = bytearray(11136)
    legacy_dds[:4] = b"DDS "
    for offset, value in {4: 124, 12: 128, 16: 128, 28: 8,
                          76: 32, 84: 0x31545844}.items():
        struct.pack_into("<I", legacy_dds, offset, value)
    assert dds_length(legacy_dds, 0, len(legacy_dds), True) == 11136
    for offset, corrupt in ((12, 64), (16, 64), (28, 7),
                            (84, 0x35545844)):
        changed = bytearray(legacy_dds)
        struct.pack_into("<I", changed, offset, corrupt)
        try:
            dds_length(changed, 0, len(changed), True)
        except OvcError:
            pass
        else:
            raise AssertionError("Incorrect V1 DDS layout passed preflight")
    assert len(CARS) == 16 and len({i for i, _ in CARS}) == 16
    print("FERRARI16_OVC_READONLY_PREFLIGHT_SELFTEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, default=Path("."))
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--require-pbr-maps", action="store_true",
                        help="fail each installed car lacking PBR normal or ORM maps")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    rows = audit(args.game_root, require_pbr_maps=args.require_pbr_maps)
    for row in rows:
        print(f"{row['id']:02d} {row['car']:<19} {row['status']:<7} "
              f"{row['selected_asset']:<16} overlay={row['dashboard_overlay']}")
        if row["status"] == "PASS":
            body = row["body"]
            print("    PBR maps normal={normal_maps} ORM={orm_maps} "
                  "zeroNormals={zero_normal_vertices}".format(**body))
        if row["status"] == "FAIL":
            print("   ", row["body"]["reason"])
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ("PASS", "MISSING", "FAIL")}
    print("FERRARI16_STATIC_PREFLIGHT", counts,
          "Quest3/physical stereo/fps: NOT_TESTED")
    if args.json_out:
        args.json_out.write_text(json.dumps({"cars": rows, "counts": counts},
                                           indent=2, ensure_ascii=False),
                                 encoding="utf-8")
    return 0 if counts["PASS"] == 16 else 2


if __name__ == "__main__":
    raise SystemExit(main())
