"""Offline regression: legacy DX11 C6 completion must not strand hourly lane."""
import ast
import base64
import json
import pathlib
import re
import unittest
import urllib
from typing import Optional

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "src-vr-v2" / "controller.py.part03"
SHA = "65efec460053277ff1f071f1f2a8bd31f2874b80"
TASK = "CONVERSION-DX11-01053"


class LegacyC6Tests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf8"))
        names = {"vr_finalize_verified_feature", "conversion_terminal_verdict", "vr_terminal_status"}
        nodes = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in names]
        self.assertEqual({x.name for x in nodes}, names)
        self.puts = []
        self.saved = {}
        def put(method, endpoint, payload):
            self.puts.append((method, endpoint, payload))
            self.saved["value"] = json.loads(base64.b64decode(payload["content"]).decode())
        def get(endpoint):
            return {"content": base64.b64encode(json.dumps(self.saved["value"]).encode()).decode()}
        self.ns = {
            "re": re, "json": json, "base64": base64, "urllib": urllib,
            "Optional": Optional, "GITHUB_REPO": "thp32tt/OutRun2006Tweaks",
            "VR_CHECKPOINT_BRANCH": "chat-controller-downloads",
            "github_commit_message": lambda sha: "fix(dx11) [AUTO:" + TASK + "]",
            "github_feature_mutate": put,
            "github_api_json": get,
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), self.ns)
        self.active = {"task_id": TASK, "branch": "vr-dx11-native-r71",
                       "lane": "DX11", "result_sha": SHA, "feature_contract": None}
        self.record = {"task_id": TASK, "target_branch": "vr-dx11-native-r71",
                       "status": "SOURCE_IMPLEMENTED_CI_PENDING",
                       "checkpoint": "C4_MATERIAL", "automation_validation": "PENDING_GITHUB_ACTIONS",
                       "acceptance_results": {"burst_source_frame": {"status": "PENDING_CI"}},
                       "score_change": 0}
        self.gate = {"head_sha": SHA, "status": "completed", "conclusion": "success"}

    def finish(self, active=None, record=None, gate=None):
        return self.ns["vr_finalize_verified_feature"](
            self.active if active is None else active,
            self.record if record is None else record,
            self.gate if gate is None else gate)

    def test_exact_sha_completed_gate_finalizes_in_controller_only(self):
        result = self.finish()
        self.assertEqual(result["status"], "COMPLETE_BUILD_VERIFIED")
        self.assertEqual(result["checkpoint"], "C6_STATE")
        self.assertEqual(result["automation_validation"], "PASS_EXACT_SHA")
        self.assertEqual(result["validation_bearing_result_sha"], SHA)
        self.assertEqual(result["runtime_validation"], "UNTESTED")
        self.assertEqual(result["score_change"], 0)
        self.assertEqual(result["acceptance_results"], self.record["acceptance_results"])
        self.assertEqual(self.record["status"], "SOURCE_IMPLEMENTED_CI_PENDING")
        self.assertEqual(self.puts[0][0], "PUT")
        self.assertEqual(self.puts[0][2]["branch"], "chat-controller-downloads")
        self.assertTrue(self.puts[0][1].endswith("/" + TASK + "-" + SHA + ".json"))
        self.assertTrue(self.ns["conversion_terminal_verdict"](result, self.active, self.gate)[0])

    def test_failed_in_progress_or_mismatched_ci_never_finalizes(self):
        for gate in ({**self.gate, "status": "in_progress"},
                     {**self.gate, "conclusion": "failure"},
                     {**self.gate, "head_sha": "f" * 40}):
            with self.subTest(gate=gate):
                self.assertIsNone(self.finish(gate=gate))
        self.assertEqual(self.puts, [])

    def test_wrong_task_branch_or_lane_never_finalizes(self):
        self.assertIsNone(self.finish(record={**self.record, "task_id": "OTHER"}))
        self.assertIsNone(self.finish(record={**self.record, "target_branch": "other"}))
        self.assertIsNone(self.finish(active={**self.active, "lane": "DX9EX"}))
        self.assertIsNone(self.finish(record={**self.record, "status": "SOURCE_IMPLEMENTED_RUNTIME_UNTESTED"}))
        self.assertEqual(self.puts, [])

    def test_requires_matching_material_commit_marker(self):
        self.ns["github_commit_message"] = lambda sha: "[AUTO:CONVERSION-DX11-01052]"
        self.assertIsNone(self.finish())
        self.assertFalse(self.puts)


if __name__ == "__main__":
    unittest.main()
