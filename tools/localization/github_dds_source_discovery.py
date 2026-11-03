#!/usr/bin/env python3
"""Locate stock/HD DDS already tracked in GitHub; never substitute unchecked DDS.

Reads only active A/B ROI crosswalk and the exact repo files identified by it.
Produces a SHA/format audit that downstream conversion can use without N100.
No network, no fonts, no publish or game edits.
"""
import argparse
import csv
import hashlib
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

CROSS = "localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
HD_SOURCE = "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
HD_CANDIDATES = "localization/graphics/hd_candidates"
CANDIDATE_ROOT = "localization/automation_inputs/candidate_outputs"
MAX_DDS_BYTES = 75 * 1024 * 1024


def validate_target(path):
    p = PurePosixPath(path)
    return (isinstance(path, str) and path.startswith("textures/load/")
            and p.suffix == ".dds" and len(p.parts) in (4, 5)
            and "\\" not in path and ":" not in path and ".." not in p.parts
            and (len(p.parts) == 4 or p.parts[2] in ("Keyboard", "PlayStation", "Switch", "Xbox"))
            and all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in p.parts))


def read_manifest(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 954 or len({r["roi_id"] for r in rows}) != 954:
        raise ValueError("CROSSWALK_COUNT_OR_DUPLICATE")
    by_target = defaultdict(list)
    for r in rows:
        target = r["source_dds_path"]
        if not validate_target(target):
            raise ValueError("INVALID_DDS_TARGET")
        if not re.fullmatch(r"[0-9a-f]{64}", r["source_dds_sha256"]):
            raise ValueError("UNPINNED_NATIVE_SOURCE")
        lanes = r["roles"]
        if lanes not in ("A", "B"):
            raise ValueError("BAD_ROLE")
        # Existing _RB_B logical ROI rows reference a PNG without _RB_B.
        parts = r["candidate_paths"].split("/")
        filename = parts[-1]
        if not re.fullmatch(r"Q\d{3}_[0-9a-f]{16}(?:_source)?_k\.png", filename):
            raise ValueError("BAD_CANDIDATE_FILENAME")
        if parts[-2] != lanes:
            raise ValueError("CANDIDATE_ROLE_MISMATCH")
        r["_candidate"] = f"{CANDIDATE_ROOT}/{lanes}/{filename}"
        by_target[target].append(r)
    return by_target


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def dds_header(path):
    with path.open("rb") as f:
        h = f.read(128)
    if len(h) < 128 or h[:4] != b"DDS " or struct.unpack_from("<I", h, 4)[0] != 124:
        raise ValueError("INVALID_DDS_HEADER")
    height, width = struct.unpack_from("<II", h, 12)
    masks = list(struct.unpack_from("<IIII", h, 92))
    if not (0 < width <= 8192 and 0 < height <= 8192):
        raise ValueError("INVALID_DIMENSIONS")
    return {"width": width, "height": height,
            "mips": struct.unpack_from("<I", h, 28)[0],
            "bpp": struct.unpack_from("<I", h, 88)[0],
            "pixel_flags": struct.unpack_from("<I", h, 80)[0],
            "masks": masks}


def build(root, out, list_only=False):
    root = Path(root).resolve()
    by_target = read_manifest(root / CROSS)
    targets = []
    for target, rows in sorted(by_target.items()):
        active = [r for r in rows if (root / r["_candidate"]).is_file()]
        if active:
            targets.append((target, rows, active))
    if list_only:
        # Sparse checkout patterns, never arbitrary user-supplied paths.
        for target, _, _ in targets:
            print("/" + HD_SOURCE + "/" + target)
            print("/" + HD_CANDIDATES + "/" + target)
        return
    result = {
        "schema": "outrun.github-dds-source-discovery.v1",
        "active_translation_rows": 954,
        "active_source_dds_total": len(by_target),
        "source_groups_with_imported_png": len(targets),
        "imported_translation_rows": sum(len(a) for _, _, a in targets),
        "release_approved": False, "runtime_validation": "UNTESTED",
        "results": [],
    }
    for target, rows, active in targets:
        pinned_hashes = {x["source_dds_sha256"] for x in rows}
        record = {"target": target, "imported_rows": len(active),
                  "total_rows": len(rows),
                  "native_sha256": list(sorted(pinned_hashes)),
                  "copies": []}
        for prefix in (HD_SOURCE, HD_CANDIDATES):
            rel = prefix + "/" + target
            file = root / rel
            if not file.is_file():
                continue
            if file.is_symlink():
                record["copies"].append({"path": rel, "status": "REJECT_SYMLINK"})
                continue
            if file.stat().st_size > MAX_DDS_BYTES:
                record["copies"].append({"path": rel, "status": "REJECT_OVERSIZE"})
                continue
            try:
                measured = sha_file(file)
                header = dds_header(file)
                record["copies"].append({
                    "path": rel, "status": "EXACT_NATIVE_SHA" if measured in pinned_hashes
                        else "HD_PRESENT_SHA_DIFFERENT_HOLD",
                    "sha256": measured, "bytes": file.stat().st_size,
                    "format": header})
            except (OSError, ValueError) as e:
                record["copies"].append({"path": rel, "status": type(e).__name__ + ": " + str(e)[:100]})
        if any(x["status"] == "EXACT_NATIVE_SHA" for x in record["copies"]):
            record["source_status"] = "NATIVE_EXACT_IN_GITHUB"
        elif record["copies"]:
            record["source_status"] = "HD_CANDIDATE_PRESENT_NOT_SOURCE_PROVEN"
        else:
            record["source_status"] = "NO_GITHUB_DDS"
        result["results"].append(record)
    result["status_counts"] = dict(sorted(Counter(x["source_status"] for x in result["results"]).items()))
    result["rows_by_status"] = dict(sorted(Counter({
        t: sum(x["imported_rows"] for x in result["results"] if x["source_status"] == t)
        for t in result["status_counts"]
    }).items()))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"imported_rows":result["imported_translation_rows"],
                      "source_groups":len(result["results"]),
                      "status_counts":result["status_counts"],
                      "rows_by_status":result["rows_by_status"]},ensure_ascii=False))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root",default=".")
    p.add_argument("--out", default="/tmp/out/gh-dds-source-audit.json")
    p.add_argument("--list-only",action="store_true")
    a = p.parse_args()
    build(a.repo_root, a.out, a.list_only)
