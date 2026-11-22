#!/usr/bin/env python3
"""Read-only Ferrari16 OVC preflight. No game files are changed or uploaded."""
from __future__ import annotations
import argparse
import json
import math
import struct
import tempfile
import zlib
from pathlib import Path

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
MAGIC = {b"OVRCAB15": 1, b"OVRCABH2": 2,
         b"OVRCABH3": 3, b"OVRCABH4": 4}


class OvcError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise OvcError(message)


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
        at += name_bytes
        for i in range(count_v):
            values = struct.unpack_from("<8f", data, at + i * 32)
            require(all(math.isfinite(x) and abs(x) <= 10000 for x in values),
                    "nonfinite vertex/UV/normal")
            min_y = min(min_y, values[1])
            if sum(n*n for n in values[3:6]) <= 1e-12:
                zero_normals += 1
        at += vertex_bytes
        fmt = "<H" if width_i == 2 else "<I"
        for i in range(count_i):
            require(struct.unpack_from(fmt, data, at + i * width_i)[0] < count_v,
                    "mesh index out of bounds")
        at += index_bytes
        gpu_bytes += vertex_bytes + index_bytes
        total_v += count_v
        total_tris += count_i // 3
        require(gpu_bytes <= MAX_GPU and total_v <= vertices and
                total_tris <= tris, "mesh cumulative budget")
    require(total_v == vertices and total_tris == tris, "mesh totals mismatch")
    for _ in range(materials):
        length = u32(data, at)
        at += 4
        dds_length(data, at, length, version == 1)
        at += length
        gpu_bytes += length
        require(gpu_bytes <= MAX_GPU, "albedo GPU budget")
    normal_maps = 0
    orm_maps = 0
    if version >= 3:
        require(data[at:at + 8] == b"OVCPBR3!", "PBR header")
        at += 8
        for _ in range(materials):
            require(at + 12 <= len(data), "PBR factors")
            rough, metal, normal_strength = struct.unpack_from("<3f", data, at)
            require(all(map(math.isfinite, (rough, metal, normal_strength))) and
                    0.04 <= rough <= 1 and 0 <= metal <= 1 and
                    0 <= normal_strength <= 2, "PBR factor bounds")
            at += 12
            for index in range(2):
                length = u32(data, at)
                at += 4
                if length:
                    dds_length(data, at, length, False)
                    at += length
                    gpu_bytes += length
                    if index == 0:
                        normal_maps += 1
                    else:
                        orm_maps += 1
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
            if kind == 3:
                require(gear <= 7, "gear bound")
            else:
                vals = struct.unpack_from("<10f", data, at + 16)
                pivot, axis = vals[:3], vals[3:6]
                require(all(math.isfinite(x) for x in vals) and
                        all(abs(x) <= 10000 for x in pivot) and
                        all(abs(x) <= 1.001 for x in axis) and
                        0.9801 <= sum(x*x for x in axis) <= 1.0201 and
                        vals[7] > vals[6] and
                        abs(vals[8]) <= 12.566371 and
                        abs(vals[9]) <= 12.566371,
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
    return {"version": version, "groups": groups, "triangles": tris,
            "vertices": vertices, "materials": materials,
            "normal_maps": normal_maps, "orm_maps": orm_maps,
            "zero_normal_vertices": zero_normals,
            "dashboard_bindings": dashboards, "floor_min_y": round(min_y, 4)}


def pbr_map_coverage(details: dict) -> bool:
    return (details.get("version", 0) >= 3 and
            details.get("normal_maps", 0) > 0 and
            details.get("orm_maps", 0) > 0)


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
                    details["reason"] = "required PBR normal/ORM maps missing"
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
        assert pbr_map_coverage(covered)
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
