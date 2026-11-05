"""Fail-closed HD source-text replacement. A/B originals only, no font fallback.

This is an evidence-producing TEST_ONLY assembler, never a visual or game approval.
It accepts only isolated-alpha source lettering with measurable native line geometry.
Opaque backgrounds, mixed cells, ambiguous glyph masks and unreadable source layouts
require a separately reviewed CLEAN/PSD mask, not automatic rectangular erasure.
"""
from __future__ import annotations
import io
import json
import hashlib
import struct
from pathlib import Path

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError
from hd_existing_candidate_salvage import (
    candidate_lines as salvage_candidate_lines,
    pad_candidate_edge,
    prove_source_edge_clear,
)

MAX_LINES = 3
MAX_SRC_ALPHA_OCCUPANCY = 0.62
MARGIN = 2


class QualityHold(ValueError):
    pass


def intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def source_ink_bounds(source, box):
    """Conservative full-alpha bbox, not estimated text pixels.

    If source boundaries are invalid or empty, keep the whole ROI as unsafe.
    A safe overlap needs both full source-alpha bounding rectangles to be
    disjoint; unknown artwork/other labels must never be rewritten blindly.
    """
    x0, y0, x1, y1 = box
    if not 0 <= x0 < x1 <= source.width or not 0 <= y0 < y1 <= source.height:
        return tuple(box)
    ink = source.crop(box).getchannel("A").getbbox()
    if ink is None:
        return tuple(box)
    return x0 + ink[0], y0 + ink[1], x0 + ink[2], y0 + ink[3]


def source_ink_conflicts(source, rows, geometric_conflict_fn):
    """Allow intersecting ROI rectangles only with disjoint native ink bboxes.

    This never declares a pixel-shared overlap safe. Candidate transforms later
    fit strictly within these original source glyph/effect bounding rectangles.
    """
    geometric = geometric_conflict_fn(rows)
    ink = {r["roi_id"]: source_ink_bounds(source, r["_bbox"]) for r in rows}
    unsafe = set()
    for i, first in enumerate(rows):
        if first["roi_id"] not in geometric:
            continue
        for second in rows[i + 1:]:
            if second["roi_id"] not in geometric:
                continue
            if intersects(first["_bbox"], second["_bbox"]) and intersects(
                ink[first["roi_id"]], ink[second["roi_id"]]
            ):
                unsafe.update((first["roi_id"], second["roi_id"]))
    return unsafe


def alpha_lines(alpha: Image.Image):
    """Return line-local effect bounding boxes; merge tiny antialias gaps."""
    width, height = alpha.size
    # alpha.getbbox includes all visible fringe, including weak shadow AA.
    active = []
    for y in range(height):
        if alpha.crop((0, y, width, y + 1)).getbbox() is not None:
            active.append(y)
    if not active:
        return []
    ranges = []
    start = prev = active[0]
    for y in active[1:]:
        if y - prev > 4:
            ranges.append((start, prev + 1))
            start = y
        prev = y
    ranges.append((start, prev + 1))
    ans = []
    for y0, y1 in ranges:
        crop = alpha.crop((0, y0, width, y1))
        b = crop.getbbox()
        if b:
            ans.append((b[0], y0, b[2], y1))
    return ans


def strict_candidate(image_bytes):
    if len(image_bytes) > 4 * 1024 * 1024:
        raise QualityHold("QA_CANDIDATE_OVER_4MB")
    try:
        with Image.open(io.BytesIO(image_bytes)) as handle:
            if handle.format != "PNG" or not 24 <= handle.width <= 4096 or not 12 <= handle.height <= 4096:
                raise QualityHold("QA_CANDIDATE_PNG_GEOMETRY")
            handle.load()
            img = handle.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise QualityHold("QA_CANDIDATE_UNREADABLE") from exc
    a = img.getchannel("A")
    b = a.getbbox()
    if not b:
        raise QualityHold("QA_CANDIDATE_INVISIBLE")
    salvage_actions = []
    if min(b[0], b[1], img.width - b[2], img.height - b[3]) < MARGIN:
        img, salvage_actions = pad_candidate_edge(img, MARGIN)
        a = img.getchannel("A")
        b = a.getbbox()
    if a.getpixel((0, 0)) or a.getpixel((img.width - 1, img.height - 1)):
        raise QualityHold("QA_CANDIDATE_BACKGROUND_NOT_CLEAN")
    return img, salvage_actions


