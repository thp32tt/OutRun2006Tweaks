"""Unit tests for scheduled localization Chrome rotation, without Docker or auth files."""
from __future__ import annotations

import ast
import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "tools/chat-controller/v0.4/src"


def load_rotation():
    source = "".join(p.read_text(encoding="utf-8") for p in sorted(CONTROLLER.glob("controller.py.part*")))
    compile(source, "<assembled-controller>", "exec")
    nodes = [node for node in ast.parse(source).body
             if isinstance(node, ast.AsyncFunctionDef) and node.name == "check_chrome_recycle"]
    assert len(nodes) == 1
    env = {
        "asyncio": asyncio, "json": json, "datetime": datetime,
        "TZ": timezone.utc, "log": Mock(), "write_runtime": Mock(),
        "save_registry": Mock(), "CHROME_RECYCLE_ENABLED": True,
        "CHROME_RECYCLE_INTERVAL_SECONDS": 7200,
        "CHROME_RECYCLE_BUSY_GRACE_SECONDS": 1800,
        "CHROME_RECYCLE_BUSY_PROBE_SECONDS": 1,
        "detect_busy": AsyncMock(return_value=False),
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 "<chrome-recycle>", "exec"), env)
    return env


class ChromeRecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = load_rotation()
        self.env["CHROME_RECYCLE_FILE"] = Path(self.tmp.name) / "chrome_recycle.json"
        def atomic_json(path, content):
            path.write_text(json.dumps(content), encoding="utf-8")
        self.env["atomic_json"] = atomic_json
        self.registry = SimpleNamespace(active_lanes={"A": {"state": "PRODUCING", "asset_path": "x.dds"}})
        self.pages = {"A": SimpleNamespace(is_closed=lambda: False),
                      "B": SimpleNamespace(is_closed=lambda: False),
                      "C1": SimpleNamespace(is_closed=lambda: False),
                      "C2": SimpleNamespace(is_closed=lambda: False)}

    def check(self, seconds):
        return asyncio.run(self.env["check_chrome_recycle"](
            None, self.pages, self.registry, seconds))

    def test_no_recycle_before_two_hours(self):
        self.assertFalse(self.check(7199))
        self.env["save_registry"].assert_not_called()
        self.assertFalse(self.env["CHROME_RECYCLE_FILE"].exists())

    def test_recycle_when_idle_preserves_task_identifiers(self):
        self.assertTrue(self.check(7200))
        self.env["save_registry"].assert_called_once_with(self.registry)
        record = json.loads(self.env["CHROME_RECYCLE_FILE"].read_text())
        self.assertEqual(record["count"], 1)
        self.assertEqual(record["busy_slots_at_request"], [])
        self.assertEqual(self.registry.active_lanes["A"]["asset_path"], "x.dds")
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["status"], "chrome_recycle_requested")
        self.assertTrue(self.check(7201))
        self.assertEqual(json.loads(self.env["CHROME_RECYCLE_FILE"].read_text())["count"], 2)

    def test_busy_tab_defers_recycle_without_writing_checkpoint(self):
        self.env["detect_busy"] = AsyncMock(side_effect=[True, False, False, False])
        self.assertFalse(self.check(7200))
        self.assertFalse(self.env["CHROME_RECYCLE_FILE"].exists())
        self.env["save_registry"].assert_not_called()
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["chrome_recycle_deferred_slots"], ["A"])

    def test_after_grace_recycles_with_exact_existing_task_identity(self):
        self.env["detect_busy"] = AsyncMock(side_effect=[False, True, False, False])
        self.assertTrue(self.check(9000))
        self.assertEqual(json.loads(self.env["CHROME_RECYCLE_FILE"].read_text())["busy_slots_at_request"], ["B"])
        self.assertEqual(self.registry.active_lanes["A"]["asset_path"], "x.dds")
        self.env["save_registry"].assert_called_once()

    def test_unknown_busy_state_is_deferred_and_not_silently_ignored(self):
        self.env["detect_busy"] = AsyncMock(side_effect=RuntimeError("renderer unresponsive"))
        self.assertFalse(self.check(7200))
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["chrome_recycle_deferred_slots"],
                         ["A", "B", "C1", "C2"])
        self.env["save_registry"].assert_not_called()

    def test_feature_off_never_stops_controller(self):
        self.env["CHROME_RECYCLE_ENABLED"] = False
        self.assertFalse(self.check(100000))
        self.env["save_registry"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
