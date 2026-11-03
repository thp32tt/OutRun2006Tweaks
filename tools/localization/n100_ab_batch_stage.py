#!/usr/bin/env python3
"""Stage up to N exact A/B ImageGen PNGs into a Git checkout on N100.

This is intentionally lightweight: CSV read, path validation, SHA256 and
byte-for-byte copy only. No OCR, Pillow, DDS processing, rendering or QA.
The Git checkout remains the destination/SSOT; this helper only prepares files
for one ordinary git add/commit/push batch.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from pathlib import Path, PurePosixPath

CROSS = "localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
DEST = "localization/automation_inputs/candidate_outputs"
SOURCE_ROOT = Path("/home/chatgpt-runner2/work/image-src/text_roi_batches/candidate_outputs")
MAX_BYTES = 4 * 1024 * 1024
ACTIVE_TOTAL = 954


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_basename(name: str) -> bool:
    return (
        isinstance(name, str)
        and name
        and Path(name).name == name
        and "/" not in name
        and "\\" not in name
        and name.lower().endswith(".png")
        and ".." not in name
    )


def load_rows(repo: Path) -> list[dict]:
    path = repo / CROSS
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != ACTIVE_TOTAL:
        raise SystemExit(f"ACTIVE_CROSSWALK_COUNT_CHANGED:{len(rows)}")
    if len({r.get("roi_id") for r in rows}) != ACTIVE_TOTAL:
        raise SystemExit("ACTIVE_CROSSWALK_ROI_NOT_UNIQUE")

    out = []
    for row in rows:
        role = row.get("roles")
        if role not in ("A", "B"):
            raise SystemExit("INVALID_ROLE:" + str(row.get("roi_id")))
        raw = row.get("candidate_paths", "")
        prefix = f"/home/chatgpt-runner2/work/image-src/text_roi_batches/candidate_outputs/{role}/"
        if not raw.startswith(prefix):
            raise SystemExit("CANDIDATE_PATH_OUTSIDE_ALLOWED_ROOT:" + str(row.get("roi_id")))
        basename = raw[len(prefix):]
        if not safe_basename(basename):
            raise SystemExit("UNSAFE_CANDIDATE_BASENAME:" + str(row.get("roi_id")))
        out.append(
            {
                "roi_id": row["roi_id"],
                "role": role,
                "basename": basename,
                "src": SOURCE_ROOT / role / basename,
                "dst": repo / DEST / role / basename,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    if not 1 <= args.limit <= 200:
        raise SystemExit("LIMIT_MUST_BE_1_TO_200")

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        raise SystemExit("REPO_NOT_GIT_CHECKOUT")

    staged = []
    missing_source = []
    existing = 0

    for row in load_rows(repo):
        dst = row["dst"]
        src = row["src"]
        if dst.is_file():
            existing += 1
            continue
        if not src.is_file() or src.is_symlink():
            missing_source.append(
                {"roi_id": row["roi_id"], "role": row["role"], "basename": row["basename"]}
            )
            continue
        size = src.stat().st_size
        if size <= 0 or size > MAX_BYTES:
            raise SystemExit(f"SOURCE_SIZE_INVALID:{src}:{size}")

        src_sha = sha256(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name("." + dst.name + ".tmp-stage")
        if tmp.exists():
            tmp.unlink()
        shutil.copyfile(src, tmp)
        os.chmod(tmp, 0o644)
        if tmp.stat().st_size != size or sha256(tmp) != src_sha:
            tmp.unlink(missing_ok=True)
            raise SystemExit("BYTE_COPY_VERIFY_FAILED:" + str(src))
        os.replace(tmp, dst)
        if sha256(dst) != src_sha:
            raise SystemExit("DEST_READBACK_SHA_FAILED:" + str(dst))

        staged.append(
            {
                "roi_id": row["roi_id"],
                "role": row["role"],
                "basename": row["basename"],
                "relative_path": str(dst.relative_to(repo)),
                "size": size,
                "sha256": src_sha,
            }
        )
        if len(staged) >= args.limit:
            break

    report = {
        "schema": "outrun.n100-ab-byte-stage.v1",
        "active_total": ACTIVE_TOTAL,
        "existing_before_batch": existing,
        "staged_count": len(staged),
        "staged": staged,
        "missing_source_count_seen": len(missing_source),
        "missing_source_sample": missing_source[:20],
        "processing": "COPY_SHA_ONLY_NO_IMAGE_OR_DDS_WORK",
    }
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.report:
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
