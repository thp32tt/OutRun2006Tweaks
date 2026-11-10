"""Regression for fail-closed overlapping ROI owner masks and native HD DDS."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from hd_overlap_ownership import prove_overlap_ownership

spec = importlib.util.spec_from_file_location("hd_batch_overlap", HERE / "github_ab_imagegen_atlas_batch.py")
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)
spec = importlib.util.spec_from_file_location("hd_strict_overlap", HERE / "hd_strict_qa.py")
strict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strict)


A = {"roi_id": "Q012_1234567890abcdef", "english": "FIRST",
     "korean": "첫째", "_bbox": [10, 8, 83, 80], "_candidate_rel": "a.png"}
B = {"roi_id": "Q012_fedcba0987654321", "english": "SECOND",
     "korean": "둘째", "_bbox": [65, 18, 144, 108], "_candidate_rel": "b.png"}


def native_dds(image):
    header = bytearray(128)
    header[:4] = b"DDS "
    for offset, value in ((4, 124), (12, image.height), (16, image.width),
                          (28, 1), (76, 32), (80, 65), (88, 32)):
        struct.pack_into("<I", header, offset, value)
    struct.pack_into("<IIII", header, 92, *batch.MASKS)
    return bytes(header) + image.tobytes("raw", "BGRA")


def fixture(ambiguous=False, connected=False):
    original = Image.new("RGBA", (192, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(original)
    draw.rectangle((20, 30, 72, 42), fill=(255, 255, 255, 255))
    draw.rectangle((90, 54, 130, 68), fill=(255, 255, 255, 255))
    if ambiguous:
        # In both metadata ROIs, no unique source ROI anchor.
        draw.rectangle((75, 25, 79, 27), fill=(255, 255, 255, 255))
    if connected:
        draw.line((72, 42, 90, 54), fill=(255, 255, 255, 255), width=2)
    return original


def candidate(path):
    image = Image.new("RGBA", (240, 100), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((15, 15, 210, 80), fill=(120, 220, 100, 255))
    image.save(path)


def run_assembly(src):
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        candidate(repo / "a.png")
        candidate(repo / "b.png")
        return strict.process_strict_atlas(
            native_dds(src), [dict(A), dict(B)], repo, "NORMAL",
            batch.native_image, batch.imported_candidate,
            batch.conflicting_rois, batch.dominant_container_holds)


class NativeOverlapProofTests(unittest.TestCase):
    def test_overlap_intersects_actual_native_source_but_exclusive_anchors_prove_owners(self):
        img = fixture()
        conflict = strict.source_ink_conflicts(img, [A, B], batch.conflicting_rois)
        self.assertEqual(conflict, {A["roi_id"], B["roi_id"]})
        masks, audit = prove_overlap_ownership(img, [A, B], conflict)
        self.assertEqual(set(masks), conflict)
        self.assertEqual(audit["ambiguous"], [])
        self.assertTrue(masks[A["roi_id"]].getpixel((70, 36)))
        self.assertFalse(masks[B["roi_id"]].getpixel((70, 36)))
        self.assertTrue(masks[B["roi_id"]].getpixel((95, 60)))

    def test_native_dds_overlap_rescue_rewrites_only_original_owned_source(self):
        src = fixture()
        data, final, clean, painted, holds = run_assembly(src)
        self.assertIsNotNone(data)
        self.assertEqual(len(painted), 2)
        self.assertFalse(holds)
        self.assertEqual(data[:128], native_dds(src)[:128])
        self.assertEqual(len(data), len(native_dds(src)))
        self.assertEqual(
            ImageChops.difference(batch.native_image(data), final).getbbox(), None
        )
        self.assertTrue(all("SOURCE_ALPHA_CONNECTED_COMPONENT_EXCLUSIVE_OWNER_TEST_ONLY"
                            in item["auto_salvage"] for item in painted))
        for item in painted:
            self.assertEqual(item["original_line_count"], item["translated_line_count"])
        # Every original pixel removed from CLEAN, while remote protected atlas
        # art remains identical. No approval is synthesized by these receipts.
        self.assertIsNone(clean.getchannel("A").getbbox())
        self.assertEqual(final.getpixel((185, 115)), src.getpixel((185, 115)))

    def test_sub16_shared_alpha_fringe_is_cosmetic_not_overlap_ink(self):
        # Use an otherwise empty shared ROI; fixture() already has real ink
        # within the shared rectangle and cannot establish the fringe boundary.
        src = Image.new("RGBA", (192, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(src)
        draw.point((75, 25), fill=(255, 255, 255, 15))
        self.assertFalse(strict.shared_native_alpha(
            src.getchannel("A"), A["_bbox"], B["_bbox"]))
        draw.point((75, 25), fill=(255, 255, 255, 16))
        self.assertTrue(strict.shared_native_alpha(
            src.getchannel("A"), A["_bbox"], B["_bbox"]))

    def test_ambiguous_unanchored_shared_component_keeps_both_held(self):
        src = fixture(ambiguous=True)
        masks, audit = prove_overlap_ownership(
            src, [A, B], {A["roi_id"], B["roi_id"]}
        )
        self.assertFalse(masks)
        self.assertEqual(set(audit["ambiguous"]), {A["roi_id"], B["roi_id"]})
        data, _, _, painted, holds = run_assembly(src)
        self.assertIsNone(data)
        self.assertFalse(painted)
        self.assertEqual({item["reason"] for item in holds},
                         {"ROI_OVERLAP_NEEDS_MANUAL_QA"})

    def test_connected_shared_ink_with_two_exclusive_anchors_remains_hold(self):
        src = fixture(connected=True)
        masks, audit = prove_overlap_ownership(
            src, [A, B], {A["roi_id"], B["roi_id"]}
        )
        self.assertFalse(masks)
        self.assertEqual(set(audit["ambiguous"]), {A["roi_id"], B["roi_id"]})

    def test_identical_roi_boxes_never_invent_an_owner(self):
        src = fixture()
        copy = dict(A, roi_id="Q012_aaaaaaaaaaaaaaaa")
        masks, audit = prove_overlap_ownership(
            src, [A, copy], {A["roi_id"], copy["roi_id"]}
        )
        self.assertFalse(masks)
        self.assertEqual(len(audit["ambiguous"]), 2)

    def test_budget_and_bad_box_are_safe_holds(self):
        src = fixture()
        bad = dict(A, _bbox=[-1, 0, 83, 80])
        masks, audit = prove_overlap_ownership(
            src, [bad, B], {bad["roi_id"], B["roi_id"]}
        )
        self.assertFalse(masks)
        self.assertEqual(audit["reason"], "ROI_OUT_OF_NATIVE_BOUNDS")


if __name__ == "__main__":
    unittest.main()
