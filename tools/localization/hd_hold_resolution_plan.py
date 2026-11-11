#!/usr/bin/env python3
"""Accountable, source-bound HOLD repair worklist after original/protected mask split.

No ROI in this file is automatically approved. The worklist identifies the
next *specific* source-protected action and points to existing masks/clean-only
previews, so later source-child QA does not regenerate A/B lettering.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from github_ab_imagegen_atlas_batch import CROSS, load_cross
from hd_rework_queue import flatten_holds
from hd_source_protection_evidence import SCHEMA

REPAIR = {
    "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE":
        ("SOURCE_EDGE_REBIND", "Prove text component across ROI edge; expand only within original source and exclude neighboring art"),
    "QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT":
        ("OPAQUE_CLEAN_MASK", "Extract original text independently of opaque background; require verified clean plate"),
    "COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD":
        ("NATIVE_SOURCE_CHILD_SPLIT", "Split source-bound coarse ROI into independently identified text children; no full-rectangle erase"),
    "QA_BC3_MIP_CHAIN_REQUIRES_ORIGINAL_FORMAT_REBUILD":
        ("BC3_MIP_CODEC", "Patch every native mip level, preserving original DXT5 blocks outside source text"),
    "QA_BC3_SAVED_PROTECTED_ATLAS_PIXEL_CHANGED":
        ("BC3_PROTECTED_BLOCK", "Preserve original protected BC3 palette/indices bitwise and rerun native pixel check"),
    "QA_BC3_TRANSLATED_COLOR_LOSS":
        ("BC3_COLOR_PALETTE", "Try exact source-compatible BC3 block palette without changing protected pixels"),
    "QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED":
        ("AB_GLYPH_REFLOW", "Reflow existing A/B alpha glyph components to original HD line count"),
}
PRIORITY_Q = ("Q043", "Q044", "Q050", "Q051", "Q057", "Q032", "Q049")


def action_for(reason, mask):
    """Return concrete, conservative repair lane based only on source evidence."""
    if reason == "ROI_OVERLAP_NEEDS_MANUAL_QA":
        if mask is None:
            raise ValueError("OVERLAP_SOURCE_MASK_EVIDENCE_MISSING")
        owned = mask["exclusive_anchored_component_pixels"]
        uncertain = mask["ambiguous_component_pixels"]
        if owned and not uncertain:
            return ("SOURCE_CHILD_ALPHA_CLEAN_REVIEW",
                    "Proof-check complete English glyph coverage from owned islands; preserve all protected pixels before bounded candidate fit")
        if owned and uncertain:
            return ("MIXED_OWNER_ALPHA_SPLIT_REVIEW",
                    "Keep ambiguous original ink intact; isolate owned text and verify English completeness before any DDS change")
        if uncertain:
            return ("AMBIGUOUS_SOURCE_COMPONENT_REVIEW",
                    "Resolve native shared alpha with exact source child coordinates or independent clean mask; no owner guess")
        return ("SOURCE_OWNER_EVIDENCE_REQUIRED",
                "No unique native owner; require source-bound manual child/clean proof")
    return REPAIR.get(reason, ("NEEDS_SOURCE_BOUND_REVIEW",
                               "Protect original art and resolve strict QA failure without reusing an unverified loose crop"))


def make_worklist(rows, held, painted, evidence, source_report_sha):
    if (evidence.get("schema") != SCHEMA or
            evidence.get("release_approved") is not False or
            evidence.get("runtime_validation") != "UNTESTED" or
            evidence.get("source_report_zip_sha256") != source_report_sha):
        raise ValueError("MASK_EVIDENCE_SOURCE_SHA_OR_QA_UNVERIFIED")
    lookup = {r["roi_id"]: r for r in rows}
    if (len(lookup) != len(rows) or set(lookup) != set(held) | set(painted)
            or set(held) & set(painted)):
        raise ValueError("SOURCE_WORKLIST_ROI_COVERAGE_ERROR")
    masks = {m["roi_id"]: m for m in evidence["tickets"]}
    overlap = {rid for rid, reason in held.items() if reason == "ROI_OVERLAP_NEEDS_MANUAL_QA"}
    if set(masks) != overlap or len(masks) != len(evidence["tickets"]):
        raise ValueError("OVERLAP_MASK_WORKLIST_NOT_COMPLETE")
    tasks = []
    for rid, reason in held.items():
        row = lookup[rid]
        mask = masks.get(rid)
        if mask and (mask["source_dds_sha256"] != row["source_dds_sha256"]
                     or mask["source_dds_path"] != row["source_dds_path"]
                     or mask["bbox_xyxy"] != row["_bbox"]):
            raise ValueError("MASK_CROSSWALK_SOURCE_PIN_CONFLICT")
        lane, instruction = action_for(reason, mask)
        source_evidence = mask or {}
        owned = source_evidence.get("exclusive_anchored_component_pixels", 0)
        ambiguous = source_evidence.get("ambiguous_component_pixels", 0)
        full = source_evidence.get("native_alpha_core_pixels", 0)
        q = rid.split("_", 1)[0]
        tasks.append({
            "roi_id": rid,
            "source_dds_path": row["source_dds_path"],
            "source_dds_sha256": row["source_dds_sha256"],
            "bbox_xyxy": row["_bbox"],
            "english": row["english"],
            "korean": row["korean"],
            "reason": reason,
            "repair_lane": lane,
            "next_action": instruction,
            "source_native_owner_pixels": owned,
            "protected_or_ambiguous_pixels": source_evidence.get("protected_or_unclaimed_pixels", 0),
            "ambiguous_pixels": ambiguous,
            "source_owner_coverage_ratio": round(owned / full, 6) if full else 0,
            "visual_evidence_files": source_evidence.get("mask_pngs", {}),
            "needs_exact_english_glyph_coverage_check": bool(owned),
            "auto_dds_approval": False,
            "runtime_validation": "UNTESTED",
            "priority": (PRIORITY_Q.index(q) if q in PRIORITY_Q else 20),
        })
    tasks.sort(key=lambda t: (t["priority"], 0 if t["source_native_owner_pixels"] else 1,
                              -t["source_owner_coverage_ratio"], t["roi_id"]))
    counts = Counter(x["repair_lane"] for x in tasks)
    if len(tasks) != len(held):
        raise ValueError("HOLD_WORKLIST_ROW_MISMATCH")
    return {
        "schema": "outrun-hd-source-protected-hold-resolution-worklist-v1",
        "release_approved": False,
        "runtime_validation": "UNTESTED",
        "source_report_zip_sha256": source_report_sha,
        "active_roi_total": len(rows),
        "painted_test_only": len(painted),
        "hold_total": len(tasks),
        "partial_mask_candidate_rows": sum(bool(t["source_native_owner_pixels"]) for t in tasks),
        "repair_lane_counts": dict(sorted(counts.items())),
        "tasks": tasks,
    }


def write_worklist(plan, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hd_hold_resolution_worklist.json").write_text(
        json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    fields = ("roi_id", "repair_lane", "reason", "priority", "source_dds_path",
              "source_dds_sha256", "bbox_xyxy", "english", "korean",
              "source_native_owner_pixels", "protected_or_ambiguous_pixels",
              "ambiguous_pixels", "source_owner_coverage_ratio", "next_action")
    with (out / "hd_hold_resolution_worklist.csv").open(
            "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for task in plan["tasks"]:
            writer.writerow({name: (json.dumps(task[name], ensure_ascii=False)
                                    if name == "bbox_xyxy" else task[name])
                             for name in fields})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--qa-report", required=True)
    parser.add_argument("--source-evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root)
    groups = load_cross(root / CROSS)
    rows = [r for g in groups.values() for r in g]
    report = json.loads(Path(args.qa_report).read_text(encoding="utf-8"))
    held, painted = flatten_holds(report)
    evidence = json.loads(Path(args.source_evidence).read_text(encoding="utf-8"))
    result = make_worklist(rows, held, painted, evidence, report["zip_sha256"])
    write_worklist(result, args.out)
    print(json.dumps({k: result[k] for k in ("active_roi_total",
        "painted_test_only", "hold_total", "partial_mask_candidate_rows",
        "repair_lane_counts")}, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