def source_text_evidence(source: Image.Image, box):
    area = source.crop(box)
    a = area.getchannel("A")
    extent = a.getbbox()
    if not extent:
        raise QualityHold("QA_NO_SOURCE_TEXT_ALPHA")
    try:
        salvage_actions = prove_source_edge_clear(source, box, extent, MARGIN)
    except ValueError as exc:
        raise QualityHold(str(exc)) from exc
    # Any completely opaque/painted panel is NOT an isolated glyph layer.
    nonzero = a.point(lambda n: 255 if n else 0)
    occupied = nonzero.histogram()[255] / (area.width * area.height)
    if occupied > MAX_SRC_ALPHA_OCCUPANCY:
        raise QualityHold("QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT")
    lines = alpha_lines(a)
    if not 1 <= len(lines) <= MAX_LINES:
        raise QualityHold("QA_SOURCE_LINE_LAYOUT_UNVERIFIED")
    if any((b[2] - b[0]) < 3 or (b[3] - b[1]) < 3 for b in lines):
        raise QualityHold("QA_SOURCE_GLYPH_TOO_SMALL")
    return nonzero, lines, occupied, salvage_actions


def fit_line(glyph: Image.Image, source_box):
    """Never expand beyond native source glyph/effect pixels; preserve aspect."""
    w = source_box[2] - source_box[0]
    h = source_box[3] - source_box[1]
    scale = min(1.0, w / glyph.width, h / glyph.height)
    out_w = max(1, int(glyph.width * scale))
    out_h = max(1, int(glyph.height * scale))
    if out_w > w or out_h > h:
        raise QualityHold("QA_GLYPH_SOURCE_BBOX_OVERFLOW")
    resized = glyph.resize((out_w, out_h), Image.Resampling.LANCZOS)
    a = resized.getchannel("A")
    if not a.getbbox():
        raise QualityHold("QA_DOWNSCALE_LOST_GLYPHS")
    # Reject an alpha stroke cut by resampling into a too-small line.
    if out_w < 3 or out_h < 3:
        raise QualityHold("QA_TRANSLATION_TOO_SMALL_TO_READ")
    return resized


def place_one_source_text(source, clean, result, row, repo, used, import_check):
    rid = row["roi_id"]
    x0, y0, x1, y1 = row["_bbox"]
    if x0 < 0 or y0 < 0 or x0 >= x1 or y0 >= y1 or x1 > source.width or y1 > source.height:
        raise QualityHold("QA_NATIVE_HD_ROI_BOUNDS_INVALID")
    box = (x0, y0, x1, y1)
    overlap_used = [b for b in used if intersects(box, b)]
    if any(intersects(source_ink_bounds(source, box), source_ink_bounds(source, b))
           for b in overlap_used):
        raise QualityHold("QA_OVERLAP_PROTECTED")
    if not import_check(repo, row):
        raise QualityHold("AB_PNG_NOT_YET_IMPORTED")
    removal_mask, src_lines, occupancy, source_salvage = source_text_evidence(source, box)
    candidate_path = repo / row["_candidate_rel"]
    candidate_bytes = candidate_path.read_bytes()
    candidate, candidate_salvage = strict_candidate(candidate_bytes)
    try:
        translated_images, detected_line_count, line_salvage = salvage_candidate_lines(
            candidate, src_lines, alpha_lines
        )
    except ValueError as exc:
        raise QualityHold(str(exc)) from exc
    positions = []
    render = []
    for s, glyph in zip(src_lines, translated_images):
        fitted = fit_line(glyph, s)
        left = x0 + s[0] + ((s[2] - s[0]) - fitted.width) // 2
        top = y0 + s[1] + ((s[3] - s[1]) - fitted.height) // 2
        dest = [left, top, left + fitted.width, top + fitted.height]
        assert dest[0] >= x0 + s[0] and dest[1] >= y0 + s[1]
        assert dest[2] <= x0 + s[2] and dest[3] <= y0 + s[3]
        positions.append(dest)
        render.append((fitted, left, top))
    # No modifications are made until every line and mask has passed.
    clean.paste((0, 0, 0, 0), box, removal_mask)
    result.paste((0, 0, 0, 0), box, removal_mask)
    for im, left, top in render:
        result.alpha_composite(im, (left, top))
    # Verify every pixel of the original text/effect has been removed from CLEAN,
    # including semitransparent shadow edges: zero alpha at every original alpha pixel.
    clean_roi = clean.crop(box)
    if ImageChops.multiply(clean_roi.getchannel("A"), removal_mask).getbbox():
        raise QualityHold("QA_ENGLISH_RESIDUE_IN_CLEAN_PLATE")
    used.append(box)
    return {
        "roi_id": rid, "english": row["english"], "korean": row["korean"],
        "roi": list(box),
        "original_native_lines": [[x0 + a, y0 + b, x0 + c, y0 + d] for a, b, c, d in src_lines],
        "translated_native_lines": positions,
        "source_alpha_occupancy": round(occupancy, 5),
        "original_line_count": len(src_lines),
        "translated_line_count": len(render),
        "candidate_detected_line_count": detected_line_count,
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "candidate_source": "EXISTING_AB_PNG_DETERMINISTIC_SALVAGE_NO_NEW_GLYPHS",
        "auto_salvage": source_salvage + candidate_salvage + line_salvage + (
            ["OVERLAPPING_ROI_REUSED_ONLY_AFTER_DISJOINT_SOURCE_ALPHA_BBOX_PROOF"]
            if overlap_used else []),
        "clean_type": "ISOLATED_SOURCE_ALPHA_TO_TRANSPARENT",
        "qa_gate": "MECHANICAL_HOLD_C1_C3_VISUAL_AND_GAME_NOT_APPROVED",
    }


