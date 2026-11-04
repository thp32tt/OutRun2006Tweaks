"""Regression tests for user-rejected oversized Korean DDS samples."""
import importlib.util
import io
import struct
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageChops, ImageOps

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ab_native", root / "github_ab_imagegen_atlas_batch.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
spec2 = importlib.util.spec_from_file_location("strict", root / "hd_strict_qa.py")
strict = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(strict)


def source_dds(multiline=False, opaque=False):
    img = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((15, 18, 98, 37), fill=(255, 255, 255, 255))
    if multiline:
        draw.rectangle((15, 50, 98, 69), fill=(255, 255, 255, 255))
    if opaque:
        draw.rectangle((0, 0, 255, 127), fill=(40, 40, 40, 255))
    head = bytearray(128)
    head[0:4] = b"DDS "
    for off, val in ((4, 124), (12, 128), (16, 256), (28, 1), (76, 32), (80, 65), (88, 32)):
        struct.pack_into("<I", head, off, val)
    struct.pack_into("<IIII", head, 92, *native.MASKS)
    return bytes(head) + img.tobytes("raw", "BGRA")


def candidate_file(path, multiline=False, edge=False):
    img = Image.new("RGBA", (480, 200))
    draw = ImageDraw.Draw(img)
    draw.rectangle((25, 35, 420, 100), fill=(40, 80, 220, 255))
    if multiline:
        draw.rectangle((25, 140, 420, 165), fill=(40, 80, 220, 255))
    if edge:
        draw.rectangle((0, 0, 10, 10), fill=(40, 80, 220, 255))
    img.save(path)


def row(path="candidate.png"):
    return {"roi_id": "Q012_1234567890abcdef", "english": "Continue?",
            "korean": "계속?", "_bbox": [4, 6, 116, 100], "_candidate_rel": path}


class StrictHDQualityTests(unittest.TestCase):
    def run_case(self, src, multiline=False, candidate_edge=False):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate_file(repo/"candidate.png", multiline, candidate_edge)
            return strict.process_strict_atlas(
                src, [row()], repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)

    def test_clean_removes_source_english_alpha_and_preserves_protected(self):
        src = source_dds()
        data, final, clean, painted, holds = self.run_case(src)
        self.assertIsNotNone(data)
        self.assertEqual(len(painted), 1)
        self.assertFalse(holds)
        original = native.native_image(src)
        self.assertIsNone(clean.crop((4, 6, 116, 100)).getchannel("A").getbbox())
        self.assertIsNone(ImageChops.difference(original.crop((150, 0, 250, 127)),
                                                  final.crop((150, 0, 250, 127))).getbbox())
        self.assertEqual(data[:128], src[:128])
        self.assertEqual(len(data), len(src))
        self.assertEqual(painted[0]["original_line_count"], 1)
        self.assertEqual(painted[0]["translated_line_count"], 1)
        original_line = painted[0]["original_native_lines"][0]
        new_line = painted[0]["translated_native_lines"][0]
        self.assertLessEqual(new_line[2]-new_line[0], original_line[2]-original_line[0])
        self.assertLessEqual(new_line[3]-new_line[1], original_line[3]-original_line[1])
        self.assertEqual(painted[0]["clean_type"], "ISOLATED_SOURCE_ALPHA_TO_TRANSPARENT")

    def test_large_generated_text_is_shrunk_to_exact_source_height(self):
        data, _, _, painted, holds = self.run_case(source_dds())
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        source_box = painted[0]["original_native_lines"][0]
        out_box = painted[0]["translated_native_lines"][0]
        self.assertLessEqual(out_box[3]-out_box[1], source_box[3]-source_box[1])
        self.assertLessEqual(out_box[2]-out_box[0], source_box[2]-source_box[0])

    def test_background_is_not_deleted_as_text(self):
        data, _, _, painted, holds = self.run_case(source_dds(opaque=True))
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertIn("QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE", holds[0]["reason"])

    def test_source_two_lines_candidate_one_is_held(self):
        data, _, _, painted, holds = self.run_case(source_dds(multiline=True))
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(holds[0]["reason"], "QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED")

    def test_source_two_lines_candidate_two_is_separate_fit(self):
        data, _, _, painted, holds = self.run_case(source_dds(multiline=True), multiline=True)
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertEqual(len(painted[0]["original_native_lines"]), 2)
        for a, b in zip(painted[0]["original_native_lines"], painted[0]["translated_native_lines"]):
            self.assertLessEqual(b[2]-b[0], a[2]-a[0])
            self.assertLessEqual(b[3]-b[1], a[3]-a[1])

    def test_candidate_edge_clipping_is_rejected(self):
        data, _, _, painted, holds = self.run_case(source_dds(), candidate_edge=True)
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(holds[0]["reason"], "QA_CANDIDATE_EDGE_CLIP")

    def test_source_border_touch_is_rejected(self):
        src = source_dds()
        b = bytearray(src)
        im = native.native_image(src)
        ImageDraw.Draw(im).rectangle((4, 10, 12, 13), fill=(255, 255, 255, 255))
        b[128:] = im.tobytes("raw", "BGRA")
        data, _, _, painted, holds = self.run_case(bytes(b))
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(holds[0]["reason"], "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")

    def test_flip_y_native_roundtrip_preserves_orientation(self):
        src = source_dds()
        # Native upside-down input contains the original text near the bottom.
        im = native.native_image(src)
        raw = src[:128] + ImageOps.flip(im).tobytes("raw", "BGRA")
        data, final, clean, painted, holds = self.run_case_fliPY(raw)
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertTrue(ImageChops.difference(native.native_image(data),
                     ImageOps.flip(final)).getbbox() is None)

    def run_case_fliPY(self, raw):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d);candidate_file(repo/"candidate.png")
            return strict.process_strict_atlas(
                raw, [row()], repo, "FLIPY", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)


if __name__ == "__main__":
    unittest.main()
