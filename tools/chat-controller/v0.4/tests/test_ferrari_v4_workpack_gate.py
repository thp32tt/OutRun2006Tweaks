"""Ferrari V4 GitHub-workpack dispatch admission regression tests."""
from __future__ import annotations

import ast
import base64
import copy
import datetime
import hashlib
import json
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src-vr-v2" / "controller.py.part03").read_text(encoding="utf-8")
NODES = {n.name: n for n in ast.parse(SOURCE).body
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


class FerrariWorkpackAdmission(unittest.TestCase):
    def setUp(self):
        seq = ["center_console", "visible_seat", "instrument_cluster",
               "dashboard", "steering_wheel", "cross_cockpit_qa"]
        self.queue = {
            "repository": "thp32tt/imsi1", "branch": "main",
            "active_by_slot": {"A": "daytona365", "C": "f50"},
            "cars": [
                {"id": "daytona365", "started_at_utc": "2026-11-08T04:13:41Z"},
                {"id": "f50", "started_at_utc": "2026-11-08T04:35:52Z"},
            ],
            "strategy_v3": {"component_sequence": seq},
        }
        self.workpacks = {
            "A": {"slot": "A", "car_id": "daytona365", "component_order": seq,
                  "current_component": "cross_cockpit_qa", "dispatches_on_component": 1,
                  "latest_accepted_editable_blend_sha256": "a" * 64,
                  "last_material_commit": "a123",
                  "components": {"cross_cockpit_qa": {
                      "status": "IN_PROGRESS", "dispatches_consumed_this_phase": 1,
                      "source_edits_this_phase": 0}}},
            "C": {"slot": "C", "car_id": "f50", "component_order": seq,
                  "current_component": "cross_cockpit_qa", "dispatches_on_component": 0,
                  "latest_accepted_editable_blend_sha256": "b" * 64,
                  "last_material_commit": "c123",
                  "components": {"cross_cockpit_qa": {
                      "status": "NOT_STARTED", "source_edits_this_phase": 0}}},
        }

        def github_api_json(url):
            if url.endswith("FERRARI16_GEOMETRY_QUEUE.json?ref=main"):
                value = self.queue
            elif url.endswith("FERRARI_COCKPIT_WORKPACK_A_DAYTONA365.json?ref=main"):
                value = self.workpacks["A"]
            elif url.endswith("FERRARI_COCKPIT_WORKPACK_C_F50.json?ref=main"):
                value = self.workpacks["C"]
            else:
                raise ValueError(url)
            return {"encoding": "base64", "content": base64.b64encode(
                json.dumps(value).encode()).decode()}

        self.env = {
            "CAR_MODEL_GITHUB_REPO": "thp32tt/imsi1",
            "CAR_MODEL_TARGET_BRANCH": "main",
            "github_api_json": github_api_json,
            "_ferrari_workpack_ssot_cache": {},
            "base64": base64, "json": json, "urllib": urllib,
            "datetime": datetime.datetime,
            "stable_hash": lambda value: hashlib.sha256(value.encode()).hexdigest(),
        }
        node = NODES["ferrari_workpack_dispatch_decision"]
        exec(compile(ast.Module(body=[node], type_ignores=[]),
                     "<ferrari_v4>", "exec"), self.env)
        self.now = datetime.datetime(2026, 11, 9, 6, 20,
                                     tzinfo=datetime.timezone.utc)

    def decision(self, slot, state=None):
        self.env["_ferrari_workpack_ssot_cache"].clear()
        return self.env["ferrari_workpack_dispatch_decision"](
            slot, state or {}, self.now)

    def test_qa_slot_after_24h_allowed_once(self):
        result = self.decision("A")
        self.assertTrue(result["allow"])
        self.assertEqual(result["component"], "cross_cockpit_qa")
        self.assertTrue(result["age_exceeded_24h"])
        self.assertFalse(self.decision("A", {
            "last_workpack_fingerprint_sent": result["fingerprint"]})["allow"])
        self.assertTrue(self.decision("C")["allow"])

    def test_protected_and_held_parts_do_not_consume_chat_slot(self):
        workpack = self.workpacks["A"]
        for part, status in (("dashboard", "P0_POLISH_HOLD"),
                             ("steering_wheel", "P0_POLISH_HOLD")):
            workpack["current_component"] = part
            workpack["components"][part] = {"status": status}
            self.assertFalse(self.decision("A")["allow"])

    def test_outdated_car_exploratory_geometry_paused(self):
        w = self.workpacks["A"]
        w["current_component"] = "visible_seat"
        w["components"]["visible_seat"] = {"status": "NOT_STARTED"}
        self.assertFalse(self.decision("A")["allow"])

    def test_qa_blocked_or_exhausted_is_parked(self):
        w = self.workpacks["A"]
        w["dispatches_on_component"] = 2
        self.assertFalse(self.decision("A")["allow"])
        w["dispatches_on_component"] = 1
        for status in ("WAITING_QA_INPUT", "BLOCKED", "COVERED_PARTIAL_QA"):
            w["components"]["cross_cockpit_qa"]["status"] = status
            self.assertFalse(self.decision("A")["allow"])

    def test_new_eligible_car_geometry_only_before_24h(self):
        self.queue["cars"][1]["started_at_utc"] = "2026-11-09T04:35:52Z"
        w = self.workpacks["C"]
        w["current_component"] = "visible_seat"
        w["components"]["visible_seat"] = {"status": "NOT_STARTED"}
        self.assertTrue(self.decision("C")["allow"])

    def test_mismatched_car_fails_closed(self):
        self.queue["active_by_slot"]["C"] = "daytona365"
        with self.assertRaises(ValueError):
            self.decision("C")

    def test_cycle_queries_workpack_before_chat_navigation(self):
        code = ast.get_source_segment(SOURCE, NODES["car_model_simple_cycle"])
        self.assertLess(code.index("ferrari_workpack_dispatch_decision("),
                        code.index("reg = load_registry(now)"))
        self.assertIn('state["last_workpack_fingerprint_sent"] = admission["fingerprint"]', code)
        self.assertNotIn("repair_components =", code)
        self.assertNotIn("coverage_components =", code)


if __name__ == "__main__":
    unittest.main()