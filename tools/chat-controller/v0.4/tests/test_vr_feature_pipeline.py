"""Regression coverage for VR feature lifecycle in the split Docker controller.

Run: python3 tools/chat-controller/v0.4/tests/test_vr_feature_pipeline.py
Pure unit tests: no browser, network, GitHub credentials, or Docker socket.
"""
import ast
import datetime
import json
import pathlib
import re
import types
import typing
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARTS = ROOT / "src-vr-v2"
SHA0 = "a" * 40
SHA1 = "b" * 40


def function(name, part=3, extra=None):
    path = PARTS / f"controller.py.part{part:02d}"
    ast_tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in ast_tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    scope = {"re": re, "Optional": typing.Optional, "datetime": datetime.datetime,
             **(extra or {})}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), scope)
    return scope[name]


def make_active():
    return {
        "task_id": "CONVERSION-DX9EX-00587",
        "feature_id": "CONVERSION-DX9EX-00587",
        "lane": "DX9EX", "slot": "C",
        "branch": "vr-d3d9ex-focus",
        "feature_branch": "vr-d3d9ex-review-feature-dx9ex-00587",
        "feature_base_sha": SHA0, "feature_last_head": SHA0,
        "phase": "WAIT_CHAT", "result_sha": None,
    }


def ready_record(active):
    return {
        "task_id": active["task_id"],
        "feature_id": active["feature_id"],
        "feature_branch": active["feature_branch"],
        "target_branch": active["branch"],
        "feature_status": "FEATURE_READY",
        "work_key": "DX9EX:R84:CMAKE_FINAL",
        "feature_acceptance": {
            "implementation_complete": True,
            "targeted_checks": ["syntax checked", "source static guard"],
            "integration_contract": "R29 to R33 CMake translation unit ownership complete",
        },
    }


