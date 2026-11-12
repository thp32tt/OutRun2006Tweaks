#!/usr/bin/env python3
"""Auto-edit existing A/B Korean PNGs against source-owned HD pixels.

Produces real pixel-edited transparent PNGs and owner-only-clean composite
PREVIEWS. A partial owner mask is NOT a complete English-removal proof. This
module never modifies source DDS, approved A/B input, or release state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps
from github_ab_imagegen_atlas_batch import (
    CROSS, ORIGINAL, load_cross, native_image,
)
from hd_existing_candidate_salvage import candidate_lines
from hd_rework_queue import flatten_holds
from hd_strict_qa import (
    QualityHold, alpha_lines, fit_line, source_effect_band_lines,
    strict_candidate,
)
from hd_source_protection_evidence import SCHEMA as MASK_SCHEMA, source_clean_preview
from hd_source_edge_rebind import SCHEMA as EDGE_SCHEMA

SCHEMA = "outrun-hd-existing-pixel-auto-editor-v1"
FRONTIER = 15
LIMIT = 200
ROI_ID = re.compile(r"Q\d{3}_[0-9a-f]{16}(?:_RB_B)?\Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_png(path: Path, mode="RGBA") -> Image.Image:
    if not path.is_file() or path.is_symlink():
        raise ValueError("AUTO_EDIT_MISSING_OR_SYMLINK_PNG")
    with Image.open(path) as im:
        if im.format != "PNG":
            raise ValueError("AUTO_EDIT_NON_PNG_SOURCE_EVIDENCE")
        im.load()
        return im.convert(mode)


def validated_mask_path(base: Path, rel: str, rid: str, suffix: str) -> Path:
    if rel != f"native_masks/{rid}_{suffix}.png" or not ROI_ID.fullmatch(rid):
        raise ValueError("AUTO_EDIT_UNTRUSTED_SOURCE_MASK_PATH")
    return base / rel


def validated_masks(source: Image.Image, owned: Image.Image,
                    protected: Image.Image, ambiguous: Image.Image) -> None:
    if any(x.mode != "L" or x.size != source.size for x in
           (owned, protected, ambiguous)):
        raise ValueError("AUTO_EDIT_MASK_DIMENSION_OR_MODE")
    for mask in (owned, protected, ambiguous):
        if mask.point(lambda x: 255 if x not in (0, 255) else 0).getbbox():
            raise ValueError("AUTO_EDIT_MASK_NON_BINARY")
    core = source.getchannel("A").point(lambda x: 255 if x > FRONTIER else 0)
    if ImageChops.multiply(owned, protected).getbbox():
        raise ValueError("AUTO_EDIT_OWNED_PROTECTED_INTERSECTION")
    if ImageChops.subtract(ambiguous, protected).getbbox():
        raise ValueError("AUTO_EDIT_AMBIGUOUS_NOT_PROTECTED")
    if ImageChops.difference(ImageChops.lighter(owned, protected), core).getbbox():
        raise ValueError("AUTO_EDIT_SOURCE_CORE_NOT_PARTITIONED")


def fit_existing_korean(candidate_bytes: bytes, source_lines: list, canvas_size):
    """Edit only the supplied artwork: alpha cleanup, reflow, shrink, center."""
    if not 1 <= len(source_lines) <= 3:
        raise QualityHold("AUTO_EDIT_SOURCE_LINES_UNVERIFIED")
    candidate, actions = strict_candidate(candidate_bytes)
    chunks, detected, reflow = candidate_lines(candidate, source_lines, alpha_lines)
    text_only = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    locations = []
    for bounds, image in zip(source_lines, chunks):
        fitted = fit_line(image, bounds)
        x = bounds[0] + (bounds[2] - bounds[0] - fitted.width) // 2
        y = bounds[1] + (bounds[3] - bounds[1] - fitted.height) // 2
        text_only.alpha_composite(fitted, (x, y))
        locations.append([x, y, x + fitted.width, y + fitted.height])
    if len(chunks) != len(source_lines) or not text_only.getchannel("A").getbbox():
        raise QualityHold("AUTO_EDIT_GLYPH_LINE_COVERAGE")
    return text_only, {
        "source_line_count": len(source_lines),
        "candidate_detected_line_count": detected,
        "translated_line_count": len(chunks),
        "source_native_line_boxes": [list(x) for x in source_lines],
        "translated_native_line_boxes": locations,
        "actions": actions + reflow + ["EXISTING_PIXELS_NATIVE_FIT_NO_FONT"],
    }


def compose_owner_only(source, owned, protected, korean):
    """Never overwrite a protected core or its one-pixel native halo."""
    validated_masks(source, owned, protected, Image.new("L", source.size, 0))
    active = korean.getchannel("A").point(lambda a: 255 if a > FRONTIER else 0)
    halo = ImageOps.expand(protected, 1, fill=0).filter(
        ImageFilter.MaxFilter(3)).crop((1, 1, source.width + 1, source.height + 1))
    if ImageChops.multiply(active, halo).getbbox():
        raise QualityHold("AUTO_EDIT_KOREAN_TOUCHES_PROTECTED_ART")
    clean = source_clean_preview(source, owned)
    result = Image.alpha_composite(clean, korean)
    delta = ImageChops.difference(source, result)
    if any(ImageChops.multiply(channel, protected).getbbox()
           for channel in delta.split()):
        raise QualityHold("AUTO_EDIT_PROTECTED_NATIVE_PIXEL_CHANGED")
    if ImageChops.multiply(clean.getchannel("A"), owned).getbbox():
        raise QualityHold("AUTO_EDIT_OWNER_ENGLISH_CORE_REMAINS")
    return clean, result


def save_png(image: Image.Image, path: Path) -> str:
    image.save(path, format="PNG", optimize=True)
    return sha(path.read_bytes())


def source_lines_from_owned(owned: Image.Image):
    lines, _ = source_effect_band_lines(owned)
    if len(lines) > 3 or not lines:
        raise QualityHold("AUTO_EDIT_SOURCE_OWNER_LINE_LAYOUT")
    return lines


def overlap_one(root, base, out, row, ticket):
    rid = row["roi_id"]
    paths = ticket["mask_pngs"]
    required = ("owned", "protected", "ambiguous", "source")
    if not all(k in paths for k in required):
        return {"roi_id": rid, "lane": "OVERLAP", "status": "NO_SOURCE_MASK_PREVIEW"}
    files = {k: validated_mask_path(base, paths[k], rid, k)
             for k in required}
    source = load_png(files["source"])
    owned, protected, ambiguous = (load_png(files[k], "L")
                                    for k in ("owned", "protected", "ambiguous"))
    validated_masks(source, owned, protected, ambiguous)
    if owned.getbbox() is None:
        return {"roi_id": rid, "lane": "OVERLAP", "status": "NO_EXCLUSIVE_NATIVE_OWNER"}
    if ticket["exclusive_anchored_component_pixels"] != owned.histogram()[255]:
        raise ValueError("AUTO_EDIT_OWNED_SOURCE_EVIDENCE_COUNT_MISMATCH")
    if ticket["ambiguous_component_pixels"] != ambiguous.histogram()[255]:
        raise ValueError("AUTO_EDIT_AMBIGUOUS_SOURCE_EVIDENCE_COUNT_MISMATCH")
    path = root / row["_candidate_rel"]
    if path.is_symlink() or not path.is_file():
        return {"roi_id": rid, "lane": "OVERLAP", "status": "AB_PNG_NOT_IMPORTED"}
    raw = path.read_bytes()
    receipt = {
        "roi_id": rid, "lane": "OVERLAP",
        "source_dds_sha256": row["source_dds_sha256"],
        "candidate_sha256": sha(raw), "source_native_bbox_xyxy": row["_bbox"],
        "owned_core_pixels": ticket["exclusive_anchored_component_pixels"],
        "ambiguous_core_pixels": ticket["ambiguous_component_pixels"],
        "partial_owner_not_complete_english_clean": True,
    }
    try:
        lines = source_lines_from_owned(owned)
        text, geometry = fit_existing_korean(raw, lines, source.size)
        receipt.update(geometry)
        fit_file = out / f"{rid}_korean_fit_RGBA.png"
        receipt["edited_transparent_png"] = fit_file.name
        receipt["edited_transparent_sha256"] = save_png(text, fit_file)
        try:
            clean, layered = compose_owner_only(source, owned, protected, text)
        except QualityHold as exc:
            receipt["status"] = "RGBA_EDITED_BUT_PROTECTED_COLLISION_HOLD"
            receipt["hold_reason"] = str(exc)
            return receipt
        clean_file = out / f"{rid}_owner_only_clean_TEST_ONLY.png"
        comp_file = out / f"{rid}_owner_clean_korean_TEST_ONLY.png"
        receipt["source_clean_preview"] = clean_file.name
        receipt["source_clean_preview_sha256"] = save_png(clean, clean_file)
        receipt["source_composite_preview"] = comp_file.name
        receipt["source_composite_preview_sha256"] = save_png(layered, comp_file)
        receipt["status"] = "EDITED_SOURCE_BOUND_PREVIEW_REVIEW_REQUIRED"
    except (QualityHold, ValueError, OSError) as exc:
        receipt["status"] = "EDIT_UNSAFE_HOLD"
        receipt["hold_reason"] = str(exc)
    return receipt


def edge_one(root, out, row, record, source):
    rid = row["roi_id"]
    box = record.get("proposed_bbox_xyxy")
    if record["status"] != "SOURCE_COMPONENT_COORDINATE_PROPOSAL_REVIEW_ONLY" or not box:
        return {"roi_id": rid, "lane": "EDGE", "status": "NO_SAFE_COORDINATE_PROPOSAL"}
    if not (0 <= box[0] < box[2] <= source.width and
            0 <= box[1] < box[3] <= source.height):
        raise ValueError("AUTO_EDIT_EDGE_BBOX_UNSAFE")
    path = root / row["_candidate_rel"]
    if path.is_symlink() or not path.is_file():
        return {"roi_id": rid, "lane": "EDGE", "status": "AB_PNG_NOT_IMPORTED"}
    raw = path.read_bytes()
    crop = source.crop(tuple(box))
    alpha = crop.getchannel("A").point(lambda x: x if x > FRONTIER else 0)
    lines, _ = source_effect_band_lines(alpha)
    receipt = {
        "roi_id": rid, "lane": "EDGE",
        "source_dds_sha256": row["source_dds_sha256"],
        "candidate_sha256": sha(raw),
        "original_bbox_xyxy": row["_bbox"],
        "proposed_bbox_xyxy": box,
    }
    try:
        if not 1 <= len(lines) <= 3:
            raise QualityHold("AUTO_EDIT_EDGE_SOURCE_LINES_UNVERIFIED")
        if alpha.histogram()[0] / (alpha.width * alpha.height) < 0.38:
            raise QualityHold("AUTO_EDIT_EDGE_SOURCE_TOO_OPAQUE")
        fitted, geometry = fit_existing_korean(raw, lines, crop.size)
        receipt.update(geometry)
        name = f"{rid}_edge_refit_RGBA.png"
        receipt["edited_transparent_png"] = name
        receipt["edited_transparent_sha256"] = save_png(fitted, out / name)
        receipt["status"] = "EDGE_KOREAN_RGBA_EDITED_SOURCE_CLEAN_NOT_PROVEN"
    except (QualityHold, ValueError, OSError) as exc:
        receipt["status"] = "EDIT_UNSAFE_HOLD"
        receipt["hold_reason"] = str(exc)
    return receipt


def run(root, qa_path, mask_path, edge_path, out, limit=LIMIT):
    if not 0 <= limit <= LIMIT:
        raise ValueError("AUTO_EDIT_LIMIT_OUT_OF_RANGE")
    root, out = Path(root), Path(out)
    qa = json.loads(Path(qa_path).read_text(encoding="utf-8"))
    evidence = json.loads(Path(mask_path).read_text(encoding="utf-8"))
    edges = json.loads(Path(edge_path).read_text(encoding="utf-8"))
    if (qa.get("schema") != "outrun.ab-imagegen-hd-strict.v2"
            or qa.get("release_approved") is not False
            or qa.get("runtime_validation") != "UNTESTED"
            or qa.get("source_dds_missing_rows") != 0
            or qa.get("source_sha_conflict_rows") != 0
            or evidence.get("schema") != MASK_SCHEMA
            or edges.get("schema") != EDGE_SCHEMA
            or evidence.get("source_report_zip_sha256") != qa.get("zip_sha256")
            or edges.get("source_report_zip_sha256") != qa.get("zip_sha256")
            or evidence.get("release_approved") is not False
            or edges.get("release_approved") is not False):
        raise ValueError("AUTO_EDIT_SOURCE_REPORT_PIN_OR_RELEASE_INVALID")
    groups = load_cross(root / CROSS)
    rows = {r["roi_id"]: r for group in groups.values() for r in group}
    held, painted = flatten_holds(qa)
    if len(rows) != 954 or len(held) + len(painted) != 954:
        raise ValueError("AUTO_EDIT_QA_CROSSWALK_COVERAGE")
    owned_tickets = evidence["tickets"]
    expected = {rid for rid, why in held.items() if why == "ROI_OVERLAP_NEEDS_MANUAL_QA"}
    if len(owned_tickets) != len(expected) or {t["roi_id"] for t in owned_tickets} != expected:
        raise ValueError("AUTO_EDIT_SOURCE_OWNER_TICKETS_INCOMPLETE")
    edge_records = edges["records"]
    edge_ids = {rid for rid, why in held.items() if why == "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE"}
    if len(edge_records) != len(edge_ids) or {r["roi_id"] for r in edge_records} != edge_ids:
        raise ValueError("AUTO_EDIT_EDGE_TICKETS_INCOMPLETE")
    out.mkdir(parents=True, exist_ok=True)
    base = Path(mask_path).parent
    records = []
    for ticket in sorted(owned_tickets, key=lambda t: t["roi_id"]):
        if len(records) >= limit:
            break
        rid = ticket["roi_id"]
        row = rows[rid]
        if ticket["source_dds_sha256"] != row["source_dds_sha256"] or ticket["bbox_xyxy"] != row["_bbox"]:
            raise ValueError("AUTO_EDIT_NATIVE_SOURCE_TICKET_CONFLICT")
        if not ticket["mask_pngs"].get("owned"):
            continue
        records.append(overlap_one(root, base, out, row, ticket))
    by_target = defaultdict(list)
    for rec in edge_records:
        if rec["status"] == "SOURCE_COMPONENT_COORDINATE_PROPOSAL_REVIEW_ONLY":
            by_target[rec["source_dds_path"]].append(rec)
    for target, items in sorted(by_target.items()):
        if len(records) >= limit:
            break
        path = root / ORIGINAL / target
        if path.is_symlink() or not path.is_file():
            raise ValueError("AUTO_EDIT_EDGE_ORIGINAL_DDS_MISSING")
        raw = path.read_bytes()
        digest = sha(raw)
        if any(r["source_dds_sha256"] != digest or
               rows[r["roi_id"]]["source_dds_sha256"] != digest for r in items):
            raise ValueError("AUTO_EDIT_EDGE_NATIVE_SHA_MISMATCH")
        source = native_image(raw)
        if items[0]["orientation"] == "FLIPY":
            source = ImageOps.flip(source)
        for rec in items:
            if len(records) >= limit:
                break
            row = rows[rec["roi_id"]]
            if rec["orientation"] != items[0]["orientation"]:
                raise ValueError("AUTO_EDIT_EDGE_ORIENTATION_CONFLICT")
            records.append(edge_one(root, out, row, rec, source))
    tally = dict(sorted(Counter(r["status"] for r in records).items()))
    proof = {
        "schema": SCHEMA,
        "source_report_zip_sha256": qa["zip_sha256"],
        "active_source_roi": 954,
        "original_hold_count_unchanged": len(held),
        "attempted_edits": len(records),
        "actual_transparent_png_edits": sum(bool(r.get("edited_transparent_png")) for r in records),
        "source_composite_preview_count": sum(bool(r.get("source_composite_preview")) for r in records),
        "results": tally,
        "release_approved": False,
        "runtime_validation": "UNTESTED",
        "visual_qa": "C1_C3_NOT_PERFORMED",
        "source_dds_modified": False,
        "input_ab_candidate_overwritten": False,
        "records": records,
    }
    (out / "auto_edit_report.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k: proof[k] for k in ("attempted_edits",
        "actual_transparent_png_edits", "source_composite_preview_count",
        "original_hold_count_unchanged", "results")}, ensure_ascii=False, sort_keys=True))
    return proof


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--qa-report", required=True)
    p.add_argument("--source-evidence", required=True)
    p.add_argument("--edge-proposals", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-edits", type=int, default=LIMIT)
    a = p.parse_args()
    run(a.repo_root, a.qa_report, a.source_evidence,
        a.edge_proposals, a.out, a.max_edits)


if __name__ == "__main__":
    main()
