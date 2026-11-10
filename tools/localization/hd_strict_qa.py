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
from hd_bc3_index_patch import BC3Hold as PaletteHold, patch_mip1
from hd_bc3_native_codec import patch_bc3_native
from hd_overlap_ownership import prove_overlap_ownership
from hd_existing_candidate_salvage import (
    candidate_lines as salvage_candidate_lines,
    pad_candidate_edge,
    prove_source_edge_clear,
    translated_touches_external_native_ink,
    COSMETIC_FRINGE_ALPHA,
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


def shared_native_alpha(alpha, first_box, second_box):
    """Prove that two metadata ROIs share actual native source pixels.

    Bounding boxes of disconnected letters can overlap while the shared
    rectangle contains no source ink. Never infer that such bounds alone
    establish a real collision; never ignore even one alpha pixel in common.
    """
    if not intersects(first_box, second_box):
        return False
    x0 = max(first_box[0], second_box[0])
    y0 = max(first_box[1], second_box[1])
    x1 = min(first_box[2], second_box[2])
    y1 = min(first_box[3], second_box[3])
    return alpha.crop((x0, y0, x1, y1)).point(
        lambda n: n if n > COSMETIC_FRINGE_ALPHA else 0).getbbox() is not None


def source_ink_conflicts(source, rows, geometric_conflict_fn):
    """HOLD every source-pixel-shared overlap; allow empty shared padding.

    Translated candidate pixels must additionally remain outside every
    OTHER non-coarse ROI, even when source shared padding was empty.
    """
    geometric = geometric_conflict_fn(rows)
    alpha = source.getchannel("A")
    unsafe = set()
    for i, first in enumerate(rows):
        if first["roi_id"] not in geometric:
            continue
        for second in rows[i + 1:]:
            if second["roi_id"] not in geometric:
                continue
            if shared_native_alpha(alpha, first["_bbox"], second["_bbox"]):
                unsafe.update((first["roi_id"], second["roi_id"]))
    return unsafe


def translated_alpha_touches_box(image, left, top, other):
    """Check actual NEW pixels, not only the destination bounding rectangle."""
    dst = (left, top, left + image.width, top + image.height)
    if not intersects(dst, other):
        return False
    x0 = max(dst[0], other[0])
    y0 = max(dst[1], other[1])
    x1 = min(dst[2], other[2])
    y1 = min(dst[3], other[3])
    return image.getchannel("A").crop(
        (x0 - left, y0 - top, x1 - left, y1 - top)
    ).getbbox() is not None


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


def source_effect_band_lines(alpha: Image.Image):
    """Rejoin a single native text line split only by narrow AA/shadow bands.

    A separately stacked subtitle or label is never a shadow: at least one
    core band must be >=4x taller than *every* other band; all accessory
    bands must be short, vertically adjacent within 7 source pixels and
    horizontally contained in the core. This is evidence classification,
    not a new alpha mask or permission to erase other source text.
    """
    bands = alpha_lines(alpha)
    if len(bands) < 2 or len(bands) > 3:
        return bands, []
    heights = [b[3] - b[1] for b in bands]
    main_index = max(range(len(bands)), key=lambda i: heights[i])
    core = bands[main_index]
    ch = heights[main_index]
    if ch < 16 or any((i != main_index and 4 * h > ch)
                      for i, h in enumerate(heights)):
        return bands, []
    for i, b in enumerate(bands):
        if i == main_index:
            continue
        gap = core[1] - b[3] if b[3] <= core[1] else (
            b[1] - core[3] if b[1] >= core[3] else 0)
        if gap > 7 or b[0] < core[0] or b[2] > core[2]:
            return bands, []
    return [(min(b[0] for b in bands), min(b[1] for b in bands),
             max(b[2] for b in bands), max(b[3] for b in bands))], [
        "SOURCE_AA_SHADOW_BANDS_SINGLE_LOGICAL_LINE_TEST_ONLY"
    ]


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
    # User-approved sub-3.2% opacity flecks are cosmetic and not lettering.
    a = a.point(lambda n: 0 if n <= COSMETIC_FRINGE_ALPHA else n)
    img.putalpha(a)
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


def source_text_evidence(source: Image.Image, box, owner_mask=None):
    area = source.crop(box)
    a = area.getchannel("A")
    if owner_mask is not None:
        a = ImageChops.multiply(a, owner_mask.crop(box))
    # Ignore only visually negligible native alpha. Opaque panels remain HOLD.
    a = a.point(lambda n: 0 if n <= COSMETIC_FRINGE_ALPHA else n)
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
    lines, effect_salvage = source_effect_band_lines(a)
    salvage_actions += effect_salvage
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


def place_one_source_text(source, clean, result, row, repo, used, import_check,
                          other_boxes=(), owner_mask=None, protected_alpha=None,
                          placed_alpha=None):
    rid = row["roi_id"]
    x0, y0, x1, y1 = row["_bbox"]
    if x0 < 0 or y0 < 0 or x0 >= x1 or y0 >= y1 or x1 > source.width or y1 > source.height:
        raise QualityHold("QA_NATIVE_HD_ROI_BOUNDS_INVALID")
    box = (x0, y0, x1, y1)
    overlap_used = [b for b in used if intersects(box, b)]
    alpha = source.getchannel("A")
    if owner_mask is None and any(shared_native_alpha(alpha, box, b) for b in overlap_used):
        raise QualityHold("QA_OVERLAP_PROTECTED")
    if not import_check(repo, row):
        raise QualityHold("AB_PNG_NOT_YET_IMPORTED")
    removal_mask, src_lines, occupancy, source_salvage = source_text_evidence(source, box, owner_mask)
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
    # A true image boundary has no external atlas pixels to damage, but
    # newly translated text/effects MUST be fully inside that boundary.
    native_edges = [side for side in ("LEFT", "TOP", "RIGHT", "BOTTOM")
                    if "SOURCE_NATIVE_ATLAS_" + side + "_EDGE_INSET_REQUIRED" in source_salvage]
    if native_edges:
        for glyph, left, top in render:
            ink = glyph.getchannel("A").getbbox()
            if ink is None:
                raise QualityHold("QA_NATIVE_ATLAS_EDGE_TRANSLATED_GLYPH_INVISIBLE")
            l, t, r, b = left + ink[0], top + ink[1], left + ink[2], top + ink[3]
            if (("LEFT" in native_edges and l < MARGIN) or
                ("TOP" in native_edges and t < MARGIN) or
                ("RIGHT" in native_edges and r > source.width - MARGIN) or
                ("BOTTOM" in native_edges and b > source.height - MARGIN)):
                raise QualityHold("QA_NATIVE_ATLAS_EDGE_TRANSLATED_GLYPH_TOUCH")
    # A distinct, unrelated English glyph may be just outside a tight ROI.
    # Do not permit newly resized Hangul to touch that protected native ink.
    if "SOURCE_EDGE_DISJOINT_EXTERNAL_ALPHA_PROOF" in source_salvage and (
        translated_touches_external_native_ink(source, box, render)
    ):
        raise QualityHold("QA_TRANSLATED_TOUCHES_PROTECTED_EXTERNAL_SOURCE")
    # Even empty source padding belongs to another label's metadata ROI.
    # New translated ink must not enter it. Check every other ROI, including
    # candidates that will be held or have not been processed yet.
    if any(translated_alpha_touches_box(im, left, top, other)
           for im, left, top in render for other in other_boxes):
        raise QualityHold("QA_TRANSLATED_OVERLAPS_OTHER_ROI")
    # For exclusively anchored shared-ROI source components, reject new
    # glyph pixels touching original foreign art/text or earlier Korean ink.
    # This is independent of bbox ownership and never marks visual QA PASS.
    if owner_mask is not None:
        if protected_alpha is None or placed_alpha is None:
            raise QualityHold("QA_OVERLAP_MISSING_PROTECTION_EVIDENCE")
        for im, left, top in render:
            dst = (left, top, left + im.width, top + im.height)
            ink = im.getchannel("A")
            padded = protected_alpha.crop((left - 1, top - 1,
                                            left + im.width + 1, top + im.height + 1))
            from PIL import ImageFilter
            nearby = padded.filter(ImageFilter.MaxFilter(3)).crop((1, 1, im.width + 1, im.height + 1))
            if ImageChops.multiply(ink, nearby).getbbox():
                raise QualityHold("QA_OVERLAP_FOREIGN_SOURCE_INK_PROTECTED")
            if ImageChops.multiply(ink, placed_alpha.crop(dst)).getbbox():
                raise QualityHold("QA_OVERLAP_ALREADY_PLACED_KOREAN_INK")
    # No modifications are made until every line and mask has passed.
    clean.paste((0, 0, 0, 0), box, removal_mask)
    result.paste((0, 0, 0, 0), box, removal_mask)
    for im, left, top in render:
        result.alpha_composite(im, (left, top))
        if placed_alpha is not None:
            box_new = (left, top, left + im.width, top + im.height)
            previous = placed_alpha.crop(box_new)
            placed_alpha.paste(ImageChops.lighter(previous, im.getchannel("A")), (left, top))
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
        "candidate_source": row.get("_candidate_import_mode",
                                   "EXISTING_AB_PNG_DETERMINISTIC_SALVAGE_NO_NEW_GLYPHS"),
        "manual_original_bbox": row.get("_manual_source_bbox_original"),
        "manual_source_child_text": row.get("_manual_source_child_text"),
        "auto_salvage": source_salvage + candidate_salvage + line_salvage + (
            ["SOURCE_ALPHA_CONNECTED_COMPONENT_EXCLUSIVE_OWNER_TEST_ONLY"]
            if owner_mask is not None else []) + (
            ["OVERLAPPING_ROI_REUSED_ONLY_AFTER_DISJOINT_SOURCE_ALPHA_BBOX_PROOF"]
            if overlap_used else []),
        "clean_type": "ISOLATED_SOURCE_ALPHA_TO_TRANSPARENT",
        "qa_gate": "COSMETIC_ALPHA_LE_8_TOLERATED_C1_C3_GAME_UNTESTED",
    }


