"""Failure injection for separated lettering; synthetic data never qualifies art."""
import json
import unittest
import numpy as np

from compose_lettering import compose, verify_lettering
import test_production_pixel_guard as guard_tests


class LetteringTests(unittest.TestCase):
    setUp = guard_tests.GuardTests.setUp
    save = guard_tests.GuardTests.save
    save_json = guard_tests.GuardTests.save_json

    def test_exact_face_composite(self):
        image, report = compose(self.repo, self.recipe)
        self.assertTrue(np.array_equal(np.array(image), self.letters))
        self.assertIn("REQUIRES_VISUAL", report["result"])

    def test_changed_geometry_invalidates_review(self):
        a = self.letters[:, :, 3].copy()
        a[5, 5] = 0
        self.recipe["geometry"] = self.save("geometry2.png", a)
        with self.assertRaisesRegex(ValueError, "stale"):
            compose(self.repo, self.recipe)

    def test_effect_cannot_replace_face(self):
        self.recipe["layers"][0]["role"] = "rim"
        with self.assertRaisesRegex(ValueError, "one face"):
            compose(self.repo, self.recipe)

    def test_face_alpha_must_match_reviewed_geometry(self):
        a = self.letters.copy()
        a[5, 5, 3] = 0
        self.recipe["layers"][0]["input"] = self.save("badface.png", a)
        with self.assertRaisesRegex(ValueError, "Face alpha"):
            compose(self.repo, self.recipe)

    def test_highlight_cannot_escape(self):
        a = np.zeros_like(self.letters)
        a[0, 0] = [255, 255, 255, 1]
        self.recipe["layers"].append({"role": "highlight", "input": self.save("badlight.png", a)})
        with self.assertRaisesRegex(ValueError, "Highlight escapes"):
            compose(self.repo, self.recipe)

    def test_final_lettering_tampering(self):
        a = self.letters.copy()
        a[5, 5, 0] = 10
        self.manifest["inputs"]["lettering"] = self.save("other.png", a)
        with self.assertRaisesRegex(ValueError, "differs"):
            verify_lettering(self.repo, self.manifest)

    def test_missing_recipe_blocks_publication(self):
        del self.manifest["lettering_recipe"]
        with self.assertRaises(KeyError):
            verify_lettering(self.repo, self.manifest)

    def test_metal_cannot_use_flat_only(self):
        self.recipe["route"] = "layered_metal"
        review = json.loads((self.repo / "geometry_review.json").read_text())
        review["route"] = "layered_metal"
        self.recipe["geometry_review"] = self.save_json("geometry_review.json", review)
        with self.assertRaisesRegex(ValueError, "Metal route"):
            compose(self.repo, self.recipe)


if __name__ == "__main__":
    unittest.main()
