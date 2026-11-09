#!/usr/bin/env python3
"""GitHub-only, exact-HD-source QA HOLD -> bounded A/B ImageGen rework tickets.

Never marks a candidate generated, reviewed, or approved. All evidence is
source-bound; no old low-resolution tiles or guessed backgrounds are used.
"""
import argparse
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path
from PIL import Image, ImageOps
import github_ab_imagegen_atlas_batch as atlas

POLICY = "hd-existing-ab-salvage-first-v2-20261105"
MAX_ACTIVE = 8
MAX_PER_ROLE = 4
MAX_REF_BYTES = 650 * 1024
MAX_REF_SIDE = 4096
# ImageGen is a last-resort fallback. Existing A/B pixels are deterministically
# padded/reflowed/downscaled by hd_strict_qa before any queue item can reach here.
REGEN_REASONS = (
    "QA_CANDIDATE", "QA_CANDIDATE_UNREADABLE", "QA_CANDIDATE_INVISIBLE",
    "QA_CANDIDATE_PNG_GEOMETRY", "QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED",
    "QA_DOWNSCALE_LOST_GLYPHS", "QA_TRANSLATION_TOO_SMALL_TO_READ",
)
# An ImageGen text-only replacement cannot erase source English when the DDS
# source alpha also contains opaque background, artwork, or mixed line shapes.
# These need a separately source-pinned CLEAN/segmentation mask; never spend
# another A/B generation request on them without that missing evidence.
CLEAN_SOURCE_REASONS = (
    "QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT",
    "QA_SOURCE_LINE_LAYOUT_UNVERIFIED",
    "OPAQUE_PROTECTED_ART_HOLD",
)
NOT_GENERATION = (
    "DDS_NOT_", "SOURCE_DDS_", "QA_NATIVE_DDS_", "ROI_OVERLAP_",
    "COARSE_ROI_", "AB_PNG_NOT_YET_IMPORTED", "QA_NATIVE_HD_ROI_",
    "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE",
)


def flatten_holds(report):
    """Identity-preserving flattening; no phantom PASS or dropped ROI."""
    holds = {}
    for item in report.get("holds", []):
        if "details" in item:
            for d in item["details"]:
                if d["roi_id"] in holds:
                    raise ValueError("DUPLICATE_HOLD_ROI")
                holds[d["roi_id"]] = d["reason"]
        else:
            ids = item.get("roi_ids", [])
            if not ids:
                raise ValueError("UNIDENTIFIED_ATLAS_HOLD")
            for rid in ids:
                if rid in holds:
                    raise ValueError("DUPLICATE_HOLD_ROI")
                holds[rid] = item["reason"]
    for atlas_item in report.get("generated", []):
        for d in atlas_item.get("holds", []):
            rid = d["roi_id"]
            if rid in holds:
                raise ValueError("DUPLICATE_HOLD_ROI")
            holds[rid] = d["reason"]
    for d in report.get("pending_import_holds", []):
        rid = d["roi_id"]
        if rid in holds:
            raise ValueError("DUPLICATE_HOLD_ROI")
        holds[rid] = d["reason"]
    good = set()
    for a in report.get("generated", []):
        for p in a.get("painted", []):
            rid = p["roi_id"]
            if rid in good or rid in holds:
                raise ValueError("DUPLICATE_PAINTED_OR_HOLD")
            good.add(rid)
    if len(good) != report["translated_roi_generated"]:
        raise ValueError("PAINTED_COUNT_DIFFERENT")
    if len(good) + len(holds) != report["active_roi_total"]:
        raise ValueError("ROI_TOTAL_NOT_ACCOUNTED")
    return holds, good


def category(reason):
    if reason.startswith(CLEAN_SOURCE_REASONS):
        return "SOURCE_CLEAN_MASK_OR_SEGMENTATION_HOLD"
    if reason.startswith(NOT_GENERATION):
        return "ENGINE_OR_COORDINATE_HOLD"
    if reason.startswith(REGEN_REASONS):
        return "AB_IMAGE_AND_CLEAN_REWORK"
    return "EVIDENCE_REVIEW_HOLD"


