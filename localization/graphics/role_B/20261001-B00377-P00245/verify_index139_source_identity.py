#!/usr/bin/env python3
"""Fail-closed verifier for B00377 index139 source identity."""
from __future__ import annotations
import argparse, hashlib, json, struct, zipfile
from pathlib import Path

ARCHIVE_SIZE = 306223257
ARCHIVE_SHA256 = "76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
MEMBER_SUFFIX = "textures/load/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds"
EXPECTED_RELEASE_SHA256 = "4c85be80485375876cdcc6be0ebd1e5578032894a194a820b47f01b271fe4786"
EXPECTED_RELEASE_DIMENSIONS = (2048, 1024)
EXPECTED_RELEASE_BYTES = 8388736
CANONICAL_SHA256 = "45cd9acffa98e79079774c4af41f90471627f7531fa33c12ff16dc4ed9292209"
CANONICAL_DIMENSIONS = (512, 256)

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    args=ap.parse_args()
    if args.archive.stat().st_size != ARCHIVE_SIZE:
        raise SystemExit("archive size mismatch")
    observed_archive_sha=sha256_file(args.archive)
    if observed_archive_sha != ARCHIVE_SHA256:
        raise SystemExit("archive sha256 mismatch")
    with zipfile.ZipFile(args.archive) as zf:
        matches=[n for n in zf.namelist() if n.replace("\\","/").lower().endswith(MEMBER_SUFFIX.lower())]
        if len(matches) != 1:
            raise SystemExit(f"expected one exact member suffix, got {len(matches)}")
        raw=zf.read(matches[0])
    member_sha=hashlib.sha256(raw).hexdigest()
    if len(raw) != EXPECTED_RELEASE_BYTES:
        raise SystemExit("release member byte-size drift")
    if member_sha != EXPECTED_RELEASE_SHA256:
        raise SystemExit("release member sha256 drift")
    if raw[:4] != b"DDS ":
        raise SystemExit("member is not DDS")
    height=struct.unpack_from("<I", raw, 12)[0]
    width=struct.unpack_from("<I", raw, 16)[0]
    mip_count=struct.unpack_from("<I", raw, 28)[0] or 1
    if (width,height) != EXPECTED_RELEASE_DIMENSIONS:
        raise SystemExit("release DDS dimension drift")
    if member_sha == CANONICAL_SHA256 or (width,height) == CANONICAL_DIMENSIONS:
        raise SystemExit("dependency fingerprint changed: re-evaluate canonical identity; sticky result no longer valid")
    out={
        "status":"PASS_SOURCE_IDENTITY_MISMATCH_VERIFIED",
        "archive_sha256":observed_archive_sha,
        "member":matches[0],
        "member_sha256":member_sha,
        "member_dimensions":[width,height],
        "mip_count":mip_count,
        "canonical_sha256":CANONICAL_SHA256,
        "canonical_dimensions":list(CANONICAL_DIMENSIONS),
        "terminal_source_state":"SOURCE_IDENTITY_MISMATCH_PINNED_RELEASE_MEMBER",
        "runtime_validation":"UNTESTED"
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
