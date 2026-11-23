#!/usr/bin/env python3
"""Synthetic positive/negative Ferrari exact-body conversion and rights gate."""
import copy
import hashlib
import json
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "ferrari16"))
from exact_variant_quality_gate import EXACT, audit_manifest, validate_one, GateError  # noqa: E402
from ferrari16_overlay_status_test import valid_v4  # noqa: E402
import zlib


def glb(path: Path, *, triangles: int = 1, width: int = 2) -> None:
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
    png += struct.pack(">II", width, width) + b"\x08\x06\x00\x00\x00"
    png += b"\x00\x00\x00\x00"
    raw = png + png
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(raw)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(png)},
            {"buffer": 0, "byteOffset": len(png), "byteLength": len(png)}],
        "images": [{"name": "normal", "bufferView": 0, "mimeType": "image/png"},
                   {"name": "orm", "bufferView": 1, "mimeType": "image/png"}],
        "accessors": [{"count": triangles * 3}],
        "meshes": [{"primitives": [{"attributes": {
            "POSITION": 0, "NORMAL": 0, "TEXCOORD_0": 0},
            "indices": 0, "mode": 4}]}],
    }
    j = json.dumps(doc, separators=(",", ":")).encode()
    j += b" " * ((-len(j)) % 4)
    raw += b"\x00" * ((-len(raw)) % 4)
    data = b"glTF" + struct.pack("<2I", 2, 12 + 8 + len(j) + 8 + len(raw))
    data += struct.pack("<2I", len(j), 0x4e4f534a) + j
    data += struct.pack("<2I", len(raw), 0x004e4942) + raw
    path.write_bytes(data)


def mapped_v4() -> bytes:
    initial = valid_v4()
    payload = initial[36:]
    pos = payload.index(b"OVCPBR3!") + 8 + 12
    dds_start = payload.index(b"DDS ") - 4
    dds_size = struct.unpack_from("<I", payload, dds_start)[0]
    dds = payload[dds_start + 4:dds_start + 4 + dds_size]
    mapped = payload[:pos] + (struct.pack("<I", len(dds)) + dds) * 2
    mapped += payload[pos + 8:]  # skip the original two empty map lengths
    header = b"OVRCABH4" + struct.pack("<7I", 4, 1, 1, 3, 1,
                                         len(mapped), zlib.crc32(mapped) & 0xffffffff)
    return header + mapped


def hashed(path: Path) -> dict:
    return {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def expected_fail(entry: dict, root: Path, fragment: str) -> None:
    try:
        validate_one(entry, root)
    except GateError as exc:
        assert fragment in str(exc), (fragment, str(exc))
    else:
        raise AssertionError("negative fixture incorrectly passed: " + fragment)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source, converted = root / "source.glb", root / "converted.glb"
        glb(source)
        glb(converted)
        ovc = root / "converted.ovc"
        ovc.write_bytes(mapped_v4())
        record = root / "rights.txt"
        record.write_text("Synthetic PRIVATE TEST rights acknowledgement only.")
        shot0, shot1 = root / "source.png", root / "converted.png"
        shot0.write_bytes(b"fixture source image")
        shot1.write_bytes(b"fixture converted image")
        entry = {
            "car_id": 8, "variant": "328 GTS", "roof": "removable-targa",
            "vehicle_reference_url": "https://example.org/328-gts-reference",
            "asset_provenance_url": "https://example.org/creator-license",
            "authorized_use": "PRIVATE_MODDING_DOCUMENTED",
            "redistribution_allowed": False,
            "manual_review": {k: True for k in (
                "body_variant", "interior", "four_wheels", "materials_uv",
                "normal_orm", "side_by_side_preview")},
            "rights_record": hashed(record), "source_preview": hashed(shot0),
            "converted_preview": hashed(shot1),
            "source_glb": hashed(source), "converted_glb": hashed(converted),
            "ovc4": hashed(ovc),
        }
        assert validate_one(entry, root)["status"] == "PASS_STATIC_SOURCE_ONLY"
        wrong = copy.deepcopy(entry)
        wrong["variant"] = "328 GTB"
        expected_fail(wrong, root, "wrong exact body")
        wrong = copy.deepcopy(entry)
        wrong["redistribution_allowed"] = True
        expected_fail(wrong, root, "public asset shipping")
        wrong = copy.deepcopy(entry)
        wrong["manual_review"]["four_wheels"] = False
        expected_fail(wrong, root, "review missing")
        wrong = copy.deepcopy(entry)
        wrong["rights_record"]["sha256"] = "0" * 64
        expected_fail(wrong, root, "SHA256 mismatch")
        glb(converted, width=1)
        wrong = copy.deepcopy(entry)
        wrong["converted_glb"] = hashed(converted)
        expected_fail(wrong, root, "silent texture downscale")
        glb(converted, triangles=2)
        wrong["converted_glb"] = hashed(converted)
        expected_fail(wrong, root, "triangle loss/decimation")
        glb(converted)
        wrong = copy.deepcopy(entry)
        wrong["roof"] = "coupe"
        expected_fail(wrong, root, "wrong exact body")
        wrong = copy.deepcopy(entry)
        wrong["car_id"] = 6
        wrong["variant"] = "Testarossa Spider"
        wrong["roof"] = "open-top-one-off-1986"
        expected_fail(wrong, root, "one-off chassis")
        wrong["one_off_chassis"] = "62897"
        assert validate_one(wrong, root)["status"] == "PASS_STATIC_SOURCE_ONLY"
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "cars": [entry]}))
        rows = audit_manifest(manifest)
        assert len(rows) == 4 and [x["status"] for x in rows].count("BLOCKED") == 3
        assert len(EXACT) == 4
    print("FERRARI16_EXACT_VARIANT_PROVENANCE_CONVERSION_POSITIVE_NEGATIVE_PASS")


if __name__ == "__main__":
    main()
