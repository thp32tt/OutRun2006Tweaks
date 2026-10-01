#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile

PINNED_ARCHIVE_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
PINNED_ARCHIVE_SIZE = 306223257
MEMBER = "textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds"
CANONICAL_SHA256 = "4da4871fc494de71520e0299f4cb26eb8c9f6f7ce30ecd78f8b1d8dcd4b0f85a"
CANONICAL_WIDTH = 2048
CANONICAL_HEIGHT = 1024
CANONICAL_MODE = "RGBA32"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def dds_info(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("not a DDS file")
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    mip_count = struct.unpack_from("<I", data, 28)[0] or 1
    pf_flags = struct.unpack_from("<I", data, 80)[0]
    fourcc_raw = data[84:88]
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    fourcc = fourcc_raw.decode("latin1")
    if fourcc_raw == b"DXT5":
        mode = "DXT5"
    elif fourcc_raw == b"DXT1":
        mode = "DXT1"
    elif rgb_bits == 32:
        mode = "RGBA32"
    else:
        mode = f"UNKNOWN(flags={pf_flags},fourcc={fourcc!r},rgb_bits={rgb_bits})"
    return {
        "width": width,
        "height": height,
        "mip_count": mip_count,
        "pixel_format": mode,
        "fourcc": fourcc,
        "rgb_bits": rgb_bits,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", help="Path to the pinned OR2-HD-GUI-v0.25.10a.zip")
    ns = ap.parse_args()

    archive_sha, archive_size = sha256_file(ns.archive)
    if archive_sha != PINNED_ARCHIVE_SHA256 or archive_size != PINNED_ARCHIVE_SIZE:
        raise SystemExit("PINNED_ARCHIVE_IDENTITY_MISMATCH")

    with zipfile.ZipFile(ns.archive) as zf:
        data = zf.read(MEMBER)

    actual = dds_info(data)
    member_sha = sha256_bytes(data)
    identity_match = (
        member_sha == CANONICAL_SHA256
        and actual["width"] == CANONICAL_WIDTH
        and actual["height"] == CANONICAL_HEIGHT
        and actual["pixel_format"] == CANONICAL_MODE
    )

    result = {
        "schema_version": 1,
        "asset_index": 230,
        "asset_id": "E95DA5",
        "queue_path": MEMBER,
        "archive_sha256": archive_sha,
        "archive_size": archive_size,
        "member_sha256": member_sha,
        "member_size": len(data),
        "actual": actual,
        "expected_canonical": {
            "sha256": CANONICAL_SHA256,
            "width": CANONICAL_WIDTH,
            "height": CANONICAL_HEIGHT,
            "pixel_format": CANONICAL_MODE,
        },
        "identity_match": identity_match,
        "source_disposition": "CANONICAL_MATCH" if identity_match else "SOURCE_IDENTITY_MISMATCH",
        "production_readiness": "SOURCE_READY" if identity_match else "PREFLIGHT_ONLY",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if identity_match else 0


if __name__ == "__main__":
    raise SystemExit(main())