def priority(row, reason):
    rid = row["roi_id"]
    # User-reported defects: menu, Stage/Ranks and shared HUD.
    q = rid.split("_")[0]
    important = ("Q044", "Q043", "Q049", "Q050", "Q051", "Q032", "Q057")
    p = important.index(q) if q in important else 20
    if "CANDIDATE" in reason:
        p -= 1
    return (p, q, rid)


def safe_hd_reference(root, row, plan, output):
    target = row["source_dds_path"]
    proof = plan.get(target)
    if proof is None:
        raise ValueError("REF_SOURCE_NOT_PINNED")
    path = root / atlas.ORIGINAL / target
    if not path.is_file() or path.is_symlink():
        raise ValueError("REF_ORIGINAL_DDS_MISSING")
    raw = path.read_bytes()
    # load_pinned_orientations returns {source_dds_path: orientation_string};
    # crosswalk already carries the SHA; never treat orientation as a dict.
    if atlas.sha(raw) != row["source_dds_sha256"] or proof not in ("NORMAL","FLIPY"):
        raise ValueError("REF_ORIGINAL_DDS_SHA_CONFLICT")
    im = atlas.native_image(raw)
    if plan[target] == "FLIPY":
        im = ImageOps.flip(im)
    x0, y0, x1, y1 = row["_bbox"]
    if not (0 <= x0 < x1 <= im.width and 0 <= y0 < y1 <= im.height):
        raise ValueError("REF_NATIVE_HD_BOX_OUT_OF_BOUNDS")
    margin = 8
    box = (max(0,x0-margin),max(0,y0-margin),
           min(im.width,x1+margin),min(im.height,y1+margin))
    width, height = box[2]-box[0], box[3]-box[1]
    if width > MAX_REF_SIDE or height > MAX_REF_SIDE:
        raise ValueError("REF_HD_CROP_TOO_LARGE")
    ref = im.crop(box)
    b = io.BytesIO()
    ref.save(b, "PNG", optimize=True)
    data = b.getvalue()
    if len(data) > MAX_REF_BYTES:
        raise ValueError("REF_HD_CROP_OVER_GITHUB_CONTENTS_LIMIT")
    output.write_bytes(data)
    return {
        "width": width, "height": height, "source_native_size": [im.width,im.height],
        "source_box_xyxy": list(box), "roi_within_reference_xyxy":
            [x0-box[0], y0-box[1], x1-box[0], y1-box[1]],
        "sha256": atlas.sha(data),
    }


