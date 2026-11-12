"""Synthetic source-owner image-edit tests; never imply C1/C3 approval."""
import unittest
from PIL import Image, ImageDraw
from hd_hold_auto_edit import (
    compose_owner_only, fit_existing_korean, validated_masks, source_lines_from_owned,
)


def scene():
    src = Image.new("RGBA", (150, 60), (0, 0, 0, 0))
    ImageDraw.Draw(src).rectangle((10, 18, 69, 38), fill=(255, 255, 255, 255))
    ImageDraw.Draw(src).rectangle((120, 18, 145, 38), fill=(20, 40, 60, 255))
    own = Image.new("L", src.size, 0)
    protect = Image.new("L", src.size, 0)
    ImageDraw.Draw(own).rectangle((10, 18, 69, 38), fill=255)
    ImageDraw.Draw(protect).rectangle((120, 18, 145, 38), fill=255)
    return src, own, protect


class AutoEditorTests(unittest.TestCase):
    def test_edits_actual_pixels_and_preserves_foreign_art(self):
        src, own, protect = scene()
        validated_masks(src, own, protect, Image.new("L", src.size, 0))
        source_lines = source_lines_from_owned(own)
        self.assertEqual(len(source_lines), 1)
        candidate = Image.new("RGBA", (90, 26), (0,0,0,0))
        ImageDraw.Draw(candidate).rectangle((3, 4, 85, 21), fill=(230, 220, 10, 255))
        from io import BytesIO
        out = BytesIO()
        candidate.save(out, format="PNG")
        fitted, receipt = fit_existing_korean(out.getvalue(), source_lines, src.size)
        self.assertEqual(fitted.size, src.size)
        self.assertEqual(receipt["translated_line_count"], 1)
        self.assertTrue(fitted.getchannel("A").getbbox())
        clean, edited = compose_owner_only(src, own, protect, fitted)
        self.assertEqual(clean.getpixel((20, 25))[3], 0)
        self.assertNotEqual(edited.getpixel((20, 25)), src.getpixel((20,25)))
        self.assertEqual(src.getpixel((125, 25)), edited.getpixel((125,25)))

    def test_reject_malformed_owner_mask_without_erasure(self):
        src, own, protect = scene()
        own.putpixel((80,25),255)
        with self.assertRaisesRegex(ValueError, "SOURCE_CORE_NOT_PARTITIONED"):
            validated_masks(src, own, protect, Image.new("L", src.size, 0))

    def test_reject_korean_covering_protected_pixels(self):
        src, own, protect = scene()
        translated = Image.new("RGBA", src.size, (0, 0, 0, 0))
        ImageDraw.Draw(translated).rectangle((119, 22, 125, 30), fill=(255, 255, 255, 255))
        with self.assertRaisesRegex(ValueError, "TOUCHES_PROTECTED_ART"):
            compose_owner_only(src, own, protect, translated)

    def test_ambiguous_pixels_are_only_protected(self):
        src, own, protect = scene()
        unknown = Image.new("L", src.size, 0)
        unknown.putpixel((130, 25), 255)
        validated_masks(src, own, protect, unknown)
        unknown.putpixel((80, 25), 255)
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_NOT_PROTECTED"):
            validated_masks(src, own, protect, unknown)

    def test_fit_never_expands_candidate_beyond_original_line(self):
        img = Image.new("RGBA", (200, 30), (0,0,0,0))
        ImageDraw.Draw(img).rectangle((2, 2, 197, 27), fill=(255,255,255,255))
        from io import BytesIO
        raw = BytesIO()
        img.save(raw, "PNG")
        fitted, record = fit_existing_korean(raw.getvalue(), [(5, 5, 55, 24)], (70, 40))
        x0,y0,x1,y1 = fitted.getchannel("A").getbbox()
        self.assertGreaterEqual(x0,5)
        self.assertGreaterEqual(y0,5)
        self.assertLessEqual(x1,55)
        self.assertLessEqual(y1,24)
        self.assertFalse(any("NEW_GLYPH" in action for action in record["actions"]))


if __name__ == "__main__":
    unittest.main()
