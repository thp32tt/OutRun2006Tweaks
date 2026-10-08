"""Evidence/identity gate regression tests; these do NOT certify visual judgment."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from qa_evidence_gate import APPROVALS, CHECKS, POLICY, VIEWS, digest, verify_approval
from export_c_pass_comparison import current_c_pass
from make_region_evidence import generate


class EvidenceGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = Image.new("RGBA", (16, 16), (255, 255, 255, 255))
        self.image.save(self.root / "e.png")
        self.png = self.ref("e.png")
        self.sha = "a" * 64
        self.source_sha = "b" * 64
        self.row = {"index": "154", "path": "textures/load/test.dds", "action": "localize_text",
                    "artwork_status": "c267_c3_strict_pass_pending_ingame", "notes": "C3_STRICT_PASS " + self.sha}
        self.machine = self.write("machine.json", {"candidate_sha256": self.sha,
            "source_sha256": self.source_sha, "result": "PASS", "changed_outside": 0,
            "alpha_outside": 0, "protected_changed": 0, "overlap": 0, "clipping": 0})
        calibration = self.write("calibration.json", {"policy_version": POLICY, "reviewer": "test-fixture",
            "blind_review_completed": True, "cases": [{"kind": kind, "image": self.png,
            "observed": "PASS" if kind == "normal" else "FAIL", "observation": "fixture gate exercise only"}
            for kind in ("normal", "opposite_slant", "clipped_stroke", "residue", "excessive_weight")]})
        finding = {"result": "PASS", "observation": "fixture", "evidence": self.png}
        stages = {}
        for name in ("C", "C3"):
            stages[name] = {"review_id": name, "reviewer": "test-fixture", "calibration": calibration,
                "pixels_before_producer_verdict": True, "prior_defect_observation": "fixture",
                "findings": {"label": {k: copy.deepcopy(finding) for k in CHECKS}}}
        self.data = {"policy_version": POLICY, "queue_index": 154, "asset_path": self.row["path"],
            "mode": "localized", "candidate_sha256": self.sha, "source_sha256": self.source_sha,
            "result": "PASS", "machine_report": self.machine, "clean_plate": self.png,
            "decoded_final": self.png, "stages": stages,
            "text_mips": [{"level": 0, "result": "PASS", "observation": "fixture", "evidence": self.png}],
            "segment_inventory": self.write("segments.json", {"source_sha256": self.source_sha,
                "localizable_segment_ids": ["label"]}),
            "family_profile": self.write("family.json", {"family_id": "test",
                "reference_observation": "fixture", "reference_image": self.png}),
            "regions": [{"id": "label", "bbox": [0, 0, 16, 16], "readable_transform": "flip_y",
                "slant": {"source_top_minus_bottom_dx": 2, "candidate_top_minus_bottom_dx": 2,
                          "anchor_observation": "fixture"}, "views": {k: self.png for k in VIEWS}}]}

    def ref(self, name):
        return {"path": name, "sha256": digest((self.root / name).read_bytes())}

    def write(self, name, data):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
        return self.ref(name)

    def check(self, **kwargs):
        self.write((APPROVALS / "q154.json").as_posix(), self.data)
        return verify_approval(self.root, self.row, self.sha, **kwargs)[1]

    def test_complete_evidence_accepted(self):
        self.assertEqual([], self.check(source_sha=self.source_sha, candidate_image=self.image))

    def test_notes_alone_do_not_approve(self):
        self.assertTrue(verify_approval(self.root, self.row, self.sha)[1])

    def test_changed_candidate_rejected(self):
        self.data["candidate_sha256"] = "c" * 64
        self.assertTrue(self.check())

    def test_changed_source_rejected(self):
        self.assertTrue(self.check(source_sha="c" * 64))

    def test_missing_check_rejected(self):
        del self.data["stages"]["C3"]["findings"]["label"]["glyph_integrity"]
        self.assertTrue(self.check())

    def test_opposite_slant_rejected(self):
        self.data["regions"][0]["slant"]["candidate_top_minus_bottom_dx"] = -2
        self.assertTrue(self.check())

    def test_visual_fail_overrides_machine_pass(self):
        self.data["stages"]["C3"]["findings"]["label"]["glyph_integrity"]["result"] = "FAIL"
        self.assertTrue(self.check())

    def test_unknown_region_not_silently_omitted(self):
        self.data["regions"] = []
        self.assertTrue(self.check())

    def test_missing_mips_rejected(self):
        self.assertTrue(self.check(mip_count=3))

    def test_stale_png_rejected(self):
        Image.new("RGBA", (16, 16)).save(self.root / "e.png")
        self.assertTrue(self.check())

    def test_preencode_png_not_dds_rejected(self):
        self.assertTrue(self.check(candidate_image=Image.new("RGBA", (16, 16))))

    def test_identical_review_identity_rejected(self):
        self.data["stages"]["C3"]["review_id"] = "C"
        self.assertTrue(self.check())

    def test_failed_calibration_rejected(self):
        p = self.root / "calibration.json"
        d = json.loads(p.read_text()); d["cases"][1]["observed"] = "PASS"
        r = self.write("calibration.json", d)
        for stage in self.data["stages"].values(): stage["calibration"] = r
        self.assertTrue(self.check())

    def test_missing_candidate_is_not_preserve_policy(self):
        self.write((APPROVALS / "q154.json").as_posix(), self.data)
        self.assertTrue(verify_approval(self.root, self.row, "")[1])

    def test_hold_and_fail_never_selected_from_pass_substring(self):
        for status in ("c3_pass_hold_strict_recheck", "c3_pass_rework_required", "c3_pass_visual_fail"):
            self.assertFalse(current_c_pass({**self.row, "artwork_status": status}))

    def test_open_user_ingame_failure_vetoes_historical_approval(self):
        backlog = self.root / "localization/graphics/INGAME_REWORK_BACKLOG.csv"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        backlog.write_text("queue_index,status\n154,OPEN_USER_INGAME_FAIL\n", encoding="utf-8")
        self.assertIn("active user in-game regression blocks approval", self.check())

    def test_other_open_ingame_index_does_not_block_this_candidate(self):
        backlog = self.root / "localization/graphics/INGAME_REWORK_BACKLOG.csv"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        backlog.write_text("queue_index,status\n155,OPEN_USER_INGAME_FAIL\n", encoding="utf-8")
        self.assertEqual([], self.check())

    def test_current_rework_status_blocks_legacy_C3_approval(self):
        self.row["artwork_status"] = "user_ingame_20261009_rework_required"
        self.assertIn("current queue REWORK/HOLD/FAIL blocks approval", self.check())

    def test_historical_closed_user_report_is_not_a_new_veto(self):
        backlog = self.root / "localization/graphics/INGAME_REWORK_BACKLOG.csv"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        backlog.write_text("queue_index,status\n154,C_STATIC_PASS_PENDING_INGAME_RETEST\n", encoding="utf-8")
        self.assertEqual([], self.check())

    def test_path_escape_rejected(self):
        self.data["decoded_final"]["path"] = "../outside.png"
        self.assertTrue(self.check())

    def test_lossless_region_generator_decodes_dds(self):
        self.image.save(self.root / "source.dds")
        self.image.save(self.root / "candidate.dds")
        result = generate(self.root, self.root / "source.dds", self.root / "e.png",
                          self.root / "candidate.dds", [{"id": "label", "bbox": [0, 0, 16, 16],
                          "readable_transform": "flip_y"}], self.root / "out")
        self.assertTrue(VIEWS.issubset(result["regions"][0]["views"]))
        self.assertEqual("EVIDENCE_ONLY_NOT_APPROVAL", result["result"])


if __name__ == "__main__":
    unittest.main()
