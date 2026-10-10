"""Regression tests for exact-SHA/C6 dispatch terminal evidence.
Run: python3 -m unittest discover -s tools/chat-controller/v0.4/tests -p test_vr_c6_terminal.py
No network or third-party dependencies. The split controller is not imported.
"""
import ast
import datetime
import pathlib
import re
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "src-vr-v2" / "controller.py.part03"


def isolated_function(name, extra=None):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    globals_ = {"re": re, "datetime": datetime.datetime, "Optional": __import__("typing").Optional, **(extra or {})}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("vr_")] + [fn], type_ignores=[]), str(SOURCE), "exec"), globals_)
    return globals_[name]


class C6TerminalTests(unittest.TestCase):
    SHA = "34ec299128d54fae63dc0ed5cbf1c18e9f75434e"

    def setUp(self):
        self.verdict = isolated_function("conversion_terminal_verdict")
        self.record = {
            "task_id": "CONVERSION-DX9EX-00561",
            "target_branch": "vr-d3d9ex-focus",
            "status": "COMPLETE_BUILD_VERIFIED_RUNTIME_UNTESTED",
            "controller_terminal": True,
            "automation_validation": "PASS_EXACT_SHA",
            "validation_bearing_result_sha": self.SHA,
            "pipeline": {"C6_RESULT": "PASS: bookkeeping result stored separately"},
        }
        self.active = {"task_id": "CONVERSION-DX9EX-00561", "branch": "vr-d3d9ex-focus"}
        self.gate = {"head_sha": self.SHA, "status": "completed", "conclusion": "success"}

    def check(self, accepted, record=None, gate=None, active=None):
        actual, reason = self.verdict(
            self.record if record is None else record,
            self.active if active is None else active,
            self.gate if gate is None else gate,
        )
        self.assertIs(actual, accepted, reason)

    def test_explicit_controller_terminal(self):
        self.check(True)

    def test_00559_complete_build_verified_narrative(self):
        self.check(True, {**self.record, "controller_terminal": False,
                          "status": "COMPLETE_BUILD_VERIFIED",
                          "pipeline": {"C6_RESULT": "COMPLETE_BUILD_VERIFIED; SHA held immutable"}})

    def test_00560_runtime_untested_narrative(self):
        self.check(True, {**self.record, "controller_terminal": False,
                          "pipeline": {"C6_RESULT": "PASS immutable material SHA preserved"}})

    def test_c6_state_checkpoint(self):
        self.check(True, {**self.record, "controller_terminal": False,
                          "checkpoint": "C6_STATE", "pipeline": {}})

    def test_c6_state_dict(self):
        self.check(True, {**self.record, "controller_terminal": False,
                          "pipeline": {"C6_STATE": {"status": "COMPLETE"}}})

    def test_status_not_terminal(self):
        for status in ("CI_PENDING", "BLOCKED_UPSTREAM_R175_FULL_GATE",
                       "FAIL", "COMPLETE_PENDING"):
            with self.subTest(status=status):
                self.check(False, {**self.record, "status": status})

    def test_pending_c6_text(self):
        self.check(False, {**self.record, "controller_terminal": False,
                           "pipeline": {"C6_RESULT": "PENDING CI verdict"}})

    def test_controller_terminal_must_be_boolean(self):
        self.check(False, {**self.record, "controller_terminal": "false", "pipeline": {}})

    def test_validation_not_pass(self):
        self.check(False, {**self.record, "automation_validation": "FAIL"})

    def test_result_sha_mismatch(self):
        self.check(False, {**self.record, "validation_bearing_result_sha": "f" * 40})

    def test_missing_result_sha(self):
        self.check(False, {**self.record, "validation_bearing_result_sha": ""})

    def test_task_and_branch_mismatch(self):
        self.check(False, {**self.record, "task_id": "wrong"})
        self.check(False, {**self.record, "target_branch": "wrong"})

    def test_in_progress_or_failed_ci(self):
        self.check(False, gate={**self.gate, "status": "in_progress", "conclusion": None})
        self.check(False, gate={**self.gate, "conclusion": "failure"})

    def test_missing_record(self):
        self.check(False, record={})

    def test_stale_retry_never_promotes_without_gate(self):
        rec = self.record
        audit = []
        extras = {
            "CONTROLLER_MODE": "conversion",
            "_github_commit_list_cache": {},
            "github_branch_head": lambda _branch: self.SHA,
            "github_find_task_commit": lambda _branch, _task: {"sha": self.SHA, "message": "material"},
            "github_task_record": lambda _head, _task: rec,
            "write_runtime": lambda **fields: audit.append(fields),
            "datetime": datetime.datetime,
            "TZ": datetime.timezone.utc,
        }
        guard = isolated_function("github_stale_event_guard", extras)
        active = {"task_id": self.active["task_id"], "production_id": self.active["task_id"],
                  "branch": self.active["branch"], "workflow": "DX9Ex Active Validation"}
        self.assertTrue(guard(active, "retry-surface"))
        self.assertEqual(active["phase"], "WAIT_ACTIONS")
        self.assertIsNone(active.get("terminal"))
        self.assertEqual(active["result_sha"], self.SHA)
        self.assertTrue(audit)


if __name__ == "__main__":
    unittest.main()
