"""Behavioral regressions for feature delivery; no live writes or network."""
import asyncio
import ast
import base64
import copy
import json
import re
import unittest
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src-vr-v2/controller.py.part03"
A, B, C = (c * 40 for c in "abc")

def functions(extra=None):
    nodes = [n for n in ast.parse(SOURCE.read_text()).body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    scope = dict(re=re, json=json, base64=base64, urllib=urllib,
                 datetime=datetime, Optional=Optional, TZ=timezone.utc,
                 GITHUB_REPO="thp32tt/OutRun2006Tweaks", log=Mock(),
                 **(extra or {}))
    # Postponed annotations let tests load real function bodies without browser types.
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), scope)
    return scope

class DeliveryContractTests(unittest.TestCase):
    def required(self, scope, name):
        self.assertTrue(name in scope, "missing production delivery behavior: " + name)
        return scope[name]

    def test_statuses_normalized_but_pending_never_complete(self):
        f = self.required(functions(), "vr_terminal_status")
        for status in ("COMPLETE_BUILD_VERIFIED_RUNTIME_UNTESTED", "DONE_BUILD_VERIFIED",
                       "COMPLETE_R239_SCOPED_POST_R175_GATE_RECOVERED"):
            self.assertTrue(f(status))
        for status in ("COMPLETE_PENDING", "FEATURE_READY", "SCOPED_PASS/FULL_GATE_FAIL"):
            self.assertFalse(f(status))

    def test_integration_recovery_rechecks_remote_sha_gate_and_ancestry(self):
        run = dict(id=17, name="Backend Conversion Gate", head_sha=B,
                   status="completed", conclusion="success")
        api = Mock(return_value={"status": "ahead", "behind_by": 0})
        gate = Mock(return_value=run)
        ns = functions(dict(github_api_json=api, github_action_run_by_id=gate,
                            github_branch_head=lambda _: C,
                            github_commit_message=lambda _: "fix [AUTO:CONVERSION-DX11-00536]"))
        f = self.required(ns, "vr_resolve_validation_record")
        record = dict(task_id="CONVERSION-DX11-00536", target_branch="vr-dx11-native-r71",
                      status="COMPLETE_R239_SCOPED_POST_R175_GATE_RECOVERED",
                      checkpoint="C6_STATE", automation_validation="PASS_SUBSEQUENT_HEAD_EXACT_SHA_GATE",
                      material_result_sha=A, validation_bearing_result_sha=A,
                      post_r175_recovery=dict(validation_head=B, validation_head_gate=17))
        active = dict(task_id=record["task_id"], branch=record["target_branch"], workflow=run["name"])
        resolved = f(record, active)
        self.assertEqual(resolved["validation_bearing_result_sha"], B)
        self.assertEqual(resolved["material_result_sha"], A)
        self.assertEqual(record["validation_bearing_result_sha"], A, "remote record must not be mutated")
        self.assertEqual(api.call_count, 2, "both material and target ancestry required")
        self.assertTrue(ns["conversion_terminal_verdict"](resolved, active, run)[0])
        gate.return_value = dict(run, head_sha=A)
        self.assertEqual(f(record, active)["validation_bearing_result_sha"], A)
        gate.return_value = dict(run, conclusion="failure")
        self.assertEqual(f(record, active)["validation_bearing_result_sha"], A)
        gate.return_value = run
        api.return_value = {"status": "diverged", "behind_by": 1}
        self.assertEqual(f(record, active)["validation_bearing_result_sha"], A)

    def test_tools_only_repair_requires_prior_material_ancestry(self):
        f = self.required(functions(), "vr_feature_diff_verdict")
        delta = {"status": "ahead", "ahead_by": 2, "behind_by": 0,
                 "files": [{"filename": "tools/verify_r29.py"}]}
        cumulative = {"status": "ahead", "ahead_by": 4, "behind_by": 0,
                      "files": [{"filename": "src/vr/d3d9/renderer.cpp"}]}
        repair = dict(task_id="CONVERSION-DX9EX-00590", retry_failed_sha=A)
        self.assertTrue(f(repair, delta, cumulative, {"status": "ahead", "behind_by": 0})[0])
        self.assertFalse(f({}, delta, cumulative, {"status": "ahead", "behind_by": 0})[0])
        self.assertFalse(f(repair, delta, cumulative, {"status": "diverged", "behind_by": 1})[0])
        self.assertFalse(f(repair, delta, {"files": []}, {"status": "ahead", "behind_by": 0})[0])
        delta["files"] = [{"filename": "docs/unrelated.md"}]
        self.assertFalse(f(repair, delta, cumulative, {"status": "ahead", "behind_by": 0})[0])

    def test_contract_requires_every_acceptance_item_and_paths(self):
        f = self.required(functions(), "vr_acceptance_verdict")
        contract = dict(feature_id="DX11:FIRST_GAME_DRAW_FRAME", work_key="DX11:LIVE_FRAME",
                        acceptance_items=[dict(id="draw", paths=["src/vr/"], expected="live draw")])
        active = dict(feature_contract=contract)
        record = dict(feature_id=contract["feature_id"], work_key=contract["work_key"],
                      acceptance_results=[dict(id="draw", status="PASS", evidence_paths=["src/vr/draw.cpp"],
                                               validation_command="python tools/check_draw.py")])
        self.assertTrue(f(active, record, ["src/vr/draw.cpp"])[0])
        self.assertFalse(f(active, dict(record, acceptance_results=[]), ["src/vr/draw.cpp"])[0])
        self.assertFalse(f(active, record, ["docs/progress.md"])[0])
        bad = copy.deepcopy(record); bad["acceptance_results"][0]["status"] = "PENDING"
        self.assertFalse(f(active, bad, ["src/vr/draw.cpp"])[0])

    def test_feature_selection_never_reissues_same_completed_or_blocked_outcome(self):
        f = self.required(functions(), "vr_select_feature")
        one = dict(feature_id="DX11:FIRST_FRAME", lane="DX11", work_key="DX11:FRAME",
                   goal="live frame", acceptance_items=[{"id": "frame"}], required_gates=[{"name":"Gate"}])
        backlog = dict(schema_version=1, features=[one])
        self.assertEqual(f(backlog, "DX11", {})["feature_id"], one["feature_id"])
        for collection in ("completed", "blocked"):
            self.assertIsNone(f(backlog, "DX11", {collection:[dict(one, terminal="PASS")]}))
        self.assertIsNone(f(backlog, "DX11", {"active_by_lane":{"A":dict(one, phase="WAIT_CHAT")}}))
        self.assertIsNone(f(backlog, "DXVK", {}))

    def test_forced_rollover_preserves_busy_or_unobservable_owner(self):
        slot = SimpleNamespace(name="A", url="https://chatgpt.com/c/old")
        ns = functions(dict(CONVERSATION_ROLLOVER_ENABLED=True, CONTROLLER_MODE="conversion",
                            CONVERSATION_ROLLOVER_MIN_SECONDS=0, MAX_CHAT_ROLLOVERS_PER_TASK=0,
                            write_runtime=Mock(), load_registry=lambda _: SimpleNamespace(slots=[slot]),
                            send_guard_reason=lambda *args: None, detect_busy=AsyncMock(return_value=True),
                            replace_with_fresh_slot_page=AsyncMock()))
        ns["github_stale_event_guard"] = lambda *args: False
        ns["_parse_iso"] = lambda _: None
        page = Mock(); page.is_closed.return_value = False
        for pages in ({"A": page}, {}):
            active = dict(task_id="CONVERSION-DX11-00537", slot="A")
            self.assertFalse(asyncio.run(ns["queue_rollover_chat"](None, pages, active, "VR_FORCED_40_MINUTE_RESUME")))
            self.assertEqual(active["rollover_pending_reason"], "VR_FORCED_40_MINUTE_RESUME")
        ns["replace_with_fresh_slot_page"].assert_not_called()

    def test_required_jobs_skipped_or_missing_cannot_complete_feature(self):
        f = self.required(functions(), "vr_gate_evidence_verdict")
        requirement = dict(name="DX9Ex Active Validation", jobs=["game", "host", "full-chain-compile", "package"])
        run = dict(name=requirement["name"], head_sha=A, status="completed", conclusion="success")
        jobs = [dict(name=n, status="completed", conclusion="success") for n in requirement["jobs"]]
        self.assertTrue(f(requirement, A, run, jobs)[0])
        self.assertFalse(f(requirement, B, run, jobs)[0])
        self.assertFalse(f(requirement, A, run, jobs[:-1])[0])
        jobs[2]["conclusion"] = "skipped"
        self.assertFalse(f(requirement, A, run, jobs)[0])

if __name__ == "__main__":
    unittest.main()
