#!/usr/bin/env python3
"""EXT16-003: installed dashboard corruption must fail the car preflight."""
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "ferrari16"))
from verify_all_car_ovc import audit  # noqa: E402


def valid_v4() -> bytes:
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
        (0, 0, 0, 0, 1, 0, 0, 0),
        (1, 0, 0, 0, 1, 0, 1, 0),
        (0, 1, 0, 0, 1, 0, 0, 1),
    ))
    group = struct.pack("<HHIII", len(name), 0, 3, 3, 4)
    group += name + vertices + struct.pack("<3I", 0, 1, 2)
    payload = group + struct.pack("<I", len(dds)) + dds
    payload += b"OVCPBR3!" + struct.pack("<3fII", 0.5, 0, 1, 0, 0)
    payload += b"OVCDASH4" + struct.pack("<I", 0)
    return b"OVRCABH4" + struct.pack(
        "<7I", 4, 1, 1, 3, 1, len(payload),
        zlib.crc32(payload) & 0xffffffff) + payload


def entry(root: Path) -> dict:
    return next(row for row in audit(root) if row["id"] == 8)


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
    print("FERRARI16_DASHBOARD_OVERLAY_POSITIVE_NEGATIVE_PASS")


if __name__ == "__main__":
    main()
