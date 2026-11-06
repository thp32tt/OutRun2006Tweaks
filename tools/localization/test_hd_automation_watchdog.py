"""No-side-effect decision tests for continuous OutRun HD automatic controller."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import io
import json
import urllib.error
from contextlib import redirect_stdout, redirect_stderr

path = Path(__file__).resolve().parent / "hd_automation_watchdog.py"
spec = importlib.util.spec_from_file_location("localization_watchdog", path)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

SHA = "a" * 40
OLD = "b" * 40


def run(sha=SHA, status="completed", conclusion="success", attempt=1, run_id=42):
    return {"id": run_id, "head_sha": sha, "status": status,
            "conclusion": conclusion, "run_attempt": attempt}


class TestController(unittest.TestCase):
    def pick(self, runs, artifacts=(), qa=None, sha=SHA):
        return c.decision(sha, runs, lambda rid: rid in artifacts, qa)

    def test_new_commit_dispatches(self):
        self.assertEqual(self.pick([])["action"], "DISPATCH")
        self.assertEqual(self.pick([run(OLD, conclusion="failure")])["action"], "DISPATCH")

    def test_waits_for_expensive_running_any_sha(self):
        out = self.pick([run(OLD, status="in_progress", conclusion=None)])
        self.assertEqual(out["action"], "WAIT_ACTIVE")
        self.assertEqual(out["run_id"], 42)

    def test_exact_success_with_artifact_dedups(self):
        self.assertEqual(self.pick([run()], artifacts=[42])["action"], "WAIT_FOR_NEW_SOURCE")

    def test_success_without_real_dds_artifact_blocks(self):
        self.assertEqual(self.pick([run()])["action"], "BLOCKED_MISSING_ARTIFACT")

    def test_one_failure_retry_only(self):
        self.assertEqual(self.pick([run(conclusion="failure", attempt=1)])["action"],
                         "RETRY_FAILED_ONCE")
        self.assertEqual(self.pick([run(conclusion="failure", attempt=2)])["action"],
                         "BLOCKED_REPEATED_FAILURE")

    def test_cancelled_same_sha_is_not_infinite_retry(self):
        self.assertEqual(self.pick([run(conclusion="cancelled")])["action"],
                         "BLOCKED_CANCELLED_SAME_SHA")

    def test_release_requires_separate_actual_game_qa(self):
        qa = {"release_approved": True, "runtime_validation": "PASS"}
        self.assertEqual(self.pick([], qa=qa)["action"], "COMPLETE_NO_DISPATCH")
        qa["runtime_validation"] = "UNTESTED"
        self.assertEqual(self.pick([], qa=qa)["action"], "DISPATCH")

    def test_unknown_failure_stays_held(self):
        self.assertEqual(self.pick([run(conclusion="neutral")])["action"],
                         "BLOCKED_UNKNOWN_STATE")

    def test_docs_only_delta_skips_heavy_dds(self):
        self.assertEqual(
            c.decision(SHA, [run(OLD)], lambda rid: rid == 42,
                       relevant_changes=False)["action"],
            "WAIT_NO_MATERIAL_CHANGE")

    def test_material_dds_source_delta_dispatches(self):
        self.assertEqual(
            c.decision(SHA, [run(OLD)], lambda rid: rid == 42,
                       relevant_changes=True)["action"], "DISPATCH")

    def test_failed_comparison_conservatively_dispatches(self):
        self.assertEqual(
            c.decision(SHA, [run(OLD)], lambda rid: rid == 42,
                       relevant_changes=None)["action"], "DISPATCH")

    def test_sha_compare_classifies_material_vs_docs_only(self):
        self.assertFalse(c.material_changed({
            "status":"ahead","total_commits":3,
            "files":[{"filename":"docs/OUTRUN_HD_KOREAN_QA_RECOVERY_20261106.md"},
                     {"filename":"tools/localization/hd_automation_watchdog.py"}]}))
        self.assertTrue(c.material_changed({
            "status":"ahead","total_commits":3,
            "files":[{"filename":"tools/localization/hd_bc3_native_codec.py"}]}))
        self.assertTrue(c.material_changed({
            "status":"ahead","total_commits":2,
            "files":[{"filename":"localization/automation_inputs/candidate_outputs/A/a.png"}]}))
        self.assertTrue(c.material_changed({"status":"diverged","files":[]}))
        self.assertTrue(c.material_changed({"status":"ahead","files":[{}]*300}))


    def test_new_sha_run_does_not_reuse_old_success(self):
        self.assertEqual(self.pick([run(OLD)], artifacts=[42])["action"], "DISPATCH")

    def test_end_to_end_controller_posts_only_exact_branch_dispatch(self):
        seen = []
        class FakeAPI:
            def __init__(self, token):
                self.token = token
            def call(self, path, method="GET", payload=None):
                seen.append((method, path, payload))
                if path.startswith("/git/ref/heads/"):
                    return {"object": {"sha": SHA}}
                if "/actions/workflows/" in path and "/runs?" in path:
                    return {"workflow_runs": []}
                if path.startswith("/contents/"):
                    raise urllib.error.HTTPError("https://api.github.com", 404, "not found", None, None)
                if path.endswith("/dispatches") and method == "POST":
                    return {}
                raise AssertionError("Unexpected API call: " + path)
        stdout = io.StringIO()
        with patch.object(c, "API", FakeAPI), patch.object(c.sys, "argv", ["watchdog","--apply"]), \
             patch.dict(c.os.environ, {"GH_TOKEN":"only-test", "GITHUB_REPOSITORY":c.REPO}, clear=True), \
             redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            self.assertEqual(c.main(), 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["action"], "DISPATCH")
        self.assertEqual(result["side_effect"], "DISPATCH_ACCEPTED_BY_GITHUB")
        posts = [item for item in seen if item[0] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][1], "/actions/workflows/outrun-ab-multi-atlas.yml/dispatches")
        self.assertEqual(posts[0][2], {"ref":c.ASSET_BRANCH})

    def test_end_to_end_document_only_change_does_not_post(self):
        seen = []
        class FakeAPI:
            def __init__(self, token):
                pass
            def call(self, path, method="GET", payload=None):
                seen.append((method, path))
                if path.startswith("/git/ref/heads/"):
                    return {"object": {"sha": SHA}}
                if "/actions/workflows/" in path and "/runs?" in path:
                    return {"workflow_runs": [run(OLD)]}
                if path.startswith("/actions/runs/42/artifacts"):
                    return {"artifacts": [{"name":"outrun-ab-multi-atlas-42",
                                         "size_in_bytes":123, "expired":False}]}
                if path.startswith("/compare/"):
                    return {"status":"ahead","total_commits":1,
                            "files":[{"filename":"docs/new-review.md"}]}
                if path.startswith("/contents/"):
                    raise urllib.error.HTTPError("https://api.github.com", 404, "not found", None, None)
                raise AssertionError("Unexpected API call: " + path)
        stdout=io.StringIO()
        with patch.object(c, "API", FakeAPI), patch.object(c.sys, "argv", ["watchdog","--apply"]), \
             patch.dict(c.os.environ, {"GH_TOKEN":"only-test", "GITHUB_REPOSITORY":c.REPO}, clear=True), \
             redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            self.assertEqual(c.main(), 0)
        result=json.loads(stdout.getvalue())
        self.assertEqual(result["action"], "WAIT_NO_MATERIAL_CHANGE")
        self.assertEqual(result["side_effect"], "NONE")
        self.assertFalse(any(method=="POST" for method, _ in seen))


if __name__ == "__main__":
    unittest.main()