def build_queue(root, report, out_dir, skip_state_root=None, reuse_only=True):
    root = Path(root).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = atlas.load_cross(root / atlas.CROSS)
    plan = atlas.load_pinned_orientations(root, groups)
    by_id = {x["roi_id"]: x for rows in groups.values() for x in rows}
    holds, good = flatten_holds(report)
    ordered = [(by_id[rid],reason) for rid,reason in holds.items()
               if category(reason) == "AB_IMAGE_AND_CLEAN_REWORK" and rid in by_id]
    ordered.sort(key=lambda item: priority(*item))
    skip_ids=set()
    if skip_state_root:
        state_root=Path(skip_state_root)
        if state_root.is_dir():
            for path in state_root.glob("HDRW-*.json"):
                if not re.fullmatch(r"HDRW-[AB]-[0-9a-f]{20}\.json",path.name):
                    continue
                if path.stat().st_size>40000:
                    raise ValueError("OVERSIZE_REWORK_STATE")
                state=json.loads(path.read_text(encoding="utf-8"))
                if state.get("task_id")==path.stem and state.get("status") not in (None,""):
                    skip_ids.add(path.stem)
    selected = []
    eligible = Counter()
    selected_counts = Counter()
    blockers = Counter()
    for row, reason in ordered:
        role = row["roles"]
        eligible[role] += 1
        if reuse_only:
            # Existing imported A/B image pixels are the only authorized inputs.
            # Preserve HOLD accounting but never create new ImageGen tickets.
            continue
        if len(selected) >= MAX_ACTIVE or selected_counts[role] >= MAX_PER_ROLE:
            continue
        candidate = root / row["_candidate_rel"]
        if not candidate.is_file() or candidate.is_symlink():
            blockers["MISSING_PINNED_AB_CANDIDATE"] += 1
            continue
        current_sha = atlas.sha(candidate.read_bytes())
        digest = hashlib.sha256((
            POLICY+"|"+row["roi_id"]+"|"+row["source_dds_sha256"]+"|"+
            current_sha+"|"+reason
        ).encode()).hexdigest()[:20]
        task_id = ("HDRW-" + role + "-" + digest)
        if task_id in skip_ids:
            continue
        img_name = task_id + "_HD_SOURCE.png"
        img_path = out_dir / img_name
        try:
            proof = safe_hd_reference(root,row,plan,img_path)
        except (OSError, ValueError) as exc:
            blockers[str(exc)[:100]] += 1
            img_path.unlink(missing_ok=True)
            continue
        selected_counts[role] += 1
        selected.append({
            "task_id": task_id, "role": role, "roi_id": row["roi_id"],
            "english": row["english"], "korean": row["korean"],
            "reason": reason,
            "status": "READY_FOR_IMAGEGEN_ONLY_AFTER_DETERMINISTIC_SALVAGE_FAILED",
            "source_dds_path": row["source_dds_path"],
            "source_dds_sha256": row["source_dds_sha256"],
            "old_candidate_sha256": current_sha,
            "source_native_bbox_xyxy": row["_bbox"],
            "reference": {"name":img_name, **proof},
            "required": ["DETERMINISTIC_EXISTING_AB_SALVAGE_ALREADY_EXHAUSTED",
                         "KOREAN_LETTERING_RGBA_PNG",
                         "SOURCE_ENGLISH_ERASED_CLEAN_PLATE_FOR_NONTRANSPARENT_BG",
                         "EXACT_SOURCE_NATIVE_SIZE_CEILING",
                         "PRESERVE_ORIGINAL_LINE_COUNT",
                         "C1_INDEPENDENT_VISUAL_QA"],
            "qa_authority": "NOT_C1_APPROVED_NOT_GAME_APPROVED",
        })
    count = Counter(category(reason) for reason in holds.values())
    q = {
        "schema": "outrun-hd-qa-chat-workqueue-v1",
        "policy": POLICY,
        "source_asset_sha256": report.get("zip_sha256",""),
        "previously_claimed_ticket_count":len(skip_ids),
        "qa_report_schema": report["schema"],
        "release_approved": False,
        "runtime_validation": "UNTESTED",
        "source_roi_count": report["active_roi_total"],
        "old_painted_count_invalid_for_release": report["translated_roi_generated"],
        "hold_count": len(holds),
        "hold_categories": dict(sorted(count.items())),
        "ab_eligible_counts": dict(sorted(eligible.items())),
        "reference_blockers": dict(sorted(blockers.items())),
        "selection_policy": ("EXISTING_A_B_PNG_ONLY_NO_NEW_IMAGEGEN" if reuse_only
                             else "IMAGEGEN FALLBACK ONLY; 8 TOTAL MAX; 4 PER ROLE"),
        "new_imagegen_disabled": bool(reuse_only),
        "tasks": selected,
    }
    (out_dir/"queue.json").write_text(json.dumps(q,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return q


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--qa-report",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--skip-state-root",default=None)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--reuse-only", action="store_true", default=True,
                       help="Default: existing PNGs only; no ImageGen tasks")
    group.add_argument("--allow-imagegen-fallback", action="store_true",
                       help="Explicit staging of SHA-bound ImageGen tasks, not image generation")
    args=ap.parse_args()
    print(json.dumps({k:v for k,v in build_queue(
        args.repo_root,json.loads(Path(args.qa_report).read_text(encoding="utf-8")),
        args.out,args.skip_state_root,reuse_only=not args.allow_imagegen_fallback).items() if k in ("hold_count","hold_categories","ab_eligible_counts","reference_blockers")},
        ensure_ascii=False))
