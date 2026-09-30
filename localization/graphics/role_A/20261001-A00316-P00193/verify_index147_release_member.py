#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, struct, zipfile
from pathlib import Path

EXPECTED_ARCHIVE_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
EXPECTED_ARCHIVE_SIZE = 306223257
MEMBER = "textures/load/spr_sprani_sumo_fe_cvt_Exst/39BCA907_512x256.dds"
EXPECTED_CANONICAL_SHA256 = "c52f48b1d08781c70e9637b9c95103dc3ae8cc637ca0ed951f74cf1d69e40b72"
EXPECTED_RELEASE_GIT_BLOB_SHA1 = "959f27e1063f249fb8d04b7ad63d8b670bdae06e"
EXPECTED_WIDTH = 2048
EXPECTED_HEIGHT = 1024

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("--out")
    args = ap.parse_args()
    archive = Path(args.archive)
    archive_sha = sha256_file(archive)
    archive_size = archive.stat().st_size
    if archive_sha != EXPECTED_ARCHIVE_SHA256 or archive_size != EXPECTED_ARCHIVE_SIZE:
        raise SystemExit("FAIL_PINNED_ARCHIVE_IDENTITY")
    with zipfile.ZipFile(archive) as zf:
        data = zf.read(MEMBER)
    dds_sha = hashlib.sha256(data).hexdigest()
    git_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
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
    release_lineage_ok = git_blob == EXPECTED_RELEASE_GIT_BLOB_SHA1
    geometry_ok = (
        header["width"] == EXPECTED_WIDTH
        and header["height"] == EXPECTED_HEIGHT
        and header["rgb_bit_count"] == 32
        and header["fourcc_u32"] == 0
    )
    canonical_sha_ok = dds_sha == EXPECTED_CANONICAL_SHA256
    outcome = "PASS_EXACT_CANONICAL_SOURCE" if canonical_sha_ok and geometry_ok else "SOURCE_IDENTITY_MISMATCH"
    result = {
        "schema_version": 16,
        "task_family": "A00316_INDEX147_PINNED_RELEASE_EXACT_MEMBER_IDENTITY",
        "queue_index": 147,
        "asset": "39BCA907",
        "queue_path": MEMBER,
        "archive": {"size": archive_size, "sha256": archive_sha, "pinned_identity_pass": True},
        "expected": {
            "canonical_sha256": EXPECTED_CANONICAL_SHA256,
            "release_git_blob_sha1": EXPECTED_RELEASE_GIT_BLOB_SHA1,
            "width": EXPECTED_WIDTH,
            "height": EXPECTED_HEIGHT,
            "mode": "RGBA32",
            "mip_count": 1,
        },
        "observed": {
            "member_bytes": len(data),
            "sha256": dds_sha,
            "git_blob_sha1": git_blob,
            "dds_header": header,
        },
        "release_lineage_match": release_lineage_ok,
        "geometry_match": geometry_ok,
        "canonical_sha256_match": canonical_sha_ok,
        "source_outcome": outcome,
        "candidate_authorized": outcome == "PASS_EXACT_CANONICAL_SOURCE",
        "runtime_validation": "UNTESTED",
    }
    text_out = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text_out, encoding="utf-8")
    print(text_out, end="")
    raise SystemExit(0 if outcome == "PASS_EXACT_CANONICAL_SOURCE" else 3)

if __name__ == "__main__":
    main()
