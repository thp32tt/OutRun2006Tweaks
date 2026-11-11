#!/usr/bin/env python3
"""Extract source-owned English and protected atlas pixels for HD HOLD reviews.

This script writes source-SHA-pinned *evidence*, never DDS binaries or approval.
Only complete connected-component proofs may pass the strict native assembler.
Partial source ownership is diagnostic and always remains HOLD.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

from github_ab_imagegen_atlas_batch import (
    CROSS, ORIGINAL, conflicting_rois, dominant_container_holds,
    load_cross, load_pinned_orientations, native_image,
)
from hd_overlap_ownership import COSMETIC_FRINGE_ALPHA, prove_overlap_ownership
from hd_rework_queue import flatten_holds
from hd_strict_qa import source_ink_conflicts

SCHEMA = "outrun-hd-source-protected-component-evidence-v1"


def binary_core(alpha):
    """Native alpha>=16 is protected unless an exact connected owner proves it."""
    return alpha.point(lambda v: 255 if v > COSMETIC_FRINGE_ALPHA else 0)


def separate_masks(source, roi, partial_owned, ambiguous_native):
    """Separate proven English-component islands from protected/uncertain ink.

    The returned masks are at original HD pixel resolution. Alpha not owned
    by the selected ROI is always protected, regardless of its opacity/color.
    """
    x0, y0, x1, y1 = roi
    if not (0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height):
        raise ValueError("UNSAFE_NATIVE_BBOX")
    ink = binary_core(source.getchannel("A").crop(tuple(roi)))
    owned = partial_owned.crop(tuple(roi)) if partial_owned is not None else Image.new("L", ink.size, 0)
    ambiguous = ambiguous_native.crop(tuple(roi)) if ambiguous_native is not None else Image.new("L", ink.size, 0)
    if ImageChops.multiply(owned, ambiguous).getbbox():
        raise ValueError("OWNER_AND_AMBIGUOUS_PIXEL_INTERSECT")
    if ImageChops.subtract(owned, ink).getbbox():
        raise ValueError("OWNER_PIXEL_NOT_NATIVE_CORE")
    if ImageChops.subtract(ambiguous, ink).getbbox():
        raise ValueError("AMBIGUOUS_PIXEL_NOT_NATIVE_CORE")
    protected = ImageChops.subtract(ink, owned)
    if ImageChops.multiply(owned, protected).getbbox():
        raise ValueError("OWNED_PIXEL_WOULD_BE_PROTECTED")
    if ImageChops.difference(ImageChops.lighter(owned, protected), ink).getbbox():
        raise ValueError("MASKS_DO_NOT_COVER_NATIVE_SOURCE")
    return owned, protected, ambiguous


def count(mask):
    return mask.histogram()[255]


def evidence_overlay(source_crop, owned, protected, ambiguous):
    """Lossless RGB preview; mask PNGs remain authoritative pixel evidence."""
    view = source_crop.convert("RGBA")
    # Green=one-owner island; amber=ambiguous; red=other/protected ink.
    pixels = view.load()
    a, b, c = owned.load(), protected.load(), ambiguous.load()
    for y in range(view.height):
        for x in range(view.width):
            if a[x, y]:
                pixels[x, y] = (25, 220, 65, 255)
            elif c[x, y]:
                pixels[x, y] = (255, 170, 10, 255)
            elif b[x, y]:
                pixels[x, y] = (245, 45, 45, 255)
    return view


def source_clean_preview(source_crop, owned):
    """Remove ONLY pixel-proven owned English core; retain all protected art.

    This is a non-installable QA preview, not a completed English clean plate.
    Weak source fringe <=15 and every ambiguous original pixel remain intact.
    """
    if source_crop.size != owned.size or owned.mode != "L":
        raise ValueError("CLEAN_PREVIEW_MASK_DIMENSIONS_INVALID")
    clean = source_crop.copy()
    clean.paste((0, 0, 0, 0), (0, 0), owned)
    diff = ImageChops.difference(source_crop, clean)
    outside = ImageOps.invert(owned)
    if any(ImageChops.multiply(channel, outside).getbbox() for channel in diff.split()):
        raise ValueError("CLEAN_PREVIEW_MODIFIED_PROTECTED_PIXEL")
    if ImageChops.multiply(clean.getchannel("A"), owned).getbbox():
        raise ValueError("CLEAN_PREVIEW_OWNER_ALPHA_RESIDUE")
    return clean


def build(root, qa_report, out, max_previews=200):
    root = Path(root)
    out = Path(out)
    if max_previews < 0 or max_previews > 200:
        raise ValueError("INVALID_PREVIEW_BUDGET")
    report = json.loads(Path(qa_report).read_text(encoding="utf-8"))
    if (report.get("schema") != "outrun.ab-imagegen-hd-strict.v2"
            or report.get("release_approved") is not False
            or report.get("runtime_validation") != "UNTESTED"
            or report.get("source_dds_missing_rows") != 0
            or report.get("source_sha_conflict_rows") != 0):
        raise ValueError("SOURCE_BOUND_QA_REPORT_REQUIRED")
    held, painted = flatten_holds(report)
    groups = load_cross(root / CROSS)
    if (set(held) & painted or
            sum(map(len, groups.values())) != report.get("active_roi_total") or
            len(held) + len(painted) != report["active_roi_total"]):
        raise ValueError("QA_HOLD_COVERAGE_INVALID")
    orientations = load_pinned_orientations(root, groups)
    overlap_holds = {rid for rid, reason in held.items()
                     if reason == "ROI_OVERLAP_NEEDS_MANUAL_QA"}
    out.mkdir(parents=True, exist_ok=True)
    preview_dir = out / "native_masks"
    preview_dir.mkdir(exist_ok=True)
    evidence = []
    selected = 0
    atlases = 0
    counts = Counter()
    for target, rows in sorted(groups.items()):
        present = [row for row in rows if row["roi_id"] in overlap_holds]
        if not present:
            continue
        path = root / ORIGINAL / target
        if not path.is_file() or path.is_symlink():
            raise ValueError("SOURCE_DDS_NOT_AVAILABLE_FOR_MASKS")
        raw = path.read_bytes()
        source_sha = hashlib.sha256(raw).hexdigest()
        if len({r["source_dds_sha256"] for r in rows}) != 1 or source_sha != rows[0]["source_dds_sha256"]:
            raise ValueError("SOURCE_DDS_SHA_MISMATCH_FOR_MASKS")
        source = native_image(raw)
        if orientations[target] == "FLIPY":
            source = ImageOps.flip(source)
        coarse = dominant_container_holds(rows)
        noncoarse = [r for r in rows if r["roi_id"] not in coarse]
        conflicts = source_ink_conflicts(source, noncoarse, conflicting_rois)
        diagnostic = {}
        full, audit = prove_overlap_ownership(source, noncoarse, conflicts, diagnostics=diagnostic)
        partial = diagnostic.get("partial_owned_masks", {})
        ambiguous = diagnostic.get("ambiguous_native_mask")
        bc3_mips = raw[84:88] == b"DXT5" and struct.unpack_from("<I", raw, 80)[0] == 4
        atlases += 1
        for row in sorted(present, key=lambda r: r["roi_id"]):
            rid = row["roi_id"]
            owned, protected, unknown = separate_masks(
                source, row["_bbox"], partial.get(rid), ambiguous)
            core = count(owned) + count(protected)
            if not core:
                raise ValueError("EMPTY_OVERLAP_CORE")
            record = {
                "roi_id": rid,
                "source_dds_path": target,
                "source_dds_sha256": source_sha,
                "native_orientation": orientations[target],
                "bbox_xyxy": row["_bbox"],
                "english": row["english"],
                "korean": row["korean"],
                "native_alpha_core_pixels": core,
                "exclusive_anchored_component_pixels": count(owned),
                "protected_or_unclaimed_pixels": count(protected),
                "ambiguous_component_pixels": count(unknown),
                "full_component_owner_proven": rid in full,
                "native_bc3_four_mips_requires_separate_codec_gate": bc3_mips,
                "status": "MASK_DIAGNOSTIC_ONLY_NO_CLEAN_ERASURE_OR_GAME_QA",
                "mask_pngs": {},
            }
            # Save a bounded number of original-resolution masks, prioritizing
            # rows with actual isolated components to accelerate manual review.
            # Never invent an owner for fully ambiguous components.
            if selected < max_previews and count(owned):
                crop = source.crop(tuple(row["_bbox"]))
                for label, mask in (("owned", owned), ("protected", protected), ("ambiguous", unknown)):
                    name = rid + "_" + label + ".png"
                    mask.save(preview_dir / name, format="PNG")
                    record["mask_pngs"][label] = "native_masks/" + name
                name = rid + "_overlay.png"
                evidence_overlay(crop, owned, protected, unknown).save(
                    preview_dir / name, format="PNG")
                record["mask_pngs"]["overlay"] = "native_masks/" + name
                for suffix, preview in (
                    ("source", crop),
                    ("owner_only_clean_test", source_clean_preview(crop, owned)),
                ):
                    name = rid + "_" + suffix + ".png"
                    preview.save(preview_dir / name, format="PNG")
                    record["mask_pngs"][suffix] = "native_masks/" + name
                selected += 1
            evidence.append(record)
            counts["partial_owner_rows"] += bool(count(owned))
            counts["fully_proven_rows"] += rid in full
            counts["ambiguous_rows"] += bool(count(unknown))
    if {r["roi_id"] for r in evidence} != overlap_holds:
        raise ValueError("UNACCOUNTED_NATIVE_OVERLAP_HOLD")
    result = {
        "schema": SCHEMA,
        "release_approved": False,
        "runtime_validation": "UNTESTED",
        "source_report_zip_sha256": report.get("zip_sha256"),
        "source_total_roi": report["active_roi_total"],
        "source_holds": len(held),
        "overlap_hold_roi": len(overlap_holds),
        "source_atlases_inspected": atlases,
        "partial_owner_rows_diagnostic_only": counts["partial_owner_rows"],
        "full_owner_rows_diagnostic_only": counts["fully_proven_rows"],
        "ambiguous_component_rows": counts["ambiguous_rows"],
        "preview_count": selected,
        "owner_only_clean_preview_is_not_full_english_removal": True,
        "mask_meaning": {
            "owned": "GREEN native source components anchored uniquely to this ROI; not automatic English cleanup approval",
            "protected": "RED original source alpha that cannot be erased by this ROI",
            "ambiguous": "AMBER original connected source alpha with no unique owner",
        },
        "tickets": evidence,
    }
    (out / "source_protection_evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: result[k] for k in (
        "overlap_hold_roi", "source_atlases_inspected",
        "partial_owner_rows_diagnostic_only", "ambiguous_component_rows",
        "preview_count", "full_owner_rows_diagnostic_only")}, sort_keys=True))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--qa-report", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-previews", type=int, default=200)
    a = p.parse_args()
    build(a.repo_root, a.qa_report, a.out, a.max_previews)


if __name__ == "__main__":
    main()