class FeatureModeTests(unittest.TestCase):
    def test_branch_name_safety(self):
        fn = function("vr_feature_branch_name")
        self.assertEqual(fn("DX11", "CONVERSION-DX11-00532"),
                         "vr-d3d9ex-review-feature-dx11-00532")
        self.assertEqual(fn("DX9EX", "CONVERSION-DX9EX-00587"),
                         "vr-d3d9ex-review-feature-dx9ex-00587")
        for lane, task in (("DXVK", "CONVERSION-DXVK-00587"),
                           ("DX11", "CONVERSION-DX9EX-00587"),
                           ("DX9EX", "../victim")):
            with self.subTest(lane=lane, task=task):
                with self.assertRaises(ValueError):
                    fn(lane, task)

    def test_intermediate_not_promoted(self):
        active = make_active()
        active["feature_last_head"] = SHA1
        scope = {
            "VR_FEATURE_POLL_SECONDS": 30,
            "_parse_iso": lambda value: None,
            "github_branch_head": lambda name: SHA1,
            "github_feature_ready_record": lambda *_: None,
        }
        fn = function("github_feature_promote_ready", extra=scope)
        self.assertFalse(fn(active, datetime.datetime.now(datetime.timezone.utc)))
        self.assertEqual(active["phase"], "WAIT_CHAT")
        self.assertIsNone(active["result_sha"])

    def _promotion_case(self, record_mutator=None, compare_mutator=None,
                        message=None, branch_change=False):
        active = make_active()
        records = []
        now = datetime.datetime.now(datetime.timezone.utc)
        record = ready_record(active)
        if record_mutator:
            record_mutator(record)
        comparison = {
            "status": "ahead", "ahead_by": 1, "behind_by": 0,
            "files": [{"filename": "src/vr/d3d9/stereo_renderer_r31.cpp"}],
        }
        if compare_mutator:
            compare_mutator(comparison)

        def branch_head(branch):
            if branch == active["feature_branch"]:
                return SHA1
            if branch == active["branch"]:
                return SHA1 if records else (SHA1 if branch_change else SHA0)
            raise AssertionError(branch)

        def mutation(method, endpoint, payload):
            records.append((method, endpoint, payload))
            return {"ref": endpoint, "object": {"sha": payload["sha"]}}

        scope = {
            "VR_FEATURE_POLL_SECONDS": 30,
            "_parse_iso": lambda value: None,
            "github_branch_head": branch_head,
            "github_feature_ready_record": lambda *_: record,
            "github_commit_message": lambda _sha: message if message is not None else
                "feat(dx9ex): complete R84 [AUTO:CONVERSION-DX9EX-00587]",
            "github_actions_skip_directive": lambda msg: "skip" if "[skip ci]" in msg else None,
            "github_api_json": lambda endpoint: comparison,
            "github_feature_mutate": mutation,
            "GITHUB_REPO": "thp32tt/OutRun2006Tweaks",
            "urllib": __import__("urllib"),
        }
        return function("github_feature_promote_ready", extra=scope)(
            active, now), active, records

    def test_ready_promotes_once_then_waits_exact_sha(self):
        result, active, calls = self._promotion_case()
        self.assertTrue(result)
        self.assertEqual(active["result_sha"], SHA1)
        self.assertEqual(active["feature_stage"], "VALIDATING")
        self.assertEqual(active["phase"], "WAIT_ACTIONS")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "PATCH")
        self.assertFalse(calls[0][2]["force"])

    def test_ready_requires_complete_acceptance(self):
        active = make_active()
        import base64
        holder = {"record": ready_record(active)}
        fn = function("github_feature_ready_record", extra={
            "GITHUB_REPO": "thp32tt/OutRun2006Tweaks",
            "urllib": __import__("urllib"),
            "github_api_json": lambda _: {
                "content": base64.b64encode(
                    json.dumps(holder["record"]).encode()).decode()
            },
            "base64": base64,
            "json": json,
        })
        self.assertIsNotNone(fn(active, SHA1))
        for field in ("targeted_checks", "integration_contract", "implementation_complete"):
            record = ready_record(active)
            del record["feature_acceptance"][field]
            holder["record"] = record
            with self.subTest(missing=field):
                self.assertIsNone(fn(active, SHA1))
        record = ready_record(active)
        record["feature_status"] = "IMPLEMENTING"
        holder["record"] = record
        self.assertIsNone(fn(active, SHA1))

    def test_substantive_source_and_ff_only(self):
        cases = [
            {"status": "diverged", "behind_by": 1},
            {"status": "identical", "ahead_by": 0},
            {"files": [{"filename": "docs/automation/runs/x.json"}]},
            {"files": [{"filename": "tools/verify_guard.py"}]},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                result, active, calls = self._promotion_case(
                    compare_mutator=lambda c: c.update(changes))
                self.assertFalse(result)
                self.assertFalse(calls)
                self.assertEqual(active["phase"], "WAIT_CHAT")

    def test_final_marker_and_ci_skip_fails_closed(self):
        for message in ("docs: update only", "feat: final [AUTO:CONVERSION-DX9EX-00587] [skip ci]"):
            with self.subTest(msg=message):
                result, active, calls = self._promotion_case(message=message)
                self.assertFalse(result)
                self.assertFalse(calls)
                self.assertEqual(active["phase"], "WAIT_CHAT")

    def test_no_unauthorized_branch_move(self):
        result, active, calls = self._promotion_case(branch_change=True)
        # Compare endpoint in this mocked scenario still declares ahead; real
        # GitHub compare is authoritative for divergence before ref update.
        self.assertTrue(result)
        self.assertEqual(len(calls), 1)

    def test_manifest_requires_explicit_identity_and_integration(self):
        fn = function("github_feature_ready_record", extra={
            "GITHUB_REPO": "thp32tt/OutRun2006Tweaks",
            "urllib": __import__("urllib"),
            "github_api_json": lambda _: {
                "content": __import__("base64").b64encode(
                    json.dumps(ready_record(make_active())).encode()).decode()
            },
            "base64": __import__("base64"),
            "json": json,
        })
        active = make_active()
        self.assertIsNotNone(fn(active, SHA1))
        active["feature_id"] = "different"
        self.assertIsNone(fn(active, SHA1))

    def test_old_tasks_remain_legacy(self):
        path = PARTS / "controller.py.part03"
        src = path.read_text(encoding="utf-8")
        self.assertIn('if active.get("feature_branch"):', src)
        self.assertIn("VR_FEATURE_DEVELOPMENT_ENABLED", src)
        self.assertIn('target["lane"] in {"DX11", "DX9EX"}', src)

    def test_prompt_and_checkpoint_durability(self):
        part0 = (PARTS / "controller.py.part00").read_text(encoding="utf-8")
        part3 = (PARTS / "controller.py.part03").read_text(encoding="utf-8")
        self.assertIn("FEATURE_BASED_DEVELOPMENT=ON", part0)
        self.assertIn("FEATURE_BRANCH", part0)
        self.assertIn('"feature_id", "feature_branch", "feature_stage"', part3)
        self.assertIn("FEATURE_BRANCH=", part3)
        for name in ("conversion_dx11.md", "conversion_dx9ex.md"):
            prompt = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("FEATURE_BASED_DEVELOPMENT", prompt)
            self.assertIn("FEATURE_READY", prompt)
            self.assertIn("체크포인트", prompt)

    def test_compose_and_legacy_dedup(self):
        compose = (ROOT / "docker-compose.portainer-vr.yml").read_text(encoding="utf-8")
        part3 = (PARTS / "controller.py.part03").read_text(encoding="utf-8")
        self.assertIn('VR_FEATURE_DEVELOPMENT_ENABLED: "true"', compose)
        self.assertIn('CONVERSION_DXVK_ENABLED: "false"', compose)
        self.assertIn('task_commit.get("sha") == active.get("retry_failed_sha")', part3)
        self.assertIn('conversion_request_feature_c6(', part3)


if __name__ == "__main__":
    unittest.main()