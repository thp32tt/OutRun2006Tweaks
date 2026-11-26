#!/usr/bin/env python3
"""EXT16-003: installed dashboard corruption must fail the car preflight."""
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "ferrari16"))
from verify_all_car_ovc import CARS, audit  # noqa: E402


def valid_v4(normal=False, orm=False, strength=1.0, degenerate_uv=False) -> bytes:
    dds = bytearray(132)
    dds[:4] = b"DDS "
    for offset, value in {
        4: 124, 12: 1, 16: 1, 28: 1, 76: 32, 80: 0x41,
        88: 32, 92: 0x00ff0000, 96: 0x0000ff00,
        100: 0x000000ff, 104: 0xff000000,
    }.items():
        struct.pack_into("<I", dds, offset, value)
    name = b"EXT_OPAQUE_00"
    vertices = b"".join(struct.pack("<8f", *v) for v in (
        (0, 0, 0, 0, 0, 1, 0, 0),
        (1, 0, 0, 0, 0, 1, 1, 0),
        (0, 1, 0, 0, 0, 1, 0, 0 if degenerate_uv else 1),
    ))
    group = struct.pack("<HHIII", len(name), 0, 3, 3, 4)
    group += name + vertices + struct.pack("<3I", 0, 1, 2)
    payload = group + struct.pack("<I", len(dds)) + dds
    payload += b"OVCPBR3!" + struct.pack("<3f", 0.5, 0, strength)
    for present in (normal, orm):
        payload += struct.pack("<I", len(dds) if present else 0)
        if present:
            payload += dds
    payload += b"OVCDASH4" + struct.pack("<I", 0)
    return b"OVRCABH4" + struct.pack(
        "<7I", 4, 1, 1, 3, 1, len(payload),
        zlib.crc32(payload) & 0xffffffff) + payload


def gear_v4(pivot: float, gear: int = 5) -> bytes:
    payload = bytearray(valid_v4()[36:])
    struct.pack_into("<I", payload, len(payload) - 4, 1)
    payload += struct.pack("<4I10f", 0, 3, gear, 0,
                           pivot, 0, 0, 0, 0, 1, 0, 1, 0, 1)
    return b"OVRCABH4" + struct.pack(
        "<7I", 4, 1, 1, 3, 1, len(payload),
        zlib.crc32(payload) & 0xffffffff) + payload


def entry(root: Path, cid: int = 8, strict: bool = False) -> dict:
    return next(row for row in audit(root, require_pbr_maps=strict) if row["id"] == cid)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        body = root / "ExternalCars" / "car_id_08.ovc"
        overlay = root / "ExternalCars" / "Dashboard" / "car_id_08.ovc"
        overlay.parent.mkdir(parents=True)
        valid = valid_v4()
        body.write_bytes(valid)
        assert entry(root)["status"] == "PASS"  # optional absent is OK

        overlay.write_bytes(valid)
        row = entry(root)
        assert row["status"] == "PASS" and row["dashboard_overlay"] == "PASS v4"

        corrupt = bytearray(valid)
        corrupt[-1] ^= 1  # valid file size; invalid CRC
        overlay.write_bytes(corrupt)
        row = entry(root)
        assert row["status"] == "FAIL"
        assert row["dashboard_overlay"] == "FAIL: OVC CRC32"
        assert row["body"]["reason"] == "dashboard overlay: OVC CRC32"

        body.write_bytes(corrupt)
        row = entry(root)
        assert row["status"] == "FAIL"
        assert row["body"]["reason"] == "OVC CRC32; dashboard overlay: OVC CRC32"

        body.unlink()
        row = entry(root)
        assert row["status"] == "FAIL"  # don't conceal orphan bad dashboard
        assert row["body"]["reason"] == "dashboard overlay: OVC CRC32"

        overlay.unlink()
        assert entry(root)["status"] == "MISSING"  # ordinary original fallback

        # A valid CRC and gear number are insufficient: native checks
        # the pivot even though gear visibility does not rotate the mesh.
        # Test both body-embedded and independent dashboard records.
        for cid, _ in CARS:
            body = root / "ExternalCars" / f"car_id_{cid:02d}.ovc"
            overlay = root / "ExternalCars" / "Dashboard" / f"car_id_{cid:02d}.ovc"
            for target in (body, overlay):
                body.write_bytes(valid)
                overlay.unlink(missing_ok=True)
                for pivot in (0.0, -10000.0, 10000.0):
                    target.write_bytes(gear_v4(pivot))
                    assert entry(root, cid)["status"] == "PASS"
                for pivot in (float("nan"), float("inf"), -float("inf"),
                              10001.0, -10001.0):
                    target.write_bytes(gear_v4(pivot))
                    row = entry(root, cid)
                    assert row["status"] == "FAIL"
                    assert "dashboard pivot bounds" in row["body"]["reason"]
                target.write_bytes(gear_v4(0.0, gear=8))
                row = entry(root, cid)
                assert row["status"] == "FAIL"
                assert "gear bound" in row["body"]["reason"]
            body.unlink()
            overlay.unlink()
        # Strict PBR admission applies independently to each installed
        # overlay, not just to its otherwise-good body. Normal structural
        # admission and optional absence remain unchanged.
        import json
        prefix = "FAIL: required per-opaque-material normal/ORM/UV/full-mip coverage: "
        covered = valid_v4(normal=True, orm=True)
        for cid, _ in CARS:
            body = root / "ExternalCars" / f"car_id_{cid:02d}.ovc"
            overlay = root / "ExternalCars" / "Dashboard" / f"car_id_{cid:02d}.ovc"
            body.write_bytes(covered)
            assert entry(root, cid, True)["status"] == "PASS"
            overlay.write_bytes(covered)
            row = entry(root, cid, True)
            assert row["status"] == "PASS" and row["dashboard_overlay"] == "PASS v4"
            for bad, missing in (
                (valid_v4(), "no_normal"),
                (valid_v4(normal=True), "no_orm"),
                (valid_v4(orm=True), "no_normal"),
                (valid_v4(normal=True, orm=True, strength=0), "disabled_normal_strength"),
                (valid_v4(normal=True, orm=True, degenerate_uv=True), "degenerate_uv"),
            ):
                overlay.write_bytes(bad)
                assert entry(root, cid)["status"] == "PASS"
                row = entry(root, cid, True)
                assert row["status"] == "FAIL"
                assert row["dashboard_overlay"].startswith(prefix)
                assert json.loads(row["dashboard_overlay"][len(prefix):])[missing] == [0]
                assert row["body"]["reason"] == "dashboard overlay: " + row["dashboard_overlay"][6:]
            # Both independent failure reasons must survive.
            body.write_bytes(valid_v4())
            row = entry(root, cid, True)
            assert row["status"] == "FAIL"
            assert "; dashboard overlay: " in row["body"]["reason"]
            body.unlink()
            row = entry(root, cid, True)
            assert row["status"] == "FAIL"
            # F50/GTO/F40 also report the absent legacy-body read failure.
            assert row["body"]["reason"].endswith(
                "dashboard overlay: " + row["dashboard_overlay"][6:])
            if cid in (2, 7, 11):
                assert "; dashboard overlay: " in row["body"]["reason"]
            else:
                assert row["body"]["reason"].startswith("dashboard overlay: ")
            overlay.unlink()
    print("FERRARI16_DASHBOARD_OVERLAY_POSITIVE_NEGATIVE_PASS")


if __name__ == "__main__":
    main()
