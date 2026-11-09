"""Offline fail-closed tests for HD source-bound HOLD triage; no DDS or API."""
import copy
import tempfile
import unittest
from pathlib import Path

import hd_hold_triage as triage


def row(rid, box, english):
    return {"roi_id": rid, "_bbox": list(box), "english": english,
            "korean": "테스트", "source_dds_path": "textures/load/demo.dds",
            "source_dds_sha256": "a" * 64}


R1 = "Q100_aaaaaaaaaaaaaaaa"
R2 = "Q100_bbbbbbbbbbbbbbbb"
R3 = "Q100_cccccccccccccccc"


def report():
    return {
        "schema": "outrun.ab-imagegen-hd-strict.v2",
        "active_roi_total": 3,
        "translated_roi_generated": 1,
        "source_dds_missing_rows": 0,
        "source_sha_conflict_rows": 0,
        "release_approved": False,
        "runtime_validation": "UNTESTED",
        "zip_sha256": "f" * 64,
        "generated": [{"painted": [{"roi_id": R3}], "holds": []}],
        "holds": [{"roi_ids": [R1, R2], "reason": "ROI_OVERLAP_NEEDS_MANUAL_QA"}],
        "pending_import_holds": [],
        "hold_roi_reason_counts": {"ROI_OVERLAP_NEEDS_MANUAL_QA": 2},
    }


def rows():
    return [row(R1, (0, 0, 50, 25), "FIRST"),
            row(R2, (30, 0, 80, 25), "SECOND"),
            row(R3, (85, 0, 100, 15), "THIRD")]


class StrictHoldTriageTests(unittest.TestCase):
    def test_all_hold_rows_accounted_and_source_neighbors_not_auto_pass(self):
        result = triage.classify(rows(), report())
        self.assertEqual(result["hold_total"], 2)
        self.assertEqual(result["painted_test_only"], 1)
        self.assertEqual(result["geometric_overlap_pairs_diagnostic_only"], 1)
        self.assertEqual(result["overlap_hold_clusters"], 1)
        self.assertEqual(result["tickets"][0]["geometric_neighbor_count"], 1)
        self.assertTrue(all(t["qa_authority"] == "UNAPPROVED_C1_C3_AND_GAME"
                            for t in result["tickets"]))
        self.assertFalse(result["release_approved"])
        self.assertEqual(result["runtime_validation"], "UNTESTED")

    def test_report_and_source_mismatch_is_rejected(self):
        bad = report()
        bad["active_roi_total"] = 4
        with self.assertRaisesRegex(ValueError, "SOURCE_AND_STRICT_QA"):
            triage.classify(rows(), bad)

    def test_duplicate_roi_and_source_sha_conflict_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_INVALID"):
            triage.classify(rows() + [copy.deepcopy(rows()[0])], report())
        changed = rows()
        changed[1]["source_dds_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_DDS_SHA_CONFLICT"):
            triage.classify(changed, report())

    def test_no_pseudo_overlap_without_geometry(self):
        changed = rows()
        changed[1]["_bbox"] = [60, 30, 90, 40]
        with self.assertRaisesRegex(ValueError, "OVERLAP_QA_HOLD_HAS_NO"):
            triage.classify(changed, report())

    def test_qa_authority_and_csv_report_are_preserved(self):
        result = triage.classify(rows(), report())
        with tempfile.TemporaryDirectory() as d:
            triage.write_result(result, Path(d))
            raw = (Path(d) / "hold_triage.csv").read_text("utf-8-sig")
            self.assertIn("ROI_OVERLAP_NEEDS_MANUAL_QA", raw)
            self.assertIn("SOURCE_ALPHA_CONNECTED_COMPONENT_OWNER", raw)
            self.assertEqual(raw.count("\n"), 3)

    def test_fake_release_and_conflicting_report_rejected(self):
        changed = report()
        changed["release_approved"] = True
        with self.assertRaisesRegex(ValueError, "STRICT_SOURCE_QA"):
            triage.classify(rows(), changed)
        changed = report()
        changed["hold_roi_reason_counts"]["ROI_OVERLAP_NEEDS_MANUAL_QA"] = 1
        with self.assertRaisesRegex(ValueError, "QA_HOLD_BREAKDOWN"):
            triage.classify(rows(), changed)


if __name__ == "__main__":
    unittest.main()
