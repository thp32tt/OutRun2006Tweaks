"""Synthetic status tests; no pixel or game PASS is inferred."""
import csv
import tempfile
import unittest
from pathlib import Path

from summarize_qa_state import classify_status, summarize


class TestThroughputReport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root / "localization/graphics"
        folder.mkdir(parents=True)
        with (folder / "asset_queue.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["index", "path", "action", "artwork_status"])
            w.writerow([35, "q035.dds", "localize_text", "c2_q035_scoped_static_pass_official_unpromoted"])
            w.writerow([60, "q060.dds", "localize_text", "c3_strict_pass_pending_ingame"])
            w.writerow([92, "q092.dds", "localize_text", "c2_rework_required_visual_fail"])
            w.writerow([102, "q102.dds", "localize_text", "c2_hold_evidence"])
            w.writerow([110, "q110.dds", "zoom_review", "c3_strict_pass"])
        with (folder / "INGAME_REWORK_BACKLOG.csv").open(
                "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "queue_index", "status"])
            w.writerow(["IGR1", 60, "OPEN_USER_INGAME_FAIL_C388_PENDING_C2"])
            w.writerow(["IGR2", "MIXED", "OPEN_USER_INGAME_FAIL"])
            w.writerow(["IGR3", 92, "CLOSED_USER_GAME_PASS"])

    def test_scoped_is_not_whole_qa(self):
        self.assertEqual("scoped_static_pass_unapproved",
                         classify_status("c2_scoped_static_pass_c3_pending"))
        self.assertEqual("rework_required",
                         classify_status("c3_strict_pass_rework_required"))
        s = summarize(self.root)
        self.assertEqual(4, s["localize_text_total"])
        self.assertEqual(1, s["current_status_counts"]["scoped_static_pass_unapproved"])
        self.assertEqual(1, s["current_status_counts"]["historical_c3_status_not_current_approval"])
        self.assertIsNone(s["approval_count"])

    def test_open_user_report_is_separate_overlay(self):
        s = summarize(self.root)
        self.assertEqual(2, s["open_user_ingame_fail_reports"])
        self.assertEqual([60], s["open_user_ingame_fail_graphics_indexes"])
        self.assertEqual([60], s["historical_c3_status_with_open_game"])
        self.assertEqual("UNTESTED", s["runtime_validation"])


if __name__ == "__main__":
    unittest.main()
