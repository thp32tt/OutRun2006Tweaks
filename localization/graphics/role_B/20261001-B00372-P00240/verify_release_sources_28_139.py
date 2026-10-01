#!/usr/bin/env python3
"""Deterministic pinned-release source verifier for B00372 indices 28 and 139.

This script intentionally performs only source-identity checks. It does not render
or modify DDS candidates. It is safe to rerun when the pinned release bundle is
available to a binary-capable runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path

PINNED_ARCHIVE = {
    "name": "OR2-HD-GUI-v0.25.10a.zip",
    "sha256": "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958",
    "size_bytes": 306223257,
}

TARGETS = [
    {
        "index": 28,
        "asset": "A05BF610",
        "member": "textures/load/spr_sprani_CLAR_RANK_Exst/A05BF610_512x512.dds",
        "canonical_sha256": "ede0367228e0a97bbbdbc58f71c03ff0e044826e17fd7697b74d852aff7a3e64",
        "canonical_width": 2047,
        "canonical_height": 2048,
    },
    {
        "index": 139,
        "asset": "313DB8CB",
        "member": "textures/load/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds",
        "canonical_sha256": "45cd9acffa98e79079774c4af41f90471627f7531fa33c12ff16dc4ed9292209",
        "canonical_width": 512,
        "canonical_height": 256,
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_dds_header(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        return {"valid_dds": False}
    header_size = struct.unpack_from("<I", data, 4)[0]
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    mip_count = struct.unpack_from("<I", data, 28)[0] or 1
    pf_size = struct.unpack_from("<I", data, 76)[0]
    pf_flags = struct.unpack_from("<I", data, 80)[0]
    fourcc = data[84:88]
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    fourcc_text = fourcc.decode("ascii", errors="replace").rstrip("\x00")
    return {
        "valid_dds": header_size == 124 and pf_size == 32,
        "width": width,
        "height": height,
        "mip_count": mip_count,
        "pixel_format_flags": pf_flags,
        "fourcc": fourcc_text,
        "rgb_bit_count": rgb_bits,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "archive",
        nargs="?",
        default="/mnt/data/OR2-HD-GUI-v0.25.10a.zip",
        help="Path to the pinned v0.25.10a release ZIP",
    )
    ap.add_argument("--output", help="Optional JSON output path")
    args = ap.parse_args()

    archive = Path(args.archive)
    result = {
        "schema": "outrun-b00372-release-source-verifier-result-v1",
        "archive": str(archive),
        "pinned": PINNED_ARCHIVE,
        "targets": [],
    }

    if not archive.is_file():
        result["archive_status"] = "SOURCE_TRANSPORT_MISS_LOCAL_FILE_ABSENT"
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        print(payload)
        if args.output:
            Path(args.output).write_text(payload + "\n", encoding="utf-8")
        return 2

    size = archive.stat().st_size
    digest = sha256_file(archive)
    result["observed_archive_size_bytes"] = size
    result["observed_archive_sha256"] = digest
    if size != PINNED_ARCHIVE["size_bytes"] or digest != PINNED_ARCHIVE["sha256"]:
        result["archive_status"] = "PINNED_RELEASE_BUNDLE_FINGERPRINT_MISMATCH"
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        print(payload)
        if args.output:
            Path(args.output).write_text(payload + "\n", encoding="utf-8")
        return 3

    result["archive_status"] = "PASS_EXACT_PINNED_RELEASE_BUNDLE"

    with zipfile.ZipFile(archive, "r") as zf:
        names = set(zf.namelist())
        for target in TARGETS:
            row = dict(target)
            member = target["member"]
            if member not in names:
                row["status"] = "SOURCE_TRANSPORT_MISS_RELEASE_MEMBER_ABSENT"
                result["targets"].append(row)
                continue

            data = zf.read(member)
            row["observed_size_bytes"] = len(data)
            row["observed_sha256"] = hashlib.sha256(data).hexdigest()
            row["dds"] = parse_dds_header(data)
            sha_ok = row["observed_sha256"] == target["canonical_sha256"]
            dim_ok = (
                row["dds"].get("valid_dds") is True
                and row["dds"].get("width") == target["canonical_width"]
                and row["dds"].get("height") == target["canonical_height"]
            )
            row["sha_identity_match"] = sha_ok
            row["canonical_dimensions_match"] = dim_ok
            if sha_ok and dim_ok:
                row["status"] = "PASS_EXACT_CANONICAL_SOURCE_IDENTITY"
            else:
                row["status"] = "SOURCE_IDENTITY_MISMATCH"
            result["targets"].append(row)

    all_pass = all(
        x.get("status") == "PASS_EXACT_CANONICAL_SOURCE_IDENTITY"
        for x in result["targets"]
    )
    result["overall"] = (
        "PASS_ALL_EXACT_CANONICAL_SOURCE_IDENTITIES"
        if all_pass
        else "FAIL_CLOSED_ONE_OR_MORE_RELEASE_SOURCE_IDENTITIES_NOT_CANONICAL"
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    return 0 if all_pass else 4


if __name__ == "__main__":
    sys.exit(main())
