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
    draw.rectangle((0 if edge else 25, 35, 420, 100), fill=(40, 80, 220, 255))
    if multiline:
        draw.rectangle((25, 140, 420, 165), fill=(40, 80, 220, 255))
    img.save(path)


def candidate_components_file(path):
    """One visual line with separable existing glyph groups; no font generation."""
    img = Image.new("RGBA", (480, 200))
    draw = ImageDraw.Draw(img)
    draw.rectangle((25, 35, 155, 100), fill=(40, 80, 220, 255))
    draw.rectangle((220, 35, 420, 100), fill=(40, 80, 220, 255))
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

    def test_native_steering_shadow_bands_are_one_logical_source_line(self):
        # Native source has top 10px AA band, main 60px letter band and
        # bottom 3px AA band, all horizontally nested in the same label.
        im = Image.new("RGBA", (490, 145), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((103, 27, 444, 36), fill=(255, 255, 255, 65))
        d.rectangle((71, 44, 444, 103), fill=(255, 255, 255, 255))
        d.rectangle((191, 109, 304, 111), fill=(255, 255, 255, 20))
        raw_bands = strict.alpha_lines(im.getchannel("A"))
        self.assertEqual(len(raw_bands), 3)
        grouped, receipt = strict.source_effect_band_lines(im.getchannel("A"))
        self.assertEqual(grouped, [(71, 27, 445, 112)])
        self.assertIn("SOURCE_AA_SHADOW_BANDS_SINGLE_LOGICAL_LINE_TEST_ONLY", receipt)

    def test_native_two_full_sized_lines_cannot_be_merged_as_shadow(self):
        im = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((24, 22, 260, 66), fill="white")
        d.rectangle((25, 84, 254, 123), fill="white")
        grouped, receipt = strict.source_effect_band_lines(im.getchannel("A"))
        self.assertEqual(len(grouped), 2)
        self.assertFalse(receipt)

    def test_small_unrelated_external_band_is_never_assigned_to_text(self):
        im = Image.new("RGBA", (300, 145), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((60, 40, 250, 100), fill="white")
        d.rectangle((7, 28, 18, 34), fill="white")
        grouped, receipt = strict.source_effect_band_lines(im.getchannel("A"))
        self.assertEqual(len(grouped), 2)
        self.assertFalse(receipt)

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

    def test_source_two_lines_candidate_one_reflows_existing_pixels_when_separable(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate_components_file(repo/"candidate.png")
            data, _, _, painted, holds = strict.process_strict_atlas(
                source_dds(multiline=True), [row()], repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertEqual(painted[0]["candidate_detected_line_count"], 1)
        self.assertEqual(painted[0]["translated_line_count"], 2)
        self.assertTrue(any("REFLOW_EXISTING_CANDIDATE_1_TO_2_LINES" in x
                            for x in painted[0]["auto_salvage"]))

    def test_partial_roi_overlap_reuses_existing_pixels_only_when_native_ink_disjoint(self):
        # Two overlapping metadata rectangles; actual native source glyph
        # bounding boxes are separate. No newly generated lettering is needed.
        src = source_dds()
        image = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
        drawer = ImageDraw.Draw(image)
        drawer.rectangle((10, 15, 39, 30), fill=(255, 255, 255, 255))
        drawer.rectangle((70, 60, 99, 75), fill=(255, 255, 255, 255))
        raw = src[:128] + image.tobytes("raw", "BGRA")
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate_file(repo / "first.png")
            candidate_file(repo / "second.png")
            rows = [
                {"roi_id": "Q012_1234567890abcdef", "english": "ONE",
                 "korean": "하나", "_bbox": [4, 6, 70, 48],
                 "_candidate_rel": "first.png"},
                {"roi_id": "Q012_fedcba0987654321", "english": "TWO",
                 "korean": "둘", "_bbox": [45, 36, 117, 99],
                 "_candidate_rel": "second.png"},
            ]
            data, final, clean, painted, holds = strict.process_strict_atlas(
                raw, rows, repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertEqual(len(painted), 2)
        self.assertEqual(final.getpixel((55, 40)), (0, 0, 0, 0))
        self.assertTrue(any("OVERLAPPING_ROI_REUSED_ONLY" in x
                            for x in painted[1]["auto_salvage"]))
        for placed in painted:
            original = placed["original_native_lines"][0]
            translated = placed["translated_native_lines"][0]
            self.assertGreaterEqual(translated[0], original[0])
            self.assertGreaterEqual(translated[1], original[1])
            self.assertLessEqual(translated[2], original[2])
            self.assertLessEqual(translated[3], original[3])

    def test_intersecting_ink_bounding_boxes_with_empty_shared_pixels_are_safe(self):
        # The bounding rectangles intersect, but not a single original
        # alpha pixel is inside the two ROIs' shared padding rectangle.
        img = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle((10, 10, 135, 19), fill=(255, 255, 255, 255))
        draw.rectangle((10, 55, 75, 62), fill=(255, 255, 255, 255))
        draw.rectangle((180, 48, 215, 53), fill=(255, 255, 255, 255))
        draw.rectangle((95, 90, 210, 95), fill=(255, 255, 255, 255))
        a, b = (4, 4, 140, 64), (80, 40, 220, 116)
        self.assertTrue(strict.intersects(strict.source_ink_bounds(img, a),
                                          strict.source_ink_bounds(img, b)))
        self.assertIsNone(img.crop((80, 40, 140, 64)).getchannel("A").getbbox())
        raw = source_dds()[:128] + img.tobytes("raw", "BGRA")
        rows = [
            {"roi_id": "Q012_1234567890abcdef", "english": "FIRST",
             "korean": "첫째", "_bbox": list(a), "_candidate_rel": "a.png"},
            {"roi_id": "Q012_fedcba0987654321", "english": "SECOND",
             "korean": "둘째", "_bbox": list(b), "_candidate_rel": "b.png"},
        ]
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate_file(repo / "a.png", multiline=True)
            candidate_file(repo / "b.png", multiline=True)
            data, final, clean, painted, holds = strict.process_strict_atlas(
                raw, rows, repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)
        self.assertIsNotNone(data)
        self.assertEqual(len(painted), 2)
        self.assertEqual(holds, [])
        self.assertIsNone(final.crop((80, 40, 140, 64)).getchannel("A").getbbox())
        self.assertEqual(data[:128], raw[:128])
        self.assertEqual(len(data), len(raw))

    def test_empty_source_overlap_but_translated_pixel_intrusion_stays_held(self):
        # Source strokes do not enter the overlapping ROI padding, but a
        # resized candidate would. No protected ROI may receive its pixels.
        img = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.line((130, 10, 10, 60), fill=(255, 255, 255, 255), width=1)
        draw.rectangle((180, 80, 210, 95), fill=(255, 255, 255, 255))
        a, b = (4, 4, 140, 64), (80, 40, 220, 116)
        self.assertIsNone(img.crop((80, 40, 140, 64)).getchannel("A").getbbox())
        raw = source_dds()[:128] + img.tobytes("raw", "BGRA")
        rows = [
            {"roi_id": "Q012_1234567890abcdef", "english": "FIRST",
             "korean": "첫째", "_bbox": list(a), "_candidate_rel": "a.png"},
            {"roi_id": "Q012_fedcba0987654321", "english": "SECOND",
             "korean": "둘째", "_bbox": list(b), "_candidate_rel": "b.png"},
        ]
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate_file(repo / "a.png")
            candidate_file(repo / "b.png")
            data, final, clean, painted, holds = strict.process_strict_atlas(
                raw, rows, repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)
        self.assertIsNotNone(data)
        self.assertEqual(len(painted), 1)
        self.assertEqual(painted[0]["roi_id"], rows[1]["roi_id"])
        self.assertEqual(holds, [{"roi_id": rows[0]["roi_id"],
                                  "reason": "QA_TRANSLATED_OVERLAPS_OTHER_ROI"}])
        self.assertEqual(final.getpixel((130, 10)), img.getpixel((130, 10)))

    def test_partial_roi_overlap_with_shared_native_ink_stays_held(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate_file(repo / "candidate.png")
            rows = [row(), dict(row(), roi_id="Q012_fedcba0987654321")]
            data, _, _, painted, holds = strict.process_strict_atlas(
                source_dds(), rows, repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(len(holds), 2)
        self.assertTrue(all(h["reason"] == "ROI_OVERLAP_NEEDS_MANUAL_QA"
                            for h in holds))

    def test_source_two_lines_candidate_two_is_separate_fit(self):
        data, _, _, painted, holds = self.run_case(source_dds(multiline=True), multiline=True)
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertEqual(len(painted[0]["original_native_lines"]), 2)
        for a, b in zip(painted[0]["original_native_lines"], painted[0]["translated_native_lines"]):
            self.assertLessEqual(b[2]-b[0], a[2]-a[0])
            self.assertLessEqual(b[3]-b[1], a[3]-a[1])

    def test_candidate_edge_is_padded_and_shrunk_before_imagegen_fallback(self):
        data, _, _, painted, holds = self.run_case(source_dds(), candidate_edge=True)
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertTrue(any("PAD_EXISTING_CANDIDATE_EDGE" in x
                            for x in painted[0]["auto_salvage"]))

    def test_physical_atlas_edge_requires_inset_but_allows_safe_narrow_hangul(self):
        # At x=0 no outside pixel exists. A narrow replacement must be
        # strictly inset; original edge alpha is removed from CLEAN.
        image = native.native_image(source_dds())
        image.paste((0, 0, 0, 0), (0, 0, image.width, image.height))
        ImageDraw.Draw(image).rectangle((0, 18, 22, 37),
                                        fill=(255, 255, 255, 255))
        src = source_dds()[:128] + image.tobytes("raw", "BGRA")
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(candidate).rectangle((20, 20, 60, 125),
                                                fill=(40, 80, 220, 255))
            candidate.save(repo / "narrow.png")
            entry = dict(row("narrow.png"), _bbox=[0, 6, 116, 100])
            data, final, clean, painted, holds = strict.process_strict_atlas(
                src, [entry], repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)
        self.assertIsNotNone(data)
        self.assertEqual(len(painted), 1)
        self.assertFalse(holds)
        self.assertIn("SOURCE_NATIVE_ATLAS_LEFT_EDGE_INSET_REQUIRED",
                      painted[0]["auto_salvage"])
        self.assertIsNone(clean.crop((0, 18, 23, 38)).getchannel("A").getbbox())
        self.assertGreaterEqual(final.getchannel("A").getbbox()[0], strict.MARGIN)

    def test_physical_atlas_edge_wide_hangul_still_held_when_it_touches(self):
        image = native.native_image(source_dds())
        image.paste((0, 0, 0, 0), (0, 0, image.width, image.height))
        ImageDraw.Draw(image).rectangle((0, 18, 22, 37),
                                        fill=(255, 255, 255, 255))
        src = source_dds()[:128] + image.tobytes("raw", "BGRA")
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            candidate_file(repo / "wide.png")
            entry = dict(row("wide.png"), _bbox=[0, 6, 116, 100])
            data, final, clean, painted, holds = strict.process_strict_atlas(
                src, [entry], repo, "NORMAL", native.native_image,
                native.imported_candidate, native.conflicting_rois,
                native.dominant_container_holds)
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(holds[0]["reason"],
                         "QA_NATIVE_ATLAS_EDGE_TRANSLATED_GLYPH_TOUCH")

    def test_source_border_touch_is_accepted_only_when_neighbor_pixels_are_clear(self):
        src = source_dds()
        b = bytearray(src)
        im = native.native_image(src)
        ImageDraw.Draw(im).rectangle((4, 18, 14, 37), fill=(255, 255, 255, 255))
        b[128:] = im.tobytes("raw", "BGRA")
        data, _, _, painted, holds = self.run_case(bytes(b))
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertIn("SOURCE_EDGE_CLEAR_NEIGHBOR_PROOF", painted[0]["auto_salvage"])

    def test_source_border_touch_with_alpha_outside_roi_remains_hold(self):
        src = source_dds()
        b = bytearray(src)
        im = native.native_image(src)
        ImageDraw.Draw(im).rectangle((3, 18, 14, 37), fill=(255, 255, 255, 255))
        b[128:] = im.tobytes("raw", "BGRA")
        data, _, _, painted, holds = self.run_case(bytes(b))
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(holds[0]["reason"], "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")

    def test_source_edge_unrelated_neighbor_is_not_false_hold(self):
        # The source text ends at x=4. Another word's native alpha lies
        # just outside the same bounding ROI but far away on the y axis.
        # The original neighbor stays bit-identical after resizing and CLEAN.
        im = native.native_image(source_dds())
        draw = ImageDraw.Draw(im)
        draw.rectangle((4, 18, 14, 37), fill=(255, 255, 255, 255))
        draw.rectangle((3, 76, 3, 81), fill=(127, 100, 255, 80))
        src = source_dds()[:128] + im.tobytes("raw", "BGRA")
        data, final, clean, painted, holds = self.run_case(src)
        self.assertIsNotNone(data)
        self.assertFalse(holds)
        self.assertEqual(len(painted), 1)
        self.assertIn("SOURCE_EDGE_DISJOINT_EXTERNAL_ALPHA_PROOF",
                      painted[0]["auto_salvage"])
        self.assertEqual(final.getpixel((3, 78)), im.getpixel((3, 78)))
        self.assertEqual(clean.getpixel((3, 78)), im.getpixel((3, 78)))
        self.assertIsNone(clean.crop((4, 18, 99, 38)).getchannel("A").getbbox())
        self.assertEqual(data[:128], src[:128])
        self.assertEqual(len(data), len(src))

    def test_source_edge_diagonal_native_continuation_is_still_hold(self):
        # Native AA can cross diagonally. Even one nonzero alpha pixel
        # connecting to the outside must preserve source and stay HOLD.
        im = native.native_image(source_dds())
        draw = ImageDraw.Draw(im)
        draw.rectangle((4, 18, 14, 37), fill=(255, 255, 255, 255))
        draw.point((3, 38), fill=(127, 100, 255, 1))
        draw.point((4, 37), fill=(255, 255, 255, 1))
        src = source_dds()[:128] + im.tobytes("raw", "BGRA")
        data, final, clean, painted, holds = self.run_case(src)
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(holds[0]["reason"],
                         "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")

    def test_diagonal_corner_external_alpha_is_not_missed_by_side_strips(self):
        # (3,5) is outside BOTH legacy strips (left uses y>=6,
        # top uses x>=4); it is nevertheless 8-connected to (4,6).
        im = native.native_image(source_dds())
        ImageDraw.Draw(im).point((4, 6), fill=(255, 255, 255, 1))
        ImageDraw.Draw(im).point((3, 5), fill=(255, 255, 255, 1))
        src = source_dds()[:128] + im.tobytes("raw", "BGRA")
        data, final, clean, painted, holds = self.run_case(src)
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual(holds[0]["reason"],
                         "QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE")

    def test_new_korean_pixel_may_not_touch_protected_native_neighbor(self):
        from hd_existing_candidate_salvage import (
            translated_touches_external_native_ink,
        )
        im = Image.new("RGBA", (128, 112), (0, 0, 0, 0))
        ImageDraw.Draw(im).point((3, 40), fill=(255, 255, 255, 20))
        glyph = Image.new("RGBA", (4, 5), (255, 90, 90, 255))
        box = (4, 6, 116, 100)
        self.assertTrue(translated_touches_external_native_ink(
            im, box, [(glyph, 4, 40)]))
        self.assertFalse(translated_touches_external_native_ink(
            im, box, [(glyph, 15, 40)]))

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
