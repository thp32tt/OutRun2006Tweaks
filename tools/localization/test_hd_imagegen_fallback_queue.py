"""Fail-closed synthetic QA work-order staging tests, no paid APIs."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import hd_imagegen_fallback_queue as work


class FallbackQueueTests(unittest.TestCase):
    def fixtures(self, d):
        root = Path(d)
        qroot = root / "queue"
        report_path = qroot / "localization/automation_runs/hd_rework_queue/last_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "schema": "outrun.ab-imagegen-hd-strict.v2",
            "active_roi_total": 954, "imported_roi_total": 954,
            "release_approved": False, "runtime_validation": "UNTESTED",
            "source_dds_missing_rows": 0, "source_sha_conflict_rows": 0,
            "zip_sha256": "a" * 64,
        }
        report_path.write_text(json.dumps(report))
        return root, qroot, report

    def fake_build(self, root, report, out, state, reuse_only):
        self.assertFalse(reuse_only)
        return {"schema": "outrun-hd-qa-chat-workqueue-v1",
                "release_approved": False, "runtime_validation": "UNTESTED",
                "new_imagegen_disabled": False,
                "source_asset_sha256": "a" * 64,
                "hold_count": 654, "tasks": []}

    def test_stages_only_explicitly_and_preserves_release_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root, qroot, _ = self.fixtures(d)
            with patch.object(work.queue, "build_queue", side_effect=self.fake_build):
                result = work.stage(root, qroot, root / "out")
            self.assertEqual(result["tasks"], [])
            self.assertFalse(result["release_approved"])

    def test_unclaimed_tasks_must_not_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root, qroot, _ = self.fixtures(d)
            task = {"task_id": "HDRW-A-" + "a" * 20}
            latest = qroot / work.FALLBACK_PREFIX / "latest.json"
            latest.parent.mkdir(parents=True, exist_ok=True)
            latest.write_text(json.dumps({
                "schema": "outrun-hd-qa-chat-workqueue-v1",
                "tasks": [task], "source_asset_sha256": "a" * 64,
                "release_approved": False}))
            with patch.object(work.queue, "build_queue") as build:
                result = work.stage(root, qroot, root / "out")
                build.assert_not_called()
            self.assertEqual(result["status"], "WAIT_UNCLAIMED_IMAGEGEN_TASKS")

    def test_non_strict_or_fake_release_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root, qroot, report = self.fixtures(d)
            report["release_approved"] = True
            p = qroot / "localization/automation_runs/hd_rework_queue/last_report.json"
            p.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "NOT_VERIFIED_STRICT"):
                work.stage(root, qroot, root / "out")

    def test_missing_original_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root, qroot, report = self.fixtures(d)
            report["source_dds_missing_rows"] = 1
            p = qroot / "localization/automation_runs/hd_rework_queue/last_report.json"
            p.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "SOURCE_PROVENANCE"):
                work.stage(root, qroot, root / "out")

    def test_bad_source_zip_sha_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root, qroot, report = self.fixtures(d)
            def fake(*args, **kwargs):
                result = self.fake_build(*args, **kwargs)
                result["source_asset_sha256"] = "b" * 64
                return result
            with patch.object(work.queue, "build_queue", side_effect=fake):
                with self.assertRaisesRegex(ValueError, "FAIL_CLOSED_WORKQUEUE"):
                    work.stage(root, qroot, root / "out")

    def test_no_token_cannot_claim_published(self):
        with tempfile.TemporaryDirectory() as d:
            root, qroot, _ = self.fixtures(d)
            with patch.object(work.queue, "build_queue", side_effect=self.fake_build):
                with self.assertRaisesRegex(ValueError, "GITHUB_TOKEN"):
                    work.stage(root, qroot, root / "out", publish_remote=True)

if __name__ == "__main__":
    unittest.main()
