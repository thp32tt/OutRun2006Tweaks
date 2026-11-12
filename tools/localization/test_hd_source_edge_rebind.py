"""Safety and usefulness checks for native-HD source-edge coordinate proposals."""
import unittest
from PIL import Image, ImageDraw
from hd_source_edge_rebind import propose


class SourceEdgeRebindTests(unittest.TestCase):
    def setUp(self):
        self.src = Image.new("RGBA", (120, 70), (0, 0, 0, 0))
        ImageDraw.Draw(self.src).rectangle((18, 15, 46, 22), fill=(255, 255, 255, 255))
        self.box = (20, 10, 40, 30)

    def test_native_source_spill_yields_proposal_not_approval(self):
        got = propose(self.src, self.box, [(80, 10, 100, 30)], pad=16)
        self.assertEqual(got["status"], "SOURCE_COMPONENT_COORDINATE_PROPOSAL_REVIEW_ONLY")
        self.assertEqual(got["proposed_bbox_xyxy"], [18, 10, 47, 30])
        self.assertFalse(got["auto_apply"])
        self.assertFalse(got["release_approved"])

    def test_foreign_ink_and_neighbor_rectangle_stay_protected(self):
        got = propose(self.src, self.box, [(41, 10, 50, 30)], pad=16)
        self.assertEqual(got["status"], "NEIGHBOR_SOURCE_ALPHA_PROTECTED")
        self.assertIsNone(got["proposed_bbox_xyxy"])

    def test_search_boundary_truncation_never_proposes_cut_text(self):
        got = propose(self.src, self.box, [], pad=2)
        self.assertEqual(got["status"], "NEEDS_LARGER_SOURCE_CHILD_OR_ART_REVIEW")
        self.assertIsNone(got["proposed_bbox_xyxy"])

    def test_alpha_15_ignored_but_16_kept(self):
        img = Image.new("RGBA", (70, 40))
        ImageDraw.Draw(img).rectangle((18, 15, 42, 18), fill=(255, 255, 255, 15))
        self.assertEqual(propose(img, (20, 10, 40, 30), [], pad=10)["escaped_core_pixels"], 0)
        ImageDraw.Draw(img).rectangle((18, 15, 42, 18), fill=(255, 255, 255, 16))
        self.assertGreater(propose(img, (20, 10, 40, 30), [], pad=10)["escaped_core_pixels"], 0)

    def test_no_crossing_is_not_false_positive(self):
        img = Image.new("RGBA", (70, 40))
        ImageDraw.Draw(img).rectangle((20, 15, 39, 18), fill=(255, 255, 255, 255))
        got = propose(img, (20, 10, 40, 30), [], pad=10)
        self.assertEqual(got["status"], "NO_NATIVE_CORE_CROSSING")

    def test_invalid_geometry_and_pad_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "EDGE_PAD_OUT_OF_RANGE"):
            propose(self.src, self.box, pad=200)
        with self.assertRaisesRegex(ValueError, "EDGE_SOURCE_BOX_OUT_OF_BOUNDS"):
            propose(self.src, (-1, 0, 20, 40))


if __name__ == "__main__":
    unittest.main()
