#!/usr/bin/env python3
"""GitHub-only immutable HD source/atlas gate for W00010 lane B.

This tool downloads only pinned files from Sonic-TV/OR2006Sprites at the
immutable commit recorded below. It does not use N100, a local clone, or a
floating branch. It validates Git blob identity, DDS header properties, and
the exact atlas sprite rectangles needed by the four even-shard assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import urllib.parse
import urllib.request
from pathlib import Path

SOURCE_REPO = "Sonic-TV/OR2006Sprites"
SOURCE_COMMIT = "a95efe01d1f136514cef94b0d9e9fd61df021754"

ASSETS = [
    {
        "index": 34,
        "asset": "B7E25BAD",
        "release_path": "Release/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",
        "release_blob_sha": "9ca9aa7e2e2528a101379257035533ea9d175b17",
        "release_bytes": 33554560,
        "expected_dimensions": [4096, 2048],
        "expected_format": "RGBA32",
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_HOLL_RANK_Exst/4x_B7E25BAD_1024x512_atlas.json",
        "atlas_blob_sha": "a6fbbfac9fd81e196b8c9a04c7efd797a0545ff9",
        "regions": {"sprite_9": [1280, 1032, 2048, 1016]},
    },
    {
        "index": 44,
        "asset": "19CEDB9",
        "release_path": "Release/spr_sprani_etc_cvt_Exst/19CEDB9_512x512.dds",
        "release_blob_sha": "2c7fd312717fc7a8a8681ef112f32756f85e0ec3",
        "release_bytes": 16777344,
        "expected_dimensions": [2048, 2048],
        "expected_format": "RGBA32",
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_etc_cvt_Exst/4x_019CEDB9_512x512_atlas.json",
        "atlas_blob_sha": "c1b0897229077f8bc5987af25f14c5b751aa3411",
        "regions": {
            "sprite_247": [0, 96, 200, 72],
            "sprite_250": [200, 96, 200, 72],
            "sprite_251": [400, 96, 120, 72],
            "sprite_252": [520, 96, 120, 72],
            "sprite_246": [0, 168, 280, 104],
            "sprite_261": [280, 168, 280, 104],
            "sprite_262": [560, 168, 216, 104],
            "sprite_263": [776, 168, 200, 104],
            "sprite_272": [1728, 184, 200, 88],
            "sprite_282": [1840, 304, 136, 88],
            "sprite_336": [1824, 1176, 200, 72],
            "sprite_352": [288, 1408, 208, 144],
            "sprite_353": [496, 1412, 208, 140],
        },
    },
    {
        "index": 52,
        "asset": "A8CE339F",
        "release_path": "Release/spr_sprani_fight_Exst/A8CE339F_512x256.dds",
        "release_blob_sha": "53f75d347682c7b5f436a6d45dc3e1950a42b5eb",
        "release_bytes": 2097280,
        "expected_dimensions": [2048, 1024],
        "expected_format": "DXT5",
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_fight_Exst/4x_A8CE339F_512x256_atlas.json",
        "atlas_blob_sha": "67c08611ea816fb273c0fcdca3b9867b93a0b7fd",
        "regions": {
            "sprite_24": [0, 304, 776, 104],
            "sprite_25": [776, 304, 776, 104],
            "sprite_26": [0, 200, 504, 104],
        },
    },
    {
        "index": 172,
        "asset": "6C9B3611",
        "release_path": "Release/spr_sprani_sumo_fe_cvt_Exst/6C9B3611_256x256.dds",
        "release_blob_sha": "56a60db00d93f2371ba480510e9086d20c5b5800",
        "release_bytes": 4194432,
        "expected_dimensions": [1024, 1024],
        "expected_format": "RGBA32",
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_6C9B3611_256x256_atlas.json",
        "atlas_blob_sha": "ec37221aeaa00a9eb3f1d1362b3b5985de351feb",
        "regions": {"sprite_788": [0, 136, 748, 888]},
    },
]


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def raw_url(path: str) -> str:
    quoted = urllib.parse.quote(path, safe="/")
    return f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{quoted}"


def fetch(path: str) -> bytes:
    req = urllib.request.Request(raw_url(path), headers={"User-Agent": "OR2006-Korean-localization-source-gate"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def dds_header(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("invalid DDS")
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    pitch_or_linear = struct.unpack_from("<I", data, 20)[0]
    mipmaps = struct.unpack_from("<I", data, 28)[0] or 1
    fourcc = data[84:88]
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    masks = list(struct.unpack_from("<IIII", data, 92))
    if fourcc == b"DXT5":
        fmt = "DXT5"
    elif fourcc == b"\0\0\0\0" and rgb_bits == 32:
        fmt = "RGBA32"
    else:
        fmt = f"UNKNOWN({fourcc!r},{rgb_bits})"
    return {
        "width": width,
        "height": height,
        "pitch_or_linear": pitch_or_linear,
        "mipmaps": mipmaps,
        "format": fmt,
        "rgb_bits": rgb_bits,
        "masks": masks,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    results = []
    failures = []
    for spec in ASSETS:
        dds = fetch(spec["release_path"])
        atlas_bytes = fetch(spec["atlas_path"])
        dds_blob = git_blob_sha(dds)
        atlas_blob = git_blob_sha(atlas_bytes)
        header = dds_header(dds)
        atlas = json.loads(atlas_bytes.decode("utf-8"))
        regions = {r["name"]: r["rect"] for r in atlas["regions"]}

        checks = {
            "release_blob_sha": dds_blob == spec["release_blob_sha"],
            "release_size": len(dds) == spec["release_bytes"],
            "dimensions": [header["width"], header["height"]] == spec["expected_dimensions"],
            "format": header["format"] == spec["expected_format"],
            "mipmaps": header["mipmaps"] == 1,
            "atlas_blob_sha": atlas_blob == spec["atlas_blob_sha"],
            "atlas_regions": all(regions.get(name) == rect for name, rect in spec["regions"].items()),
        }
        if not all(checks.values()):
            failures.append({"index": spec["index"], "asset": spec["asset"], "checks": checks})

        results.append({
            "index": spec["index"],
            "asset": spec["asset"],
            "release_path": spec["release_path"],
            "release_git_blob_sha": dds_blob,
            "release_sha256": hashlib.sha256(dds).hexdigest(),
            "release_bytes": len(dds),
            "dds": header,
            "atlas_path": spec["atlas_path"],
            "atlas_git_blob_sha": atlas_blob,
            "regions": {name: regions.get(name) for name in spec["regions"]},
            "checks": checks,
        })

    out = {
        "schema_version": 1,
        "source_repository": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "assets": results,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "candidate_dds_written": False,
        "runtime_validation": "UNTESTED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
