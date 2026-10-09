"""Synthetic failure injection plus the recorded C332 defect; no art approval."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import numpy as np
from PIL import Image

from production_pixel_guard import VERSION, MANIFESTS, check_changed, pixel_checks, sha, verify


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.source = np.zeros((16, 24, 4), dtype=np.uint8)
        self.source[4:10, 4:9] = [230, 230, 230, 255]
        self.source[10:13, 9:14] = [230, 120, 20, 255]  # sibling INSIDE broad edit bbox
        self.clean = self.source.copy()
        self.clean[4:10, 4:9] = 0
        self.letters = np.zeros_like(self.source)
        self.letters[5:9, 5:8] = [240, 240, 240, 255]
        self.final = np.array(Image.alpha_composite(Image.fromarray(self.clean), Image.fromarray(self.letters)))
        self.masks = {k: np.zeros((16, 24), dtype=bool) for k in
                      ("removal", "protected", "edit", "transparent", "effect", "restore")}
        self.masks["edit"][3:14, 3:15] = True
        self.masks["removal"][4:10, 4:9] = True
        self.masks["transparent"][:] = self.masks["removal"]
        self.masks["protected"][10:13, 9:14] = True
        self.masks["effect"][4:10, 4:9] = True
        self.manifest = {"version": VERSION, "coordinates": "native_raw", "stage": "final",
                         "inputs": {}, "masks": {}, "regions": [{"id": "test",
                         "source_anchors": {"top": [8, 4], "bottom": [6, 9]},
                         "candidate_anchors": {"top": [7, 5], "bottom": [6, 8]}}]}
        for key, image in (("source", self.source), ("baseline", self.source),
                           ("clean", self.clean), ("lettering", self.letters), ("candidate", self.final)):
            suffix = ".dds" if key in {"source", "baseline", "candidate"} else ".png"
            self.manifest["inputs"][key] = self.save(key + suffix, image)
        for key, image in self.masks.items():
            self.manifest["masks"][key] = self.save(key + ".png", image.astype(np.uint8) * 255)
        self.manifest["regions"][0]["anchor_evidence"] = self.save("anchors.png", self.source)

    def save(self, path, array):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(array).save(p)
        return {"path": path, "sha256": sha(p.read_bytes())}

    def result(self):
        return verify(self.repo, self.manifest)

    def test_control_is_mechanical_only(self):
        self.assertEqual(self.result()["result"], "MECHANICAL_PASS_VISUAL_REVIEW_REQUIRED")

    def test_plate_can_run_before_lettering(self):
        self.manifest["stage"] = "plate"
        del self.manifest["inputs"]["candidate"]
        self.assertEqual(self.result()["errors"], [])

    def test_dirty_baseline_cannot_hide_lost_source_sibling(self):
        damaged = self.source.copy()
        damaged[10:13, 9:14] = 0
        clean = self.clean.copy()
        clean[10:13, 9:14] = 0
        c = pixel_checks(self.source, damaged, clean, self.masks)
        self.assertEqual(c["clean_protected_diff_from_source"], 15)
        self.assertEqual(c["clean_changed_outside_removal_or_restore"], 0)

    def test_explicit_source_restoration_is_allowed(self):
        damaged = self.source.copy()
        damaged[10:13, 9:14] = 0
        self.masks["restore"][:] = self.masks["protected"]
        self.assertTrue(all(n == 0 for n in pixel_checks(self.source, damaged, self.clean, self.masks).values()))

    def test_rectangular_removal_cannot_eat_sibling(self):
        self.masks["removal"][:] = self.masks["edit"]
        self.assertGreater(pixel_checks(self.source, self.source, self.clean, self.masks)["removal_over_protected"], 0)

    def test_one_pixel_source_residue(self):
        self.clean[4, 4, 3] = 1
        self.manifest["inputs"]["clean"] = self.save("clean.png", self.clean)
        self.assertIn("transparent_plate_residue", self.result()["errors"])

    def test_one_pixel_foreign_box(self):
        self.final[3, 3] = [50, 50, 50, 128]
        self.manifest["inputs"]["candidate"] = self.save("candidate.dds", self.final)
        self.assertIn("final_changed_outside_effect", self.result()["errors"])

    def test_opposite_slant(self):
        self.manifest["regions"][0]["candidate_anchors"]["top"][0] = 5
        self.assertIn("OPPOSITE_OR_UPRIGHT_SLANT:test", self.result()["errors"])

    def test_stale_hash_rejected(self):
        (self.repo / "clean.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.result()

    def test_nonfinite_anchor_rejected(self):
        self.manifest["regions"][0]["source_anchors"]["top"][0] = float("nan")
        with self.assertRaises(ValueError):
            self.result()

    def test_native_dimensions_not_resized(self):
        self.manifest["inputs"]["clean"] = self.save("clean.png", self.clean[:8])
        with self.assertRaises(ValueError):
            self.result()

    def test_changed_candidate_requires_exact_manifest(self):
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "--allow-empty", "-qm", "fixture"], cwd=self.repo, check=True)
        path = "localization/graphics/hd_candidates/test.dds"
        self.manifest["inputs"]["candidate"] = self.save(path, self.final)
        with self.assertRaises(FileNotFoundError):
            check_changed(self.repo, "HEAD")
        p = self.repo / MANIFESTS / (self.manifest["inputs"]["candidate"]["sha256"] + ".json")
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.assertEqual(len(check_changed(self.repo, "HEAD")), 1)
        # A different but well-formed baseline cannot hide collateral changes.
        self.manifest["inputs"]["baseline"] = self.manifest["inputs"]["candidate"]
        p.write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "pre-change candidate"):
            check_changed(self.repo, "HEAD")


class RecordedDefectTest(unittest.TestCase):
    def test_c332_b331_protected_orange_loss_is_detected(self):
        # This is a historical rejected crop, NOT current candidate qualification.
        root = Path(__file__).resolve().parents[2]
        p = root / "localization/graphics/role_B/20261009-B331-Q060-P0-CONDENSED-RACING-ITALIC"
        source = np.array(Image.open(p / "B331_SOURCE_LOSSLESS.png").convert("RGBA"))
        clean = np.array(Image.open(p / "B331_CLEAN_LOSSLESS.png").convert("RGBA"))
        old = np.array(Image.open(p / "B331_CURRENT_LOSSLESS.png").convert("RGBA"))
        r, g, b, a = [source[:, :, i].astype(np.int32) for i in range(4)]
        protected = (a > 90) & (r > 150) & (g > 35) & (b * 100 < r * 55) & (r * 100 > g * 105)
        protected[:90] = False
        masks = {k: np.zeros(source.shape[:2], dtype=bool) for k in
                 ("removal", "protected", "edit", "transparent", "restore")}
        masks["protected"] = protected
        masks["edit"][:] = True
        masks["removal"] = ~protected
        counts = pixel_checks(source, old, clean, masks)
        self.assertEqual(int(protected.sum()), 8892)
        self.assertEqual(counts["clean_protected_diff_from_source"], 8892)


if __name__ == "__main__":
    unittest.main()
