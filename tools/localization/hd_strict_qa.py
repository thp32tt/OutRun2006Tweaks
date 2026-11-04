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

MAX_LINES = 3
MAX_SRC_ALPHA_OCCUPANCY = 0.62
MARGIN = 2


class QualityHold(ValueError):
    pass


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
    if min(b[0], b[1], img.width - b[2], img.height - b[3]) < MARGIN:
        raise QualityHold("QA_CANDIDATE_EDGE_CLIP")
    if a.getpixel((0, 0)) or a.getpixel((img.width - 1, img.height - 1)):
        raise QualityHold("QA_CANDIDATE_BACKGROUND_NOT_CLEAN")
    return img


def source_text_evidence(area: Image.Image):
    a = area.getchannel("A")
    extent = a.getbbox()
    if not extent:
        raise QualityHold("QA_NO_SOURCE_TEXT_ALPHA")
    if min(extent[0], extent[1], area.width - extent[2], area.height - extent[3]) < MARGIN:
        raise QualityHold("QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")
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
    return nonzero, lines, occupied


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
    if any(x0 < b[2] and b[0] < x1 and y0 < b[3] and b[1] < y1 for b in used):
        raise QualityHold("QA_OVERLAP_PROTECTED")
    if not import_check(repo, row):
        raise QualityHold("AB_PNG_NOT_YET_IMPORTED")
    src = source.crop(box)
    removal_mask, src_lines, occupancy = source_text_evidence(src)
    candidate_path = repo / row["_candidate_rel"]
    candidate_bytes = candidate_path.read_bytes()
    candidate = strict_candidate(candidate_bytes)
    cand_alpha = candidate.getchannel("A")
    translated_lines = alpha_lines(cand_alpha)
    if len(translated_lines) != len(src_lines):
        raise QualityHold("QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED")
    positions = []
    render = []
    for s, c in zip(src_lines, translated_lines):
        glyph = candidate.crop(c)
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
        "translated_line_count": len(translated_lines),
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
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
    conflicts = conflict_fn([r for r in rows if r["roi_id"] not in coarse])
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
    if ImageChops.difference(decode(data), native).getbbox():
        raise ValueError("QA_NATIVE_DDS_ROUNDTRIP_MISMATCH")
    return data, result, clean, painted, holds
