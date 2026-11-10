"""Only exact SHA-pinned user PNG QA archive may be admitted to TEST_ONLY."""
import tempfile
import unittest
import zipfile
from pathlib import Path
import hd_manual_user_import as manual


class ManualUserSourceImport(unittest.TestCase):
    def test_absent_manual_zip_does_not_affect_previous_ab(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(manual.apply_user_manual_candidates(d, {}), 0)

    def test_forged_zip_cannot_change_candidate_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root/manual.INPUT_ZIP
            archive.parent.mkdir(parents=True)
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("QA_MANIFEST.json", '{"release_approved":true}')
            row = {"roi_id": next(iter(manual.EXPECTED)),
                   "_candidate_rel": "old_ab.png"}
            before = row.copy()
            with self.assertRaisesRegex(ValueError, "MANUAL_QA_ZIP_SHA_MISMATCH"):
                manual.apply_user_manual_candidates(root, {"source.dds": [row]})
            self.assertEqual(row, before)

    def test_stage_child_is_inside_original_and_separate_from_other_labels(self):
        old = manual.STAGE_ORIGINAL_BBOX
        child = manual.STAGE_CHILD_BBOX
        self.assertEqual(old, [0,319,427,512])
        self.assertTrue(old[0] <= child[0] < child[2] <= old[2])
        self.assertTrue(old[1] <= child[1] < child[3] <= old[3])
        self.assertGreaterEqual(child[1], 436)
        self.assertEqual(len(manual.EXPECTED), 6)
        self.assertEqual(manual.EXPECTED["Q205_bf0d812a762a295e"][0],
                         manual.EXPECTED["Q205_0e672581cf837a7d"][0])


if __name__ == "__main__":
    unittest.main()
