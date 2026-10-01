#!/usr/bin/env python3
"""Audit B-owned font-pipeline atlas bindings and pinned HD source identity.

The tool is fail-closed and does not create or modify DDS files. It binds each
B-shard font queue row to the stock runtime descriptor/resource handle, then
optionally verifies the pinned v0.25.10a release ZIP and exact member identity.
A source identity PASS does not authorize font replacement: real KoreanK3Trace
font-state usage is still required before choosing a page-switch/repurpose slot.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import zipfile
from pathlib import Path

EXPECTED_ZIP_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
EXPECTED_ZIP_SIZE = 306223257
PINNED_COMMIT = "55f67a813dd3603d201d0be0da47c071965f53a4"

TARGETS = {
    16: {
        "asset_hash": "23DDB6EC",
        "release_member": "textures/load/spr_font_xst/23DDB6EC_512x512.dds",
        "pinned_direct_blob_sha1": "a83c1afc529a906d437514d6bd55971888dee099",
    },
    19: {
        "asset_hash": "B3ED3652",
        "release_member": "textures/load/spr_font_xst/B3ED3652_512x256.dds",
        "pinned_direct_blob_sha1": "3209996de4248741b513af43e4570c10e037e95d",
    },
    22: {
        "asset_hash": "E86D77E8",
        "release_member": "textures/load/spr_font_xst/E86D77E8_256x128.dds",
        "pinned_direct_blob_sha1": "1fc96888d3089639c086cd9245944cf0abc019bf",
    },
}


def csv_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def parse_dds(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("not a complete DDS header")
    hdr = data[4:128]
    size, flags, height, width, pitch_or_linear, depth, mip_count = struct.unpack_from("<7I", hdr, 0)
    if size != 124:
        raise ValueError(f"unexpected DDS header size: {size}")
    pf_size, pf_flags, fourcc, rgb_bits, rmask, gmask, bmask, amask = struct.unpack_from("<II4sIIIII", hdr, 72)
    if pf_size != 32:
        raise ValueError(f"unexpected DDS pixel format size: {pf_size}")
    fourcc_text = fourcc.decode("ascii", "replace").rstrip("\0")
    fmt = fourcc_text if fourcc_text else f"RGBA{rgb_bits}"
    return {
        "width": width,
        "height": height,
        "format": fmt,
        "mip_count": mip_count or 1,
        "pitch_or_linear": pitch_or_linear,
        "header128_sha256": hashlib.sha256(data[:128]).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--release-zip", type=Path)
    args = parser.parse_args()

    root = args.repo_root
    queue = {int(r["index"]): r for r in csv_rows(root / "localization/graphics/asset_queue.csv")}
    inventory = {r["path"]: r for r in csv_rows(root / "localization/graphics/inventory.csv")}
    stock = json.loads((root / "localization/font/stock_font_map.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "localization/font/hangul_glyph_manifest.json").read_text(encoding="utf-8"))
    descriptors = {d["dds_hash"]: d for d in stock["descriptors"]}

    release = None
    zf = None
    if args.release_zip:
        release = {
            "path": str(args.release_zip),
            "size": args.release_zip.stat().st_size,
            "sha256": sha256_file(args.release_zip),
        }
        release["identity"] = (
            "PASS_EXACT_PINNED_BUNDLE"
            if release["size"] == EXPECTED_ZIP_SIZE and release["sha256"] == EXPECTED_ZIP_SHA256
            else "FAIL_PINNED_BUNDLE_IDENTITY"
        )
        if release["identity"] != "PASS_EXACT_PINNED_BUNDLE":
            raise SystemExit(json.dumps(release, indent=2))
        zf = zipfile.ZipFile(args.release_zip, "r")

    out = {
        "schema": "outrun-b00370-b-owned-font-pipeline-static-source-crosswalk-v1",
        "pinned_release": {
            "tag": "v0.25.10a",
            "commit": PINNED_COMMIT,
            "expected_zip_sha256": EXPECTED_ZIP_SHA256,
            "expected_zip_size": EXPECTED_ZIP_SIZE,
            "verified": release,
        },
        "manifest": {
            "glyph_count": manifest["glyph_count"],
            "page_count": manifest["page_count"],
            "page_capacity": manifest["page_capacity"],
            "grid": manifest["grid"],
        },
        "targets": [],
    }

    try:
        for index, spec in TARGETS.items():
            q = queue[index]
            if q["action"] != "font_pipeline" or q["artwork_status"] != "blocked_runtime_font":
                raise ValueError(f"queue state changed for index {index}")
            if spec["asset_hash"] not in q["path"]:
                raise ValueError(f"asset hash/path mismatch for index {index}")

            inv = inventory[q["path"]]
            desc = descriptors[spec["asset_hash"]]
            stock_w, stock_h = desc["dds_size"]
            hd_w, hd_h = int(inv["width"]), int(inv["height"])
            target = {
                "index": index,
                "path": q["path"],
                "asset_hash": spec["asset_hash"],
                "queue_status": q["artwork_status"],
                "canonical_inventory": {
                    "sha256": inv["sha256"],
                    "width": hd_w,
                    "height": hd_h,
                    "decoded_mode": inv["mode"],
                    "category": inv["category"],
                },
                "stock_runtime_descriptor": {
                    "descriptor_index": desc["descriptor_index"],
                    "resource_handle": desc["resource_handle"],
                    "cell": desc["cell"],
                    "base_code": desc["base_code"],
                    "letter_spacing": desc["letter_spacing"],
                    "stock_dds_size": desc["dds_size"],
                    "stock_dds_format": desc["dds_format"],
                },
                "inventory_to_stock_dimension_ratio": [hd_w / stock_w, hd_h / stock_h],
                "static_crosswalk": "PASS",
                "runtime_font_handle_usage": "BLOCKED_UNTIL_REAL_TRACE",
            }

            if zf is not None:
                data = zf.read(spec["release_member"])
                parsed = parse_dds(data)
                member_sha = hashlib.sha256(data).hexdigest()
                member_git_sha = git_blob_sha1(data)
                if member_git_sha != spec["pinned_direct_blob_sha1"]:
                    raise ValueError(f"pinned direct/release Git blob mismatch for index {index}")
                exact = member_sha == inv["sha256"]
                target["source_identity"] = {
                    "pinned_direct": {
                        "path": "Release/" + spec["release_member"].split("textures/load/", 1)[1],
                        "git_blob_sha1": spec["pinned_direct_blob_sha1"],
                        "release_member_git_blob_match": True,
                    },
                    "release_member": {
                        "path": spec["release_member"],
                        "bytes": len(data),
                        "sha256": member_sha,
                        **parsed,
                    },
                    "canonical_sha256_match": exact,
                    "outcome": "SOURCE_ACQUIRED_EXACT_CANONICAL" if exact else "SOURCE_IDENTITY_MISMATCH",
                }
            out["targets"].append(target)
    finally:
        if zf is not None:
            zf.close()

    out["conclusion"] = {
        "static_descriptor_crosswalk_complete": True,
        "safe_repurpose_inferred_from_static_data": False,
        "candidate_dds_modified": False,
        "required_next": (
            "Collect real KoreanK3Trace font_state usage on target screens and bind "
            "actual resource-handle activity before selecting any Korean atlas/page-switch target."
        ),
        "runtime_validation": "UNTESTED",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