def process_strict_atlas(raw, rows, repo, orientation, decode, import_check,
                         conflict_fn, coarse_fn):
    source = decode(raw)
    if orientation == "FLIPY":
        source = ImageOps.flip(source)
    clean = source.copy()
    result = source.copy()
    painted, holds, used = [], [], []
    coarse = coarse_fn(rows)
    conflicts = source_ink_conflicts(
        source, [r for r in rows if r["roi_id"] not in coarse], conflict_fn
    )
    for row in sorted(rows, key=lambda r: (r["_bbox"][1], r["_bbox"][0], r["roi_id"])):
        rid = row["roi_id"]
        if rid in coarse:
            holds.append({"roi_id": rid, "reason": "COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD"})
            continue
        if rid in conflicts:
            holds.append({"roi_id": rid, "reason": "ROI_OVERLAP_NEEDS_MANUAL_QA"})
            continue
        try:
            evidence = place_one_source_text(source, clean, result, row, repo, used, import_check)
            painted.append(evidence)
        except (OSError, ValueError, UnidentifiedImageError, OverflowError) as exc:
            holds.append({"roi_id": rid, "reason": str(exc)[:160]})
    if not painted:
        return None, None, None, painted, holds
    # Only declared, accepted source ROI rectangles can change. Other sprites stay bit-identical.
    roi_mask = Image.new("L", source.size, 0)
    for x0, y0, x1, y1 in used:
        roi_mask.paste(255, (x0, y0, x1, y1))
    outside = ImageOps.invert(roi_mask)
    for final in (result, clean):
        diff = ImageChops.difference(source, final)
        if any(ImageChops.multiply(ch, outside).getbbox() for ch in diff.split()):
            raise ValueError("QA_PROTECTED_ATLAS_PIXEL_CHANGED")
    native = ImageOps.flip(result) if orientation == "FLIPY" else result
    masks = struct.unpack_from("<IIII", raw, 92)
    fmt = "BGRA" if masks == (0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000) else "RGBA"
    data = raw[:128] + native.tobytes("raw", fmt)
    if data[:128] != raw[:128] or len(data) != len(raw) or data == raw:
        raise ValueError("QA_NATIVE_DDS_SOURCE_HEADER_OR_NOOP")
    diff = ImageChops.difference(decode(data), native)
    if any(channel.getbbox() for channel in diff.split()):
        raise ValueError("QA_NATIVE_DDS_ROUNDTRIP_MISMATCH")
    return data, result, clean, painted, holds
