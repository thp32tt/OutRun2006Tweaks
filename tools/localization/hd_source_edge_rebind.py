#!/usr/bin/env python3
"""Propose source-SHA-pinned HD text ROI edge rebindings; NEVER change DDS.

The 8-connected native alpha>=16 component is a geometry diagnostic, NOT proof
that pixels are English text. Proposals stay TEST_ONLY pending protected-art,
English CLEAN, independent C1/C3 and real-game review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageOps
from github_ab_imagegen_atlas_batch import CROSS, ORIGINAL, load_cross, load_pinned_orientations, native_image
from hd_rework_queue import flatten_holds

SCHEMA = "outrun-hd-source-edge-rebind-proposals-v1"
REASON = "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE"
CORE_THRESHOLD = 15
MAX_PAD = 96


def propose(source: Image.Image, box, other_boxes=(), pad=64):
    """Return a conservative, non-applying proposal from source-alpha islands."""
    if not (1 <= pad <= MAX_PAD):
        raise ValueError("EDGE_PAD_OUT_OF_RANGE")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height):
        raise ValueError("EDGE_SOURCE_BOX_OUT_OF_BOUNDS")
    sx0, sy0 = max(0, x0-pad), max(0, y0-pad)
    sx1, sy1 = min(source.width, x1+pad), min(source.height, y1+pad)
    w, h = sx1-sx0, sy1-sy0
    alpha = source.getchannel("A").crop((sx0, sy0, sx1, sy1)).tobytes()
    seen = bytearray(w*h)
    seeds = []
    for x in range(x0, x1):
        seeds.extend(((y0-sy0)*w+x-sx0, (y1-1-sy0)*w+x-sx0))
    for y in range(y0, y1):
        seeds.extend(((y-sy0)*w+x0-sx0, (y-sy0)*w+x1-1-sx0))
    escaped = []
    hit_neighbor = False
    hit_search_boundary = False
    components = 0
    for first in seeds:
        if seen[first] or alpha[first] <= CORE_THRESHOLD:
            continue
        components += 1
        q = deque([first])
        seen[first] = 1
        group_out = []
        foreign = False
        clipped = False
        while q:
            key = q.popleft()
            lx, ly = key % w, key // w
            gx, gy = sx0+lx, sy0+ly
            if not (x0 <= gx < x1 and y0 <= gy < y1):
                group_out.append((gx, gy))
            if lx in (0, w-1) or ly in (0, h-1):
                clipped = True
            if any(a <= gx < c and b <= gy < d for a, b, c, d in other_boxes):
                foreign = True
            for ny in range(max(0, ly-1), min(h, ly+2)):
                for nx in range(max(0, lx-1), min(w, lx+2)):
                    nk = ny*w+nx
                    if not seen[nk] and alpha[nk] > CORE_THRESHOLD:
                        seen[nk] = 1
                        q.append(nk)
        if group_out:
            escaped.extend(group_out)
            hit_neighbor |= foreign
            hit_search_boundary |= clipped
    result = {
        "status": "NO_NATIVE_CORE_CROSSING",
        "original_bbox_xyxy": list(box),
        "proposed_bbox_xyxy": None,
        "edge_connected_components": components,
        "escaped_core_pixels": len(escaped),
        "neighbor_core_conflict": hit_neighbor,
        "scan_window_truncated": hit_search_boundary,
        "auto_apply": False,
        "release_approved": False,
    }
    if not escaped:
        return result
    if hit_search_boundary:
        result["status"] = "NEEDS_LARGER_SOURCE_CHILD_OR_ART_REVIEW"
        return result
    if hit_neighbor:
        result["status"] = "NEIGHBOR_SOURCE_ALPHA_PROTECTED"
        return result
    proposed = (min(x0, min(x for x, y in escaped)),
                min(y0, min(y for x, y in escaped)),
                max(x1, max(x for x, y in escaped)+1),
                max(y1, max(y for x, y in escaped)+1))
    if any(proposed[0] < c and a < proposed[2] and
           proposed[1] < d and b < proposed[3] for a, b, c, d in other_boxes):
        result["status"] = "PROPOSED_BBOX_INTERSECTS_OTHER_ROI"
        return result
    result["status"] = "SOURCE_COMPONENT_COORDINATE_PROPOSAL_REVIEW_ONLY"
    result["proposed_bbox_xyxy"] = list(proposed)
    return result


def build(root: Path, qa_report: Path, out: Path, pad=64):
    root, out = Path(root), Path(out)
    report = json.loads(Path(qa_report).read_text(encoding="utf-8"))
    if (report.get("schema") != "outrun.ab-imagegen-hd-strict.v2" or
            report.get("release_approved") is not False or
            report.get("runtime_validation") != "UNTESTED" or
            report.get("source_dds_missing_rows") != 0 or
            report.get("source_sha_conflict_rows") != 0):
        raise ValueError("EDGE_REBIND_STRICT_SOURCE_REPORT_REQUIRED")
    groups = load_cross(root / CROSS)
    holds, painted = flatten_holds(report)
    if sum(map(len, groups.values())) != report["active_roi_total"] or len(holds)+len(painted) != report["active_roi_total"]:
        raise ValueError("EDGE_REBIND_SOURCE_COVERAGE")
    orientations = load_pinned_orientations(root, groups)
    targets = {rid for rid, reason in holds.items() if reason == REASON}
    records = []
    for target, rows in sorted(groups.items()):
        pending = [r for r in rows if r["roi_id"] in targets]
        if not pending:
            continue
        path = root / ORIGINAL / target
        if path.is_symlink() or not path.is_file():
            raise ValueError("EDGE_REBIND_ORIGINAL_DDS_MISSING")
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if any(r["source_dds_sha256"] != sha for r in rows):
            raise ValueError("EDGE_REBIND_SOURCE_SHA_CONFLICT")
        source = native_image(raw)
        if orientations[target] == "FLIPY":
            source = ImageOps.flip(source)
        for row in sorted(pending, key=lambda item: item["roi_id"]):
            neighbors = [r["_bbox"] for r in rows if r["roi_id"] != row["roi_id"]]
            result = propose(source, row["_bbox"], neighbors, pad)
            records.append({
                "roi_id": row["roi_id"],
                "english": row["english"],
                "korean": row["korean"],
                "source_dds_path": target,
                "source_dds_sha256": sha,
                "orientation": orientations[target],
                **result,
            })
    if {r["roi_id"] for r in records} != targets:
        raise ValueError("EDGE_REBIND_HOLD_COVERAGE_MISMATCH")
    counts = dict(sorted(Counter(r["status"] for r in records).items()))
    evidence = {
        "schema": SCHEMA,
        "source_report_zip_sha256": report["zip_sha256"],
        "source_roi_total": report["active_roi_total"],
        "source_held_total": len(holds),
        "edge_hold_total": len(targets),
        "proposal_status_counts": counts,
        "cosmetic_alpha_tolerance_max": CORE_THRESHOLD,
        "native_sha_pinned": True,
        "visual_qa": "UNTESTED",
        "runtime_validation": "UNTESTED",
        "release_approved": False,
        "auto_apply": False,
        "records": records,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "source_edge_rebind_proposals.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)+"\n",
        encoding="utf-8")
    print(json.dumps({"edge_hold_total": len(targets), "status_counts": counts,
                      "release_approved": False}, ensure_ascii=False))
    return evidence


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--qa-report", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--pad", type=int, default=64)
    a = p.parse_args()
    build(Path(a.repo_root), Path(a.qa_report), Path(a.out), a.pad)


if __name__ == "__main__":
    main()
