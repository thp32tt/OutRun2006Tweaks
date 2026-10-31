"""Regression: annotated DX11 rollover counter must not hide a verified C6 record.

No GitHub credentials, game assets, Playwright, or hardware required.
Run: python3 tools/chat-controller/v0.4/tests/test_dx11_annotated_c6_record.py
"""
import ast
import base64
import json
from pathlib import Path
import re
import unittest
import urllib.parse
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = "".join((ROOT / "src-vr-v2" / f"controller.py.part{i:02d}").read_text()
              for i in range(4))
NODES = {node.name: node for node in ast.parse(SRC).body
         if isinstance(node, ast.FunctionDef)}


class AnnotatedC6Test(unittest.TestCase):
    def setUp(self):
        self.task_id = "CONVERSION-DX11-01184"
        self.sha = "b6dbd1c15f398d3203e58f5e1104cad9cd0b4a9f"
        self.branch = "vr-dx11-native-r71"
        self.record = {
            "schema_version": 2, "task_id": self.task_id,
            "production_id": self.task_id,
            "attempt": "2/3 (rollover; no retry increment)",
            "target_branch": self.branch,
            "status": "COMPLETE_BUILD_VERIFIED",
            "checkpoint": "C6_STATE",
            "validation_bearing_result_sha": self.sha,
            "material_result_sha": self.sha,
            "automation_validation": "PASS_EXACT_SHA",
            "runtime_validation": "UNTESTED",
        }
        self.env = {
            "re": re, "json": json, "base64": base64,
            "urllib": SimpleNamespace(parse=urllib.parse),
            "GITHUB_REPO": "thp32tt/OutRun2006Tweaks",
            "production_id_from_identifier": lambda x: x,
            "github_api_json": self.api,
            "vr_terminal_status": lambda status: status in
                {"COMPLETE_BUILD_VERIFIED", "COMPLETE", "PASS"},
        }
        for name in ("parse_task_record_counter", "_task_records",
                     "github_task_record", "conversion_terminal_verdict"):
            n = NODES[name]
            exec(compile(ast.fix_missing_locations(ast.Module(
                body=[n], type_ignores=[])), "<test>", "exec"), self.env)

    def api(self, path):
        if "/contents/docs/automation/runs/" in path:
            return {"content": base64.b64encode(
                json.dumps(self.record).encode("utf-8")).decode("ascii")}
        raise AssertionError("Unexpected API request: " + path)

    def test_annotated_rollover_counter(self):
        parser = self.env["parse_task_record_counter"]
        self.assertEqual(parser("2/3 (rollover; no retry increment)", field="attempt"), 2)
        self.assertEqual(parser("1/3", field="attempt"), 1)
        self.assertEqual(parser(2, field="attempt"), 2)
        self.assertEqual(parser("0", field="rollover"), 0)

    def test_invalid_annotation_and_invalid_range_fail_closed(self):
        parser = self.env["parse_task_record_counter"]
        for value in ("2/3 (accept anyway)", "4/3", "2/0",
                      "2/3 (rollover; no retry increment) extra", "-1", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parser(value, field="attempt")

    def test_real_shape_c6_record_found_and_terminal_verdict_passes(self):
        record = self.env["github_task_record"](self.sha, self.task_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["attempt"], "2/3 (rollover; no retry increment)")
        active = {"task_id": self.task_id, "branch": self.branch,
                  "result_sha": self.sha, "feature_contract": None}
        run = {"head_sha": self.sha, "status": "completed", "conclusion": "success"}
        self.assertEqual(
            self.env["conversion_terminal_verdict"](record, active, run),
            (True, "C6_EXACT_SHA_VERIFIED"),
        )


if __name__ == "__main__":
    unittest.main()
