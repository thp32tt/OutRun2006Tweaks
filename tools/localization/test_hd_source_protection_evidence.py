"""Source/protected pixel ownership evidence never approves held HD art."""
import unittest
from PIL import Image, ImageDraw, ImageChops

from hd_overlap_ownership import prove_overlap_ownership
from hd_source_protection_evidence import separate_masks, evidence_overlay, count


A = {"roi_id": "Q011_1111111111111111", "_bbox": (10, 10, 80, 75)}
B = {"roi_id": "Q011_2222222222222222", "_bbox": (65, 20, 150, 90)}


def source(ambiguous=False):
    img = Image.new("RGBA", (180, 110), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((15, 20, 70, 34), fill=(255, 255, 255, 255))
    draw.rectangle((90, 50, 130, 63), fill=(255, 255, 255, 255))
    if ambiguous:
        draw.rectangle((73, 40, 76, 43), fill=(255, 255, 255, 255))
    return img


class SourceProtectionEvidenceTests(unittest.TestCase):
    def test_native_source_and_protected_masks_are_exact_and_non_overlapping(self):
        img = source()
        diag = {}
        masks, audit = prove_overlap_ownership(
            img, [A, B], {A["roi_id"], B["roi_id"]}, diagnostics=diag)
        self.assertEqual(set(masks), {A["roi_id"], B["roi_id"]})
        self.assertEqual(audit["ambiguous"], [])
        own, protected, ambiguous = separate_masks(
            img, A["_bbox"], diag["partial_owned_masks"][A["roi_id"]],
            diag["ambiguous_native_mask"])
        self.assertGreater(count(own), 0)
        self.assertEqual(count(ambiguous), 0)
        self.assertEqual(ImageChops.multiply(own, protected).getbbox(), None)
        # Foreign label at x=90 is outside A and never part of its clean mask.
        self.assertEqual(own.getpixel((60, 20)), 255)
        view = evidence_overlay(img.crop(A["_bbox"]), own, protected, ambiguous)
        self.assertEqual(view.getpixel((60, 20)), (25, 220, 65, 255))
        self.assertEqual(img.getpixel((70, 30)), (255, 255, 255, 255))

    def test_ambiguous_shared_components_are_protected_not_fake_owned(self):
        img = source(ambiguous=True)
        diag = {}
        proven, audit = prove_overlap_ownership(
            img, [A, B], {A["roi_id"], B["roi_id"]}, diagnostics=diag)
        self.assertFalse(proven)
        self.assertEqual(len(audit["ambiguous"]), 2)
        own, protected, uncertain = separate_masks(
            img, A["_bbox"], diag["partial_owned_masks"][A["roi_id"]],
            diag["ambiguous_native_mask"])
        self.assertGreater(count(own), 0)
        self.assertEqual(count(protected), count(uncertain))
        self.assertEqual(count(uncertain), 16)
        # Only partial proof; the strict DDS assembler MUST keep both held.
        self.assertTrue(diag["partial_proof_not_assembly_approval"])

    def test_alpha_15_is_cosmetic_alpha_16_remains_protected(self):
        img = Image.new("RGBA", (10, 10))
        img.putpixel((3, 3), (255, 255, 255, 15))
        img.putpixel((4, 4), (255, 255, 255, 16))
        owned, protected, uncertain = separate_masks(img, (0, 0, 10, 10), None, None)
        self.assertEqual(count(owned), 0)
        self.assertEqual(count(protected), 1)
        self.assertEqual(protected.getpixel((4, 4)), 255)
        self.assertEqual(count(uncertain), 0)

    def test_mask_preconditions_fail_closed(self):
        img = source()
        owned = Image.new("L", img.size, 0)
        owned.putpixel((15, 15), 255)  # Inside ROI, outside source alpha.
        with self.assertRaisesRegex(ValueError, "OWNER_PIXEL_NOT_NATIVE_CORE"):
            separate_masks(img, A["_bbox"], owned, None)
        with self.assertRaisesRegex(ValueError, "UNSAFE_NATIVE_BBOX"):
            separate_masks(img, (-1, 0, 10, 10), None, None)


if __name__ == "__main__":
    unittest.main()