def process_strict_atlas(raw, rows, repo, orientation, decode, import_check,
                         conflict_fn, coarse_fn, excluded_bc3=frozenset()):
    source = decode(raw)
    if orientation == "FLIPY":
        source = ImageOps.flip(source)
    clean = source.copy()
    result = source.copy()
    painted, holds, used = [], [], []
    coarse = coarse_fn(rows)
    noncoarse = [r for r in rows if r["roi_id"] not in coarse]
    conflicts = source_ink_conflicts(source, noncoarse, conflict_fn)
    # Preserve the existing fail-closed BC3 codec path: shared-block ROI
    # ownership is not inferred from per-pixel uncompressed coordinates.
    ownership_masks = {}
    if conflicts and not (raw[84:88] == b"DXT5" and struct.unpack_from("<I", raw, 80)[0] == 4):
        ownership_masks, _ = prove_overlap_ownership(source, noncoarse, conflicts)
    conflicts = conflicts - set(ownership_masks)
    placed_alpha = Image.new("L", source.size, 0)
    for row in sorted(rows, key=lambda r: (r["_bbox"][1], r["_bbox"][0], r["roi_id"])):
        rid = row["roi_id"]
        if rid in coarse:
            holds.append({"roi_id": rid, "reason": "COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD"})
            continue
        if rid in conflicts:
            holds.append({"roi_id": rid, "reason": "ROI_OVERLAP_NEEDS_MANUAL_QA"})
            continue
        if rid in excluded_bc3:
            # Preserve the full original ROI rather than leaving fragments.
            holds.append({"roi_id": rid, "reason": "QA_BC3_TRANSLATED_COLOR_LOSS"})
            continue
        try:
            owner_mask = ownership_masks.get(rid)
            other_boxes = [r["_bbox"] for r in noncoarse
                           if r["roi_id"] != rid and
                           not (owner_mask is not None and
                                shared_native_alpha(source.getchannel("A"),
                                    row["_bbox"], r["_bbox"]))]
            foreign_alpha = (ImageChops.subtract(source.getchannel("A"), owner_mask).point(
                                 lambda n: n if n > COSMETIC_FRINGE_ALPHA else 0)
                             if owner_mask is not None else None)
            evidence = place_one_source_text(
                source, clean, result, row, repo, used, import_check, other_boxes,
                owner_mask=owner_mask, protected_alpha=foreign_alpha,
                placed_alpha=placed_alpha
            )
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
    if raw[84:88] == b"DXT5" and struct.unpack_from("<I", raw, 80)[0] == 4:
        # DXT5 is lossy; preserve the original RGB565 + alpha endpoints
        # bit-for-bit, touching only the indices of source-approved ROI pixels.
        # Unsupported 13-mip originals fail closed in the codec.
        native_boxes = [
            (x0, source.height - y1, x1, source.height - y0)
            if orientation == "FLIPY" else (x0, y0, x1, y1)
            for x0, y0, x1, y1 in used
        ]
        raw_source = ImageOps.flip(source) if orientation == "FLIPY" else source
        bc3_method = "DXT5_BC3_ORIGINAL_ENDPOINTS_INDEX_ONLY"
        try:
            # Prefer bit-exact original BC3 endpoints and all original color
            # palette values. This path cannot perturb untouched pixels.
            data, bc3_receipt = patch_mip1(raw, native, native_boxes, raw_source)
        except PaletteHold as exc:
            if str(exc) not in (
                "QA_BC3_EXISTING_RGB_PALETTE_INSUFFICIENT",
                "QA_BC3_EXISTING_ALPHA_PALETTE_INSUFFICIENT",
            ):
                raise
            # Fallback only when SOURCE block palettes cannot express the
            # existing high-quality A/B lettering. Recompress changed blocks
            # only, with individual source/pixel protection and error ceilings.
            # A failed proof stays HOLD; no unilateral visual approval.
            data, bc3_receipt = patch_bc3_native(raw, native, raw_source, native_boxes)
            bc3_method = "DXT5_BC3_CHANGED_BLOCKS_PROTECTED_REENCODE_TEST_ONLY"
        if data[:128] != raw[:128] or len(data) != len(raw) or data == raw:
            raise ValueError("QA_BC3_SOURCE_FORMAT_OR_NOOP")
        actual_native = decode(data)
        actual_readable = ImageOps.flip(actual_native) if orientation == "FLIPY" else actual_native
        # The preview must represent ACTUAL stored DXT5 bytes, not the
        # ideal uncompressed composite. All non-ROI pixels stay unchanged.
        difference = ImageChops.difference(source, actual_readable)
        if any(ImageChops.multiply(ch, outside).getbbox() for ch in difference.split()):
            raise ValueError("QA_BC3_SAVED_PROTECTED_ATLAS_PIXEL_CHANGED")
        for roi in painted:
            roi["dds_format"] = bc3_method
            roi["bc3_saved_format_receipt"] = bc3_receipt
            roi["auto_salvage"].append(
                "DXT5_INDEX_ONLY_VISUAL_QA_REQUIRED"
                if bc3_method == "DXT5_BC3_ORIGINAL_ENDPOINTS_INDEX_ONLY"
                else "DXT5_CHANGED_BLOCKS_REENCODE_VISUAL_QA_REQUIRED"
            )
        return data, actual_readable, clean, painted, holds
    masks = struct.unpack_from("<IIII", raw, 92)
    fmt = "BGRA" if masks == (0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000) else "RGBA"
    data = raw[:128] + native.tobytes("raw", fmt)
    if data[:128] != raw[:128] or len(data) != len(raw) or data == raw:
        raise ValueError("QA_NATIVE_DDS_SOURCE_HEADER_OR_NOOP")
    diff = ImageChops.difference(decode(data), native)
    if any(channel.getbbox() for channel in diff.split()):
        raise ValueError("QA_NATIVE_DDS_ROUNDTRIP_MISMATCH")
    return data, result, clean, painted, holds
