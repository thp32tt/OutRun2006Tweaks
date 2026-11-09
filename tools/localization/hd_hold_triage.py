#!/usr/bin/env python3
"""Conservative native-HD HOLD diagnostics: no generation, ROI auto-PASS or DDS writes.

Joins the exact SHA-pinned 954-ROI crosswalk with the strict Atlas QA receipt.
Geometric rectangle intersections are *potential neighbors*, NEVER proof of
source-ink ownership or permission to erase any pixel.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from github_ab_imagegen_atlas_batch import CROSS, load_cross
from hd_rework_queue import flatten_holds, category

ACTIONS = {
    "ROI_OVERLAP_NEEDS_MANUAL_QA": "SOURCE_ALPHA_CONNECTED_COMPONENT_OWNER_OR_SOURCE_MASK_REQUIRED",
    "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE": "VERIFY_8_CONNECTED_SOURCE_TEXT_SPILL_AND_PROTECTED_HALO_THEN_REBIND_ROI",
    "COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD": "SPLIT_OVERBROAD_SOURCE_ROI_INTO_SHA_PINNED_TEXT_CHILDREN",
    "QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT": "SOURCE_CLEAN_PLATE_OR_TEXT_ONLY_MASK_REQUIRED",
    "QA_SOURCE_LINE_LAYOUT_UNVERIFIED": "SOURCE_LINE_SEGMENTATION_EVIDENCE_REQUIRED",
    "OPAQUE_PROTECTED_ART_HOLD": "SEPARATE_PROTECTED_ART_FROM_SOURCE_GLYPH_AND_REVIEW_CLEAN",
    "QA_BC3_MIP_CHAIN_REQUIRES_ORIGINAL_FORMAT_REBUILD": "PRESERVE_ALL_NATIVE_DXT5_MIP_LEVELS_WITH_BLOCK_PROTECTION",
    "QA_BC3_TRANSLATED_COLOR_LOSS": "BC3_EXACT_VISIBLE_GLYPH_PALETTE_OR_BLOCK_REENCODE_PROOF",
    "QA_DOWNSCALE_LOST_GLYPHS": "EXISTING_AB_PIXEL_FIT_OR_MANUAL_RGBA_KOREAN_GLYPH",
    "QA_TRANSLATION_TOO_SMALL_TO_READ": "EXISTING_AB_PIXEL_FIT_OR_MANUAL_RGBA_KOREAN_GLYPH",
}

FIELDS = ("roi_id", "reason", "category", "action", "source_dds_path",
          "source_dds_sha256", "bbox_xyxy", "english", "korean",
          "geometric_neighbor_count", "geometric_neighbors", "overlap_cluster")


def intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def classify(rows, report):
    if (report.get("schema") != "outrun.ab-imagegen-hd-strict.v2"
            or report.get("release_approved") is not False
            or report.get("runtime_validation") != "UNTESTED"
            or report.get("source_dds_missing_rows") != 0
            or report.get("source_sha_conflict_rows") != 0):
        raise ValueError("STRICT_SOURCE_QA_REPORT_NOT_VERIFIED")
    holds, painted = flatten_holds(report)
    by_id = {}
    groups = defaultdict(list)
    for row in rows:
        rid = row["roi_id"]
        box = row["_bbox"]
        if rid in by_id or len(box) != 4 or any(type(x) is not int for x in box) or not (
                0 <= box[0] < box[2] and 0 <= box[1] < box[3]):
            raise ValueError("DUPLICATE_OR_INVALID_SOURCE_ROI")
        if not isinstance(row.get("source_dds_path"), str) or not isinstance(row.get("source_dds_sha256"), str):
            raise ValueError("MISSING_SOURCE_BINDING")
        by_id[rid] = row
        groups[row["source_dds_path"]].append(row)
    if len(by_id) != report["active_roi_total"] or set(by_id) != set(holds) | painted:
        raise ValueError("SOURCE_AND_STRICT_QA_ROI_ID_MISMATCH")
    if set(holds) & painted:
        raise ValueError("SOURCE_CANNOT_BE_BOTH_PAINTED_AND_HELD")

    neighbors = defaultdict(set)
    geometric_pairs = 0
    for path, group in groups.items():
        hashes = {row["source_dds_sha256"] for row in group}
        if len(hashes) != 1:
            raise ValueError("SOURCE_DDS_SHA_CONFLICT_INSIDE_ATLAS")
        for i, first in enumerate(group):
            for second in group[i + 1:]:
                if intersects(first["_bbox"], second["_bbox"]):
                    neighbors[first["roi_id"]].add(second["roi_id"])
                    neighbors[second["roi_id"]].add(first["roi_id"])
                    geometric_pairs += 1
    overlap_ids = sorted(rid for rid, why in holds.items()
                         if why == "ROI_OVERLAP_NEEDS_MANUAL_QA")
    if any(not neighbors[rid] for rid in overlap_ids):
        raise ValueError("OVERLAP_QA_HOLD_HAS_NO_RECTANGULAR_NEIGHBORS")

    # Only connect held overlap ROIs from the SAME source atlas. Each cluster
    # remains HOLD; connected rectangles do not indicate shared source text.
    active = set(overlap_ids)
    group_of = {}
    cluster_rows = []
    for rid in overlap_ids:
        if rid in group_of:
            continue
        pending = [rid]
        members = []
        while pending:
            node = pending.pop()
            if node in group_of:
                continue
            group_of[node] = len(cluster_rows) + 1
            members.append(node)
            pending.extend(sorted(neighbors[node] & active - set(group_of)))
        cluster_rows.append(sorted(members))
    tickets = []
    for rid in sorted(holds):
        row = by_id[rid]
        why = holds[rid]
        tickets.append({
            "roi_id": rid,
            "reason": why,
            "category": category(why),
            "action": ACTIONS.get(why, "PRESERVE_HOLD_REQUIRE_SOURCE_PINNED_QA"),
            "source_dds_path": row["source_dds_path"],
            "source_dds_sha256": row["source_dds_sha256"],
            "bbox_xyxy": row["_bbox"],
            "english": row["english"],
            "korean": row["korean"],
            "geometric_neighbor_count": len(neighbors[rid]),
            "geometric_neighbors": sorted(neighbors[rid]),
            "overlap_cluster": group_of.get(rid),
            "qa_authority": "UNAPPROVED_C1_C3_AND_GAME",
        })
    reasons = Counter(holds.values())
    categories = Counter(category(reason) for reason in holds.values())
    if dict(reasons) != report["hold_roi_reason_counts"]:
        raise ValueError("QA_HOLD_BREAKDOWN_NOT_ACCOUNTED")
    return {
        "schema": "outrun-hd-hold-native-source-triage-v1",
        "status": "TICKETS_ONLY_NO_SOURCE_ERASURE_NO_FAKE_QA_PASS",
        "release_approved": False,
        "runtime_validation": "UNTESTED",
        "qa_source_zip_sha256": report.get("zip_sha256"),
        "source_roi_total": len(by_id),
        "painted_test_only": len(painted),
        "hold_total": len(holds),
        "source_dds_atlases": len(groups),
        "geometric_overlap_pairs_diagnostic_only": geometric_pairs,
        "geometric_overlap_rows_diagnostic_only": sum(bool(neighbors[rid]) for rid in by_id),
        "overlap_hold_clusters": len(cluster_rows),
        "largest_overlap_hold_clusters": [
            {"size": len(nodes), "roi_ids": nodes}
            for nodes in sorted(cluster_rows, key=lambda x: (-len(x), x))[:20]],
        "hold_reasons": dict(sorted(reasons.items())),
        "hold_categories": dict(sorted(categories.items())),
        "tickets": tickets,
    }


def write_result(result, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hold_triage.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    with (out / "hold_triage.csv").open("w", encoding="utf-8-sig", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=FIELDS)
        writer.writeheader()
        for ticket in result["tickets"]:
            writer.writerow({
                name: (json.dumps(ticket[name], ensure_ascii=False, separators=(",", ":"))
                       if name in ("bbox_xyxy", "geometric_neighbors") else
                       ("" if ticket[name] is None else ticket[name]))
                for name in FIELDS
            })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--qa-report", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.repo_root)
    groups = load_cross(root / CROSS)
    rows = [r for group in groups.values() for r in group]
    report = json.loads(Path(args.qa_report).read_text(encoding="utf-8"))
    result = classify(rows, report)
    write_result(result, args.out)
    print(json.dumps({k: result[k] for k in (
        "source_roi_total", "painted_test_only", "hold_total",
        "source_dds_atlases", "overlap_hold_clusters",
        "hold_reasons", "hold_categories")}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
