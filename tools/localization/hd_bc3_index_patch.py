"""Conservative DXT5/BC3 mip1 existing-palette pixel-index patcher.

Keep original RGB565 endpoints and EVERY unchanged decoded pixel bit-exact.
Only all-alpha-zero original blocks may receive alpha 255/0 endpoints, and
ONLY after verifying every untouched decoded pixel exactly equals its source.
No full block re-encode, inferred mips or generic-font redraw.
Changed pixels that cannot be represented closely by the source block palette
remain HOLD. Caller must separately verify CLEAN, layout, ROI and game visuals.
"""
from __future__ import annotations

import io
import struct
from PIL import Image

# User-authorized small BC3 quantization variance; protected native pixels
# remain exact and no DDS mip/header format change is permitted.
ALPHA_ERROR_LIMIT = 24
COLOR_ERROR_LIMIT = 30


class BC3Hold(ValueError):
    pass


def bc3_shape(data):
    if len(data) < 128 or data[:4] != b"DDS ":
        raise BC3Hold("QA_BC3_BAD_DDS_HEADER")
    width = struct.unpack_from("<I", data, 16)[0]
    height = struct.unpack_from("<I", data, 12)[0]
    mipmaps = struct.unpack_from("<I", data, 28)[0]
    pixel_flags = struct.unpack_from("<I", data, 80)[0]
    if data[84:88] != b"DXT5" or pixel_flags != 4:
        raise BC3Hold("QA_BC3_FOURCC_NOT_DXT5")
    if not (4 <= width <= 4096 and 4 <= height <= 4096 and
            width % 4 == 0 and height % 4 == 0):
        raise BC3Hold("QA_BC3_NON_BLOCK_ALIGNED")
    if mipmaps != 1:
        raise BC3Hold("QA_BC3_MIP_CHAIN_REQUIRES_ORIGINAL_FORMAT_REBUILD")
    expected = 128 + (width // 4) * (height // 4) * 16
    if len(data) != expected:
        raise BC3Hold("QA_BC3_PAYLOAD_LENGTH_MISMATCH")
    return width, height


def rgb565(value):
    red = (value >> 11) & 31
    green = (value >> 5) & 63
    blue = value & 31
    return ((red << 3) | (red >> 2),
            (green << 2) | (green >> 4),
            (blue << 3) | (blue >> 2))


def palettes(block):
    a0, a1 = block[0], block[1]
    if a0 > a1:
        alpha = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
    else:
        alpha = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
    c0, c1 = struct.unpack_from("<HH", block, 8)
    first, second = rgb565(c0), rgb565(c1)
    # BC3 always uses DXT1 four-color interpolation even when c0 <= c1.
    color = [first, second,
             tuple((2 * x + y) // 3 for x, y in zip(first, second)),
             tuple((x + 2 * y) // 3 for x, y in zip(first, second))]
    return alpha, color


def select_alpha(palette, want):
    i = min(range(8), key=lambda j: (abs(palette[j] - want), j))
    if abs(palette[i] - want) > ALPHA_ERROR_LIMIT:
        raise BC3Hold("QA_BC3_EXISTING_ALPHA_PALETTE_INSUFFICIENT")
    return i


def select_color(palette, want):
    i = min(range(4), key=lambda j: (
        sum((palette[j][k] - want[k]) ** 2 for k in range(3)), j))
    if any(abs(palette[i][k] - want[k]) > COLOR_ERROR_LIMIT for k in range(3)):
        raise BC3Hold("QA_BC3_EXISTING_RGB_PALETTE_INSUFFICIENT")
    return i


def _decode_bc3(data):
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.size != (struct.unpack_from("<I", data, 16)[0],
                               struct.unpack_from("<I", data, 12)[0]):
                raise BC3Hold("QA_BC3_DECODE_DIMENSION_MISMATCH")
            image.load()
            return image.convert("RGBA")
    except (OSError, SyntaxError) as exc:
        raise BC3Hold("QA_BC3_DECODE_FAILED") from exc


def patch_mip1(original, native_final, native_boxes, native_source=None):
    """Change only DXT5 block indices for pixels differing from source.

    native_boxes is a native-space pixel-rectangle ROI allow-list. No changes
    may occur outside them. A touching 4x4 block is not permission to rewrite
    its other (protected) pixels. All endpoints and header remain fixed.
    """
    width, height = bc3_shape(original)
    if native_final.mode != "RGBA" or native_final.size != (width, height):
        raise BC3Hold("QA_BC3_FINAL_DIMENSIONS")
    source = native_source if native_source is not None else _decode_bc3(original)
    if source.mode != "RGBA" or source.size != (width, height):
        raise BC3Hold("QA_BC3_SOURCE_DIMENSIONS")
    blocks_per_row = width // 4
    allow = Image.new("1", (width, height), 0)
    candidate_blocks = set()
    for box in native_boxes:
        if (len(box) != 4 or not 0 <= box[0] < box[2] <= width or
                not 0 <= box[1] < box[3] <= height):
            raise BC3Hold("QA_BC3_UNSAFE_NATIVE_ROI")
        allow.paste(1, tuple(box))
        for by in range(box[1] // 4, (box[3] - 1) // 4 + 1):
            for bx in range(box[0] // 4, (box[2] - 1) // 4 + 1):
                candidate_blocks.add((bx, by))
    source_px, desired_px, allowed_px = source.load(), native_final.load(), allow.load()
    output = bytearray(original)
    touched = []
    changed_total = 0
    transparent_rebased = 0
    for bx, by in sorted(candidate_blocks):
        offset = 128 + (by * blocks_per_row + bx) * 16
        old_block = bytes(output[offset:offset + 16])
        alpha_palette, color_palette = palettes(old_block)
        ai = int.from_bytes(old_block[2:8], "little")
        ci = int.from_bytes(old_block[12:16], "little")
        pixel_rows = []
        for index in range(16):
            x, y = bx * 4 + index % 4, by * 4 + index // 4
            src_rgba, new_rgba = source_px[x, y], desired_px[x, y]
            changed = src_rgba != new_rgba
            if changed and not allowed_px[x, y]:
                raise BC3Hold("QA_BC3_PROTECTED_PIXEL_CHANGED")
            pixel_rows.append((index, src_rgba, new_rgba, changed))
        changed_in_block = sum(int(r[3]) for r in pixel_rows)
        if not changed_in_block:
            continue
        need_rebase = any(
            row[3] and min(abs(v - row[2][3]) for v in alpha_palette) > ALPHA_ERROR_LIMIT
            for row in pixel_rows
        )
        if need_rebase:
            # For a block with alpha-zero at ALL original pixels, replacing
            # its ALPHA endpoints is safe only if the decoded saved bytes
            # prove every old pixel unchanged. RGB endpoints never move.
            if not all(row[1][3] == 0 for row in pixel_rows):
                raise BC3Hold("QA_BC3_EXISTING_ALPHA_PALETTE_INSUFFICIENT")
            rebased = bytes([255, 0]) + old_block[2:]
            alpha_palette, _ = palettes(rebased)
            ai = 0
            transparent_rebased += 1
        for index, src_rgba, new_rgba, changed in pixel_rows:
            if not changed and not need_rebase:
                continue
            want = new_rgba if changed else src_rgba
            a = select_alpha(alpha_palette, want[3])
            if changed and want[3] >= 16:
                c = select_color(color_palette, want)
                ci = (ci & ~(3 << (2 * index))) | (c << (2 * index))
            ai = (ai & ~(7 << (3 * index))) | (a << (3 * index))
        if need_rebase:
            output[offset:offset + 2] = bytes((255, 0))
        output[offset + 2:offset + 8] = ai.to_bytes(6, "little")
        output[offset + 12:offset + 16] = ci.to_bytes(4, "little")
        touched.append((bx, by, changed_in_block))
        changed_total += changed_in_block
    if not changed_total:
        raise BC3Hold("QA_BC3_NO_GLYPH_CHANGE")
    data = bytes(output)
    if data[:128] != original[:128] or len(data) != len(original):
        raise BC3Hold("QA_BC3_HEADER_OR_SIZE_CHANGED")
    actual = _decode_bc3(data).load()
    for bx, by, count in touched:
        for index in range(16):
            x, y = bx * 4 + index % 4, by * 4 + index // 4
            got, src, want = actual[x, y], source_px[x, y], desired_px[x, y]
            if src == want:
                if got != src:
                    raise BC3Hold("QA_BC3_UNCHANGED_PIXEL_NOT_EXACT")
            elif not allowed_px[x, y]:
                raise BC3Hold("QA_BC3_PIXEL_OUTSIDE_ALLOWLIST")
            elif (abs(got[3] - want[3]) > ALPHA_ERROR_LIMIT or
                  (want[3] >= 16 and
                   any(abs(got[k] - want[k]) > COLOR_ERROR_LIMIT for k in range(3)))):
                raise BC3Hold("QA_BC3_SAVED_PIXEL_ERROR_EXCEEDED")
    return data, {
        "bc3_blocks_modified": len(touched),
        "bc3_pixels_modified": changed_total,
        "bc3_method": "SOURCE_RGB_ENDPOINTS_FIXED_INDEX_ONLY_WITH_PROVEN_FULLY_TRANSPARENT_ALPHA_REBASE",
        "bc3_alpha_rebased_from_zero_blocks": transparent_rebased,
        "bc3_still_requires": "C1_C3_NATIVE_50PCT_MIP_AND_GAME_QA"
    }
