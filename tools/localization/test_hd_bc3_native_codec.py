"""Synthetic BC3/DXT5 native Korean atlas safety tests, no font fallback."""
import io
import struct
import unittest
from PIL import Image, ImageDraw
import hd_bc3_native_codec as bc


def fake_dxt5(width=32, height=32, boxes=((8, 8, 15, 15),)):
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for rectangle in boxes:
        draw.rectangle(rectangle, fill=(250, 250, 250, 255))
    head = bytearray(128)
    head[:4] = b'DDS '
    for at, n in ((4, 124), (12, height), (16, width),
                  (28, 1), (76, 32), (80, 4), (108, 0x1000)):
        struct.pack_into('<I', head, at, n)
    head[84:88] = b'DXT5'
    raw = bytearray(head)
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            raw.extend(bc.encode_bc3_block(
                [img.getpixel((x + i%4, y + i//4)) for i in range(16)]))
    source = Image.open(io.BytesIO(raw)).convert('RGBA')
    return bytes(raw), source


class DXT5OriginalProtection(unittest.TestCase):
    def test_full_text_blocks_patched_other_blocks_exact_source_bytes(self):
        raw, original = fake_dxt5()
        result = original.copy()
        ImageDraw.Draw(result).rectangle((8, 8, 15, 15), fill=(20, 210, 20, 255))
        patched, stats = bc.patch_bc3_native(raw, result, original, [(4, 4, 20, 20)])
        self.assertEqual(patched[:128], raw[:128])
        self.assertEqual(len(patched), len(raw))
        self.assertEqual(stats['bc3_blocks_patched'], 4)
        for by in range(8):
            for bx in range(8):
                offset = 128 + 16*(by*8 + bx)
                if 2 <= bx <= 3 and 2 <= by <= 3:
                    self.assertNotEqual(raw[offset:offset+16], patched[offset:offset+16])
                else:
                    self.assertEqual(raw[offset:offset+16], patched[offset:offset+16])
        self.assertGreater(Image.open(io.BytesIO(patched)).convert('RGBA').getpixel((10, 10))[1], 150)

    def test_protected_visible_pixels_on_same_block_fail_closed(self):
        raw, source = fake_dxt5(boxes=((4, 8, 7, 11),))
        result = source.copy()
        ImageDraw.Draw(result).rectangle((4, 8, 5, 11), fill=(0, 255, 0, 255))
        with self.assertRaisesRegex(bc.BC3Hold, 'PROTECTED_PIXEL_CHANGED'):
            bc.patch_bc3_native(raw, result, source, [(4, 8, 6, 12)])

    def test_unapproved_change_cannot_escape_bbox(self):
        raw, source = fake_dxt5()
        result = source.copy()
        ImageDraw.Draw(result).rectangle((8, 8, 15, 15), fill=(0, 255, 0, 255))
        with self.assertRaisesRegex(bc.BC3Hold, 'SOURCE_NOOP'):
            bc.patch_bc3_native(raw, result, source, [(0, 0, 4, 4)])

    def test_sub16_aa_fringe_may_quantize_but_glyph_core_survives(self):
        raw, source = fake_dxt5()
        result = source.copy()
        result.putpixel((4, 4), (20, 210, 20, 255))
        result.putpixel((5, 4), (20, 210, 20, 8))
        patched, receipt = bc.patch_bc3_native(
            raw, result, source, [(4, 4, 8, 8)])
        native = Image.open(io.BytesIO(patched)).convert('RGBA')
        self.assertGreater(native.getpixel((4, 4))[3], 200)
        self.assertLessEqual(abs(native.getpixel((5, 4))[3] - 8), 32)
        self.assertGreater(receipt['bc3_blocks_patched'], 0)
        self.assertEqual(patched[128:144], raw[128:144])

    def test_mip_chain_fails_closed_without_reencoding_all_levels(self):
        raw, _ = fake_dxt5()
        multi = bytearray(raw)
        struct.pack_into('<I', multi, 28, 2)
        multi.extend(bc.encode_bc3_block([(0, 0, 0, 0)]*16)*16)
        self.assertEqual(bc.bc3_header(multi), (32, 32, 2))
        source = Image.open(io.BytesIO(multi)).convert('RGBA')
        result = source.copy()
        ImageDraw.Draw(result).rectangle((8, 8, 15, 15), fill=(0, 255, 0, 255))
        with self.assertRaisesRegex(bc.BC3Hold, 'MIP_CHAIN_REQUIRES'):
            bc.patch_bc3_native(bytes(multi), result, source, [(4, 4, 20, 20)])

    def test_original_2d_dds_depth_one_is_not_a_volume_texture(self):
        raw, _ = fake_dxt5()
        source = bytearray(raw)
        struct.pack_into('<I', source, 24, 1)
        self.assertEqual(bc.bc3_header(source), (32, 32, 1))
        struct.pack_into('<I', source, 24, 2)
        with self.assertRaisesRegex(bc.BC3Hold, 'VOLUME_OR_CUBEMAP'):
            bc.bc3_header(source)

    def test_reject_corrupt_payload_and_cube_texture(self):
        raw, _ = fake_dxt5()
        with self.assertRaisesRegex(bc.BC3Hold, 'BAD_MIP_PAYLOAD'):
            bc.bc3_header(raw[:-1])
        cube = bytearray(raw)
        struct.pack_into('<I', cube, 112, 0x200)
        with self.assertRaisesRegex(bc.BC3Hold, 'CUBEMAP'):
            bc.bc3_header(bytes(cube))

    def test_second_protected_text_keeps_original_block_exactly(self):
        raw, source = fake_dxt5(boxes=((8, 8, 15, 15), (24, 24, 27, 27)))
        result = source.copy()
        ImageDraw.Draw(result).rectangle((8, 8, 15, 15), fill=(0, 200, 0, 255))
        patched, _ = bc.patch_bc3_native(raw, result, source, [(4, 4, 20, 20)])
        offset = 128 + 16*(6*8+6)
        self.assertEqual(raw[offset:offset+16], patched[offset:offset+16])

    def test_thin_antialiased_hangul_alpha_never_quantizes_to_zero(self):
        alphas = [0, 1, 3, 5, 12, 18, 25, 32,
                  40, 60, 100, 130, 170, 200, 240, 255]
        original = [(255, 250, 240, a) for a in alphas]
        encoded = bc.encode_bc3_block(original)
        decoded = bc.decode_bc3_block(encoded)
        for src, dst in zip(original, decoded):
            if src[3] > 0:
                self.assertGreater(dst[3], 0, "A tiny alpha edge may not disappear")
            self.assertLessEqual(abs(src[3] - dst[3]), 32)
        self.assertTrue(encoded[0] <= encoded[1],
                        "Low-alpha edge uses explicit 0/255 BC3 mode")

    def test_transparent_matte_outlier_does_not_recolor_readable_hangul(self):
        # Sub-16 alpha matte RGB must not force an endpoint which makes
        # the opaque native Korean glyph lose a color channel by >55.
        ink = ([(245, 20, 15, 255)] * 7
               + [(245, 120, 15, 255)] * 8)
        pixels = ink + [(0, 255, 255, 1)]
        encoded = bc.encode_bc3_block(pixels)
        decoded = bc.decode_bc3_block(encoded)
        for src, actual in zip(ink, decoded[:15]):
            self.assertLessEqual(
                max(abs(src[channel] - actual[channel]) for channel in range(3)),
                55,
                "Transparent matte pixels must not cause BC3 glyph core color loss")
            self.assertGreaterEqual(actual[3], 223)
        self.assertGreater(decoded[15][3], 0)

    def test_all_visible_ink_endpoint_fallback_recovers_interior_pair(self):
        # Real 4x4 BC3 has only two RGB565 endpoints. With >8 unique
        # colors a min/max-channel-only search fails this fixture (>55),
        # while a non-extreme visible pair fits all 16 pixels (<=55).
        # No new font, visual approval or relaxed color budget.
        rgb = [
            (108, 169, 123), (105, 186, 150), (138, 175, 156),
            (119, 164, 158), (121, 197, 137), (110, 174, 153),
            (121, 178, 139), (101, 169, 129), (170, 61, 44),
            (166, 75, 47), (171, 94, 68), (171, 75, 77),
            (132, 99, 64), (164, 62, 46), (198, 219, 251),
            (189, 210, 213),
        ]
        source = [color + (255,) for color in rgb]
        encoded = bc.encode_bc3_block(source)
        self.assertEqual(encoded, bc.encode_bc3_block(source))
        decoded = bc.decode_bc3_block(encoded)
        self.assertTrue(all(actual[3] == 255 for actual in decoded))
        self.assertLessEqual(max(
            abs(original[ch] - actual[ch])
            for original, actual in zip(source, decoded) for ch in range(3)
        ), 55)

    def test_pillow_and_manual_dxt5_decoding_agree(self):
        raw, source = fake_dxt5()
        block = raw[128:144]
        self.assertEqual(bc.decode_bc3_block(block)[:4], [source.getpixel((x, 0)) for x in range(4)])


if __name__ == '__main__':
    unittest.main()
