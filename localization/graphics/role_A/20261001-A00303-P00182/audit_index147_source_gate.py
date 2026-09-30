#!/usr/bin/env python3
"""Fail-closed canonical source identity gate for asset 39BCA907 / queue index 147."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

EXPECTED_SHA256 = "c52f48b1d08781c70e9637b9c95103dc3ae8cc637ca0ed951f74cf1d69e40b72"
EXPECTED_WIDTH = 2048
EXPECTED_HEIGHT = 1024
EXPECTED_MODE = "RGBA"
QUEUE_PATH = "textures/load/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds"
PINNED_UPSTREAM_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"
PINNED_RELEASE_PATH = "Release/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds"
PINNED_RELEASE_GIT_BLOB_SHA = "959f27e1063f249fb8d04b7ad63d8b670bdae06e"

def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source_dds")
    ap.add_argument("--out")
    args = ap.parse_args()

    p = Path(args.source_dds)
    data = p.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) < 128 or data[:4] != b"DDS ":
        raise SystemExit("FAIL_DDS_HEADER")
    header = {
        "header_size": u32(data, 4),
        "height": u32(data, 12),
        "width": u32(data, 16),
        "pitch_or_linear_size": u32(data, 20),
        "mip_count_header": u32(data, 28),
        "pixel_format_size": u32(data, 76),
        "pixel_format_flags": u32(data, 80),
        "fourcc_u32": u32(data, 84),
        "rgb_bit_count": u32(data, 88),
        "r_mask": u32(data, 92),
        "g_mask": u32(data, 96),
        "b_mask": u32(data, 100),
        "a_mask": u32(data, 104),
    }
    sha_ok = digest == EXPECTED_SHA256
    geometry_ok = header["width"] == EXPECTED_WIDTH and header["height"] == EXPECTED_HEIGHT
    result = {
        "schema_version": 15,
        "task_family": "A00303_INDEX147_CANONICAL_SOURCE_GATE",
        "queue_index": 147,
        "asset": "39BCA907",
        "queue_path": QUEUE_PATH,
        "expected": {
            "sha256": EXPECTED_SHA256,
            "width": EXPECTED_WIDTH,
            "height": EXPECTED_HEIGHT,
            "inventory_mode": EXPECTED_MODE,
            "pinned_upstream_commit": PINNED_UPSTREAM_COMMIT,
            "pinned_release_path": PINNED_RELEASE_PATH,
            "pinned_release_git_blob_sha": PINNED_RELEASE_GIT_BLOB_SHA,
        },
        "observed": {
            "path": str(p),
            "bytes": len(data),
            "sha256": digest,
            "dds_header": header,
        },
        "sha256_match": sha_ok,
        "geometry_match": geometry_ok,
        "source_identity": "PASS_EXACT_CANONICAL_SHA_AND_GEOMETRY" if sha_ok and geometry_ok else "FAIL_CANONICAL_SOURCE_IDENTITY",
        "runtime_validation": "UNTESTED",
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    if not (sha_ok and geometry_ok):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
