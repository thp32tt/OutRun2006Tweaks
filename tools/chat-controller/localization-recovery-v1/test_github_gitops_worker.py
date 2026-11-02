"""Offline-only unit smoke: existing Portainer -> GitHub worker, no network."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

WORKER = Path(__file__).with_name("github_gitops_worker.py")
spec = importlib.util.spec_from_file_location("outrun_github_worker", WORKER)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerSecurity(unittest.TestCase):
    def test_remote_target_guard(self):
        worker.validate_publish_path("localization/automation_runs/github_portainer/0123456789abcdef/TEST_ONLY.zip")
        worker.validate_publish_path("localization/automation_runs/github_portainer/0123456789abcdef/qa_report.json")
        for name in (
            "../../.github/workflows/hijack.yml",
            "localization/automation_runs/github_portainer/ZZZZ/qa_report.json",
            "localization/automation_runs/github_portainer/0123456789abcdef/../../../bad",
        ):
            with self.assertRaises(ValueError):
                worker.validate_publish_path(name)

    def test_local_snapshot_guard(self):
        with tempfile.TemporaryDirectory() as home:
            valid = worker.safe_snapshot_path(Path(home), worker.FILES[0])
            self.assertTrue(valid.is_relative_to(Path(home)))
            with self.assertRaisesRegex(ValueError, "UNAPPROVED_GITHUB_INPUT_PATH"):
                worker.safe_snapshot_path(Path(home), "../x")

    def test_publish_no_token_never_writes(self):
        self.assertEqual(
            worker.publish_new("localization/automation_runs/github_portainer/0123456789abcdef/TEST_ONLY.zip",
                               b"proof", ""), "NO_GITHUB_WRITE_TOKEN")

    def test_qa_rejects_fake_game_approval(self):
        with tempfile.TemporaryDirectory() as home:
            report = {"release_approved":True,"runtime_validation":"PASS",
                      "visual_qa":"PASS","native_dds_count":3}
            with self.assertRaisesRegex(ValueError, "GATE_FALSE_RELEASE_APPROVAL"):
                worker.verify_test_only(report,Path(home))

    def test_dedup_without_remote_download(self):
        with tempfile.TemporaryDirectory() as home:
            h=Path(home)
            sha="a"*40
            worker.atomic_json(h/"last_run.json", {
                "remote_head":sha,"status":"SUCCESS","publish_status":"PUBLISHED"})
            with patch.object(worker,"remote_head",return_value=sha), \
                 patch.object(worker,"fetch_snapshot",side_effect=AssertionError("duplicate work")):
                ret=worker.one_cycle(h,"fake-token-not-used")
            self.assertEqual(ret["status"],"NO_NEW_GITHUB_SOURCE")

    def test_sha_and_format(self):
        self.assertEqual(len(worker.hash_bytes(b"a")),64)
        self.assertTrue(worker.BRANCH.startswith("korean-"))
        self.assertEqual(worker.REPO,"thp32tt/OutRun2006Tweaks")


if __name__ == "__main__":
    unittest.main()
