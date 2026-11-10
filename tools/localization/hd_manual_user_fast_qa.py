#!/usr/bin/env python3
"""Fast GitHub CPU check of the exact six user-supplied Korean native-HD ROIs."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import github_ab_imagegen_atlas_batch as atlas
from hd_manual_user_import import EXPECTED, apply_user_manual_candidates


def run(root):
    root = Path(root).resolve()
    groups = atlas.load_cross(root / atlas.CROSS)
    orientations = atlas.load_pinned_orientations(root, groups)
    if apply_user_manual_candidates(root, groups) != 6:
        raise ValueError("SIX_USER_MANUAL_ROI_FILES_NOT_IMPORTED")
    targets = {target for target, rows in groups.items()
               if any(r["roi_id"] in EXPECTED for r in rows)}
    result = {
        "schema": "outrun-hd-six-user-manual-source-qa-test-only-v1",
        "release_approved": False, "runtime_validation": "UNTESTED",
        "manual_user_roi_count": 6, "manual_source_atlases": len(targets),
        "status_by_roi": {}, "source_errors": []
    }
    for target in sorted(targets):
        rows = groups[target]
        p = root / atlas.ORIGINAL / target
        if not p.is_file():
            result["source_errors"].append({"atlas": target, "reason": "SOURCE_NOT_CHECKED_OUT"})
            continue
        raw = p.read_bytes()
        expected_sha = {r["source_dds_sha256"] for r in rows}
        if len(expected_sha) != 1 or hashlib.sha256(raw).hexdigest() not in expected_sha:
            result["source_errors"].append({"atlas": target, "reason": "SHA_PINNED_SOURCE_MISMATCH"})
            continue
        try:
            native, image, clean, painted, held = atlas.process_strict_with_bc3_quarantine(
                raw, rows, root, orientations[target])
            passids = {p["roi_id"] for p in painted}
            hold_reason = {h["roi_id"]: h["reason"] for h in held}
            for row in rows:
                rid = row["roi_id"]
                if rid not in EXPECTED:
                    continue
                result["status_by_roi"][rid] = {
                    "translation": row["korean"], "atlas": target,
                    "status": "DDS_MECHANICAL_TEST_ONLY" if rid in passids else "HOLD",
                    "reason": None if rid in passids else hold_reason.get(rid, "UNKNOWN_HOLD"),
                    "candidate_sha256": EXPECTED[rid][0],
                    "stage_child_source_only": rid.endswith("17d32be0f1ec1624")
                }
        except Exception as exc:
            result["source_errors"].append({
                "atlas": target, "reason": f"{type(exc).__name__}:{str(exc)[:160]}"})
    if len(result["status_by_roi"]) + sum(
            sum(row["roi_id"] in EXPECTED for row in groups[e["atlas"]])
            for e in result["source_errors"]) != 6:
        raise ValueError("FAST_QA_MANUAL_ROI_ACCOUNTING_ERROR")
    result["mechanical_test_only_roi"] = sum(
        t["status"] == "DDS_MECHANICAL_TEST_ONLY" for t in result["status_by_roi"].values())
    result["held_or_source_error_roi"] = 6 - result["mechanical_test_only_roi"]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = run(args.repo_root)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
