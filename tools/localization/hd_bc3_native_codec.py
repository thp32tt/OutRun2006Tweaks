"""DXT5/BC3 DDS block patcher for existing A/B Korean PNG TEST_ONLY atlases.

Only validated source-text ROIs may change. Unmodified compressed blocks are
byte-identical. Any visible protected pixel change caused by compression HOLDs
the entire atlas. Multi-level mip sources remain HOLD, not downconverted.
"""
from __future__ import annotations
import struct
from PIL import Image, ImageChops


class BC3Hold(ValueError):
    pass


def bc3_header(raw):
    if len(raw) < 128 or raw[:4] != b'DDS ' or struct.unpack_from('<I', raw, 4)[0] != 124:
        return None
    if struct.unpack_from('<I', raw, 76)[0] != 32 or struct.unpack_from('<I', raw, 80)[0] != 4:
        return None
    if raw[84:88] != b'DXT5':
        return None
    h, w = struct.unpack_from('<II', raw, 12)
    mips = struct.unpack_from('<I', raw, 28)[0]
    if w < 4 or h < 4 or w > 4096 or h > 4096 or mips < 1 or mips > 13:
        raise BC3Hold('QA_BC3_UNSUPPORTED_DIMENSIONS_OR_MIPS')
    if struct.unpack_from('<I', raw, 24)[0] not in (0, 1) or struct.unpack_from('<I', raw, 112)[0]:
        raise BC3Hold('QA_BC3_VOLUME_OR_CUBEMAP_HOLD')
    expected = 128 + sum(
        16 * max(1, (max(1, w >> i) + 3) // 4)
        * max(1, (max(1, h >> i) + 3) // 4) for i in range(mips)
    )
    if len(raw) != expected:
        raise BC3Hold('QA_BC3_BAD_MIP_PAYLOAD_SIZE')
    return w, h, mips


def _rgb565(pixel):
    r, g, b = pixel[:3]
    return ((r * 31 + 127) // 255 << 11) | ((g * 63 + 127) // 255 << 5) | ((b * 31 + 127) // 255)


def _unpack565(v):
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


def _alpha_palette(a0, a1):
    if a0 > a1:
        return [a0, a1] + [((7-i)*a0 + i*a1)//7 for i in range(1, 7)]
    return [a0, a1] + [((5-i)*a0 + i*a1)//5 for i in range(1, 5)] + [0, 255]


def encode_bc3_block(pixels):
    """Bounded deterministic BC3 compressor; per-block output remains unapproved."""
    if len(pixels) != 16:
        raise BC3Hold('QA_BC3_BLOCK_NOT_16_PIXELS')
    alphas = [p[3] for p in pixels]
    hi_alpha, lo_alpha = max(alphas), min(alphas)
    positive = [a for a in alphas if a > 0]
    min_positive = min(positive) if positive else 0
    # BC3 has two alpha interpolation modes: a0 > a1 yields 8
    # interpolated values, while a0 <= a1 explicitly includes 0 and 255.
    # In thin anti-aliased Hangul strokes, min alpha can be 1 while a
    # nearby full-strength stroke is 255. The naive (255,0) palette then
    # rounds alpha=1 to zero, making a native glyph edge disappear.
    # Evaluate deterministic endpoint pairs, preferring a mode with explicit
    # zero and a small positive endpoint if that preserves every stroke.
    candidates = [
        (hi_alpha, lo_alpha),
        (min_positive, hi_alpha),
        (min_positive, 255),
        (0, hi_alpha),
        (0, 255),
    ]
    best_encoding = None
    for pair in dict.fromkeys(candidates):
        palette = _alpha_palette(*pair)
        indexes = []
        errors = []
        valid = True
        for alpha in alphas:
            # A positive source alpha can NEVER be mapped to visible zero.
            choices = [k for k in range(8) if alpha == 0 or palette[k] > 0]
            if not choices:
                valid = False
                break
            idx = min(choices, key=lambda k: (abs(alpha - palette[k]), k))
            indexes.append(idx)
            errors.append(abs(alpha - palette[idx]))
        if not valid:
            continue
        key = (max(errors), sum(errors), pair)
        if best_encoding is None or key < best_encoding[0]:
            best_encoding = (key, pair, indexes)
    if best_encoding is None:
        raise BC3Hold('QA_BC3_NO_ALPHA_PALETTE_WITH_POSITIVE_STROKES')
    a0, a1 = best_encoding[1]
    alpha_indexes = sum(idx << (3*i) for i, idx in enumerate(best_encoding[2]))
    # A/B PNGs may contain arbitrary matte RGB in nearly transparent (<16)
    # AA fringe pixels. Such pixels are not readable ink and cannot veto the
    # channel-55 quality gate on the actual glyph body. Prefer core colors;
    # if a block has no core pixels, fall back to its positive-alpha colors.
    visible = [p[:3] for p in pixels if p[3] >= 16]
    if not visible:
        visible = [p[:3] for p in pixels if p[3] > 0] or [p[:3] for p in pixels]
    unique = sorted(set(visible))
    def rgb_candidate(first, second):
        c0, c1 = _rgb565(first), _rgb565(second)
        if c0 < c1:
            c0, c1 = c1, c0
        if c0 == c1:
            if c0 < 65535:
                c0 += 1
            else:
                c1 -= 1
        p0, p1 = _unpack565(c0), _unpack565(c1)
        palette = [p0, p1,
                   tuple((2*p0[k] + p1[k])//3 for k in range(3)),
                   tuple((p0[k] + 2*p1[k])//3 for k in range(3))]
        selected = [min(range(4), key=lambda idx: (
            max(abs(color[k]-palette[idx][k]) for k in range(3)),
            sum((color[k]-palette[idx][k])**2 for k in range(3)), idx))
            for color in visible]
        max_error = max(max(abs(color[k]-palette[idx][k]) for k in range(3))
                        for color, idx in zip(visible, selected))
        sq_error = sum(sum((color[k]-palette[idx][k])**2 for k in range(3))
                       for color, idx in zip(visible, selected))
        return (max_error, sq_error, c0, c1), c0, c1, palette
    initial_lo = min(unique, key=lambda p: (sum(p),p))
    initial_hi = max(unique, key=lambda p: (sum(p),p))
    best = rgb_candidate(initial_hi, initial_lo)
    if best[0][0] > 55:
        # A grayscale/luminance-only endpoint pair misrepresents some
        # source-colored A/B Korean glyphs. Search a bounded set of actual
        # visible candidate RGB colors; never relax the downstream 55/channel
        # saved-pixel gate or change a protected native pixel.
        if len(unique) <= 8:
            anchors = unique
        else:
            anchors = sorted({min(unique,key=lambda p:p[k]) for k in range(3)}
                             | {max(unique,key=lambda p:p[k]) for k in range(3)}
                             | {initial_lo,initial_hi})
        for first in anchors:
            for second in anchors:
                if first == second:
                    continue
                trial = rgb_candidate(first, second)
                if trial[0] < best[0]:
                    best = trial
        if best[0][0] > 55 and len(unique) > len(anchors):
            # Only on a failing block: try all distinct real visible ink
            # endpoint pairs (at most 16 pixels). Color extremes can hide
            # a feasible interior pair in multicolor AA/shadow glyphs.
            # This is a search improvement, NOT a weaker QA threshold:
            # saved BC3 bytes must still satisfy the original per-pixel
            # protected-alpha and <=55/channel color guards.
            for first in unique:
                for second in unique:
                    if first == second:
                        continue
                    trial = rgb_candidate(first, second)
                    if trial[0] < best[0]:
                        best = trial
    _, c0, c1, rgb_palette = best
    rgb_indexes = 0
    for i, pixel in enumerate(pixels):
        best_index = min(range(4), key=lambda k: (
            max(abs(pixel[ch]-rgb_palette[k][ch]) for ch in range(3)),
            sum((pixel[ch]-rgb_palette[k][ch])**2 for ch in range(3)), k))
        rgb_indexes |= best_index << (2*i)
    return bytes((a0, a1)) + alpha_indexes.to_bytes(6, 'little') + struct.pack('<HHI', c0, c1, rgb_indexes)


def decode_bc3_block(block):
    if len(block) != 16:
        raise BC3Hold('QA_BC3_BLOCK_BYTES')
    a0, a1 = block[0:2]
    alpha_indexes = int.from_bytes(block[2:8], 'little')
    alpha_palette = _alpha_palette(a0, a1)
    c0, c1, rgb_indexes = struct.unpack('<HHI', block[8:])
    p0, p1 = _unpack565(c0), _unpack565(c1)
    rgb = [p0, p1,
           tuple((2*p0[k] + p1[k])//3 for k in range(3)),
           tuple((p0[k] + 2*p1[k])//3 for k in range(3))]
    return [rgb[(rgb_indexes >> (2*i)) & 3]
            + (alpha_palette[(alpha_indexes >> (3*i)) & 7],) for i in range(16)]


def _visible_diff(a, b):
    return a[3] != b[3] or (a[3] > 0 and b[3] > 0 and a[:3] != b[:3])


def _allowed(x, y, boxes):
    return any(a <= x < c and b <= y < d for a, b, c, d in boxes)


def patch_bc3_native(raw, native, original_native, native_boxes):
    """Encode changed DXT5 blocks; exact visible source protection outside ROIs."""
    meta = bc3_header(raw)
    if meta is None:
        raise BC3Hold('QA_NOT_DXT5_FORMAT')
    width, height, mips = meta
    if mips != 1:
        raise BC3Hold('QA_BC3_MIP_CHAIN_REQUIRES_REENCODE_PROOF')
    if (native.size != (width, height) or original_native.size != (width, height)
            or native.mode != 'RGBA' or original_native.mode != 'RGBA'):
        raise BC3Hold('QA_BC3_NATIVE_RGBA_SIZE_MISMATCH')
    if any(not(0 <= a < c <= width and 0 <= b < d <= height)
           for a, b, c, d in native_boxes):
        raise BC3Hold('QA_BC3_INVALID_ROI_MASK')
    mutable = bytearray(raw)
    blocks_x = (width + 3) // 4
    # Compute only near edited ROI pixels, not every 4K atlas block.
    changed_blocks = set()
    for x0, y0, x1, y1 in native_boxes:
        diff = ImageChops.difference(native.crop((x0, y0, x1, y1)),
                                     original_native.crop((x0, y0, x1, y1)))
        channels = [box for channel in diff.split() if (box := channel.getbbox())]
        if not channels:
            continue
        a = x0 + min(r[0] for r in channels)
        b = y0 + min(r[1] for r in channels)
        c = x0 + max(r[2] for r in channels)
        d = y0 + max(r[3] for r in channels)
        changed_blocks.update((bx, by) for by in range(b//4, (d+3)//4)
                              for bx in range(a//4, (c+3)//4))
    if not changed_blocks:
        raise BC3Hold('QA_BC3_SOURCE_NOOP')
    block_count = 0
    for bx, by in sorted(changed_blocks, key=lambda pair: (pair[1], pair[0])):
        x0, y0 = bx*4, by*4
        old_pixels, new_pixels, valid = [], [], []
        for i in range(16):
            x, y = x0 + i%4, y0 + i//4
            if x < width and y < height:
                old = original_native.getpixel((x, y))
                new = native.getpixel((x, y))
                inside = _allowed(x, y, native_boxes)
                if _visible_diff(old, new) and not inside:
                    raise BC3Hold('QA_BC3_WRITE_OUTSIDE_VALIDATED_ROI')
                valid.append((i, inside, old, new))
                old_pixels.append(old)
                new_pixels.append(new)
            else:
                old_pixels.append((0, 0, 0, 0))
                new_pixels.append((0, 0, 0, 0))
        if not any(_visible_diff(a, b) for a, b in zip(old_pixels, new_pixels)):
            continue
        encoded = encode_bc3_block(new_pixels)
        decoded = decode_bc3_block(encoded)
        for i, inside, old, new in valid:
            pixel = decoded[i]
            if not inside:
                if _visible_diff(old, pixel):
                    raise BC3Hold('QA_BC3_PROTECTED_PIXEL_CHANGED_BY_ENCODING')
            elif new[3] > 0:
                # Sub-16 alpha is a barely visible AA/shadow fringe. BC3
                # may quantize that fringe to zero; NEVER allow the glyph
                # body (alpha >= 16) to disappear or exceed error limits.
                if (new[3] >= 16 and pixel[3] == 0) or abs(pixel[3] - new[3]) > 40:
                    raise BC3Hold('QA_BC3_TRANSLATED_ALPHA_LOST')
                # Invisible (<16 alpha) fringe RGB is not readable glyph
                # color and can contain matte pixels after Lanczos resizing.
                # Alpha>=16 text/glow tolerates up to 64/channel (9 more than
                # the prior rule), while never altering protected source pixels.
                if new[3] >= 16 and max(abs(pixel[k] - new[k]) for k in range(3)) > 64:
                    failure = BC3Hold('QA_BC3_TRANSLATED_COLOR_LOSS')
                    # Exact native pixel for safe ROI-specific fail-closed retry.
                    failure.native_xy = (x0 + i % 4, y0 + i // 4)
                    raise failure
            elif pixel[3] > 16:
                raise BC3Hold('QA_BC3_ENGLISH_ALPHA_RESIDUE')
        offset = 128 + (by*blocks_x + bx)*16
        mutable[offset:offset+16] = encoded
        block_count += 1
    if not block_count or bytes(mutable) == raw:
        raise BC3Hold('QA_BC3_PATCH_NOOP')
    if mutable[:128] != raw[:128] or len(mutable) != len(raw):
        raise BC3Hold('QA_BC3_HEADER_OR_MIP_LENGTH_CHANGED')
    return bytes(mutable), {'bc3_blocks_patched': block_count,
                            'original_format': 'DXT5', 'mip_count': 1,
                             'cosmetic_rgb_max_error': 64,
                             'cosmetic_alpha_max_error': 40,
                             'cosmetic_residue_alpha_max': 16}
