"""Recovery v1-only regression: 4 workers, fixed schedule, safe Chrome repair.

No imports from the later v0.4 event/asset queue engine.
"""
from __future__ import annotations

import asyncio
import ast
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "".join((ROOT / "src" / ("controller.py.part%02d" % i)).read_text(encoding="utf-8")
                 for i in range(4))
spec = importlib.util.spec_from_file_location("recovery_chrome_maintenance", ROOT / "chrome_maintenance.py")
maint = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = maint
spec.loader.exec_module(maint)


def run(coro):
    return asyncio.run(coro)


class FakePage:
    def __init__(self, url="https://chatgpt.com/c/saved", closed=False, probe=None):
        self.url = url
        self.closed = closed
        self.handlers = {}
        self.goto_urls = []
        self.probe = probe or {
            "url": url, "title": "ChatGPT", "body": "Need to fix Aw, Snap! issue",
            "composer": True,
        }
    def on(self, event, handler):
        self.handlers[event] = handler
    def is_closed(self):
        return self.closed
    async def evaluate(self, code):
        return self.probe
    async def close(self):
        self.closed = True
    async def screenshot(self, **kwargs):
        return b""
    async def goto(self, url, **kwargs):
        self.url = url
        self.goto_urls.append(url)


class FakeContext:
    def __init__(self):
        self.browser = SimpleNamespace(is_connected=lambda: True)
        self.created = []
    async def new_page(self):
        page = FakePage()
        self.created.append(page)
        return page


class RecoveryMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = {}
        self.saved = "https://chatgpt.com/c/saved"
        self.slots = [SimpleNamespace(name=n, url=self.saved, runs=5)
                      for n in ("A", "B", "C1", "C2")]
        self.pages = {n.name: FakePage() for n in self.slots}
        self.context = FakeContext()
        self.status = Mock()
        self.maint_recycle_path = Path(self.temp.name) / "chrome_recycle.json"
        patcher = patch.object(maint, "CHROME_RECYCLE_FILE", self.maint_recycle_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, protected=frozenset()):
        return run(maint.scan_slot_tabs(
            self.context, self.pages, self.slots, self.state, set(protected),
            "https://chatgpt.com/g/test", self.status, lambda url: "/c/" in url))

    def test_four_lane_policy_and_fixed_six_launches(self):
        compile(SOURCE, "<recovery-v1-controller>", "exec")
        tree = ast.parse(SOURCE)
        assignments = {node.targets[0].id: ast.literal_eval(node.value)
                       for node in tree.body if isinstance(node, ast.Assign)
                       and len(node.targets) == 1
                       and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id in {"LOCALIZATION_SLOT_NAMES", "SCHEDULED_LOCALIZATION_LANES"}}
        self.assertEqual(assignments["LOCALIZATION_SLOT_NAMES"], ("A", "B", "C1", "C2"))
        self.assertEqual(assignments["SCHEDULED_LOCALIZATION_LANES"],
                         {0:"A", 10:"C1", 20:"C2", 30:"B", 40:"C1", 50:"C2"})
        self.assertNotIn("next_production_id", SOURCE)
        self.assertNotIn("task_events", SOURCE)

    def test_legacy_three_tabs_migrate_in_place_and_keep_daily_history(self):
        wanted = {"Slot", "Registry", "logical_date", "new_registry", "load_registry", "save_registry"}
        tree = ast.parse(SOURCE)
        nodes = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted]
        self.assertEqual(len(nodes), len(wanted))
        sandbox = Path(self.temp.name)
        registry_path = sandbox / "chat_registry.json"
        environment = {
            "dataclass": dataclass, "asdict": asdict,
            "Optional": __import__("typing").Optional, "datetime": datetime,
            "timedelta": timedelta, "TZ": timezone.utc,
            "ROLLOVER_HOUR": 2, "CHAT_SLOTS": 4, "CONTROLLER_MODE": "localization",
            "LOCALIZATION_SLOT_NAMES": ("A", "B", "C1", "C2"),
            "STATE_DIR": sandbox, "REGISTRY_FILE": registry_path,
            "json": json, "log": Mock(), "Slot": None, "Registry": None,
        }
        module = ast.Module(
            body=[ast.ImportFrom(module="__future__", names=[
                ast.alias(name="annotations")], level=0)] + nodes,
            type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), "<recovery-registry>", "exec"),
             environment)
        now = datetime(2026, 10, 10, 9, tzinfo=timezone.utc)
        old_date = "2026-10-08"
        old = {
            "logical_date": old_date, "next_slot": 2,
            "slots": [{"name": "A", "url": "https://chatgpt.com/c/a", "runs": 3},
                      {"name": "B", "url": "https://chatgpt.com/c/b", "runs": 4},
                      {"name": "C", "url": "https://chatgpt.com/c/c", "runs": 17,
                       "last_result": "sent"}],
            "rate_limit_attempts": 2, "rate_limit_until": None,
            "last_global_send_at": "2026-10-09T20:00:00+09:00",
        }
        registry_path.write_text(json.dumps(old), encoding="utf-8")
        restored = environment["load_registry"](now)
        self.assertEqual([s.name for s in restored.slots], ["A", "B", "C1", "C2"])
        self.assertEqual(restored.slots[2].url, "https://chatgpt.com/c/c")
        self.assertEqual(restored.slots[2].runs, 17)
        self.assertEqual(restored.slots[2].last_result, "sent")
        self.assertEqual(restored.rate_limit_attempts, 2)
        self.assertEqual(restored.next_slot, 2)
        self.assertEqual(restored.slots[3].runs, 0)
        self.assertEqual(json.loads((sandbox / ("chat_registry_" + old_date + ".json")).read_text())["slots"][2]["name"], "C")
        new_state = environment["load_registry"](now)
        self.assertEqual(new_state.slots[2].runs, 17)
        self.assertEqual(new_state.slots[2].name, "C1")

    def test_corrupt_legacy_registry_is_not_erased(self):
        wanted = {"Slot", "Registry", "logical_date", "new_registry", "load_registry", "save_registry"}
        nodes = [n for n in ast.parse(SOURCE).body
                 if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in wanted]
        sandbox = Path(self.temp.name)
        path = sandbox / "chat_registry.json"
        path.write_text("{corrupt", encoding="utf-8")
        env = {"dataclass": dataclass, "asdict": asdict, "datetime": datetime,
               "timedelta": timedelta, "TZ": timezone.utc, "ROLLOVER_HOUR": 2,
               "CHAT_SLOTS": 4, "CONTROLLER_MODE": "localization",
               "LOCALIZATION_SLOT_NAMES": ("A", "B", "C1", "C2"),
               "STATE_DIR": sandbox, "REGISTRY_FILE": path, "json": json, "log": Mock()}
        mod = ast.Module(body=[
            ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
        ] + nodes, type_ignores=[])
        exec(compile(ast.fix_missing_locations(mod), "<registry-test>", "exec"), env)
        with self.assertRaises(json.JSONDecodeError):
            env["load_registry"](datetime(2026, 10, 10, tzinfo=timezone.utc))
        self.assertEqual(path.read_text(), "{corrupt")

    def test_closed_c2_is_reopened_without_touching_other_slots(self):
        old = self.pages["C2"]
        old.closed = True
        before = {name: self.pages[name] for name in ("A", "B", "C1")}
        self.scan()
        self.assertIsNot(self.pages["C2"], old)
        self.assertEqual(self.pages["C2"].goto_urls, [self.saved])
        self.assertEqual(self.slots[3].runs, 5)
        for name, page in before.items():
            self.assertIs(self.pages[name], page)

    def test_english_crash_text_inside_composer_is_not_error(self):
        self.scan()
        self.assertEqual(len(self.context.created), 0)

    def test_chrome_error_page_needs_two_checks(self):
        self.pages["C1"].probe = {"url": "chrome-error://chromewebdata/",
                                   "title": "Aw, Snap!", "body": "", "composer": False}
        self.scan()
        self.assertEqual(len(self.context.created), 0)
        self.scan()
        self.assertEqual(len(self.context.created), 1)
        self.assertEqual(self.status.call_args.kwargs["tab_recovery_last_slot"], "C1")

    def test_other_lane_during_send_is_not_repaired(self):
        self.pages["A"].closed = True
        self.scan({"A"})
        self.assertEqual(len(self.context.created), 0)

    def test_renderer_crash_event_causes_isolated_repair(self):
        self.scan()
        self.pages["B"].handlers["crash"]()
        self.scan()
        self.assertEqual(len(self.context.created), 1)
        self.assertEqual(self.status.call_args.kwargs["tab_recovery_last_reason"], "renderer_crash")

    def test_recycle_is_due_at_two_hours_without_changing_worker_data(self):
        pages = dict(self.pages)
        checkpoint = Mock()
        with patch.object(maint, "CHROME_RECYCLE_ENABLED", True), \
             patch.object(maint, "CHROME_RECYCLE_INTERVAL_SECONDS", 7200), \
             patch.object(maint, "CHROME_RECYCLE_BUSY_GRACE_SECONDS", 1800):
            self.assertFalse(run(maint.request_periodic_recycle(
                pages, set(), 7199, AsyncMock(return_value=False), self.status, checkpoint)))
            self.assertTrue(run(maint.request_periodic_recycle(
                pages, set(), 7200, AsyncMock(return_value=False), self.status, checkpoint)))
        checkpoint.assert_called_once()
        self.assertEqual(json.loads(self.maint_recycle_path.read_text())["count"], 1)
        self.assertEqual([s.runs for s in self.slots], [5,5,5,5])

    def test_busy_recycle_defers_thirty_minutes(self):
        with patch.object(maint, "CHROME_RECYCLE_ENABLED", True), \
             patch.object(maint, "CHROME_RECYCLE_INTERVAL_SECONDS", 7200), \
             patch.object(maint, "CHROME_RECYCLE_BUSY_GRACE_SECONDS", 1800):
            self.assertFalse(run(maint.request_periodic_recycle(
                self.pages, {"A"}, 7200, AsyncMock(return_value=False),
                self.status, Mock())))
            checkpoint = Mock()
            self.assertTrue(run(maint.request_periodic_recycle(
                self.pages, {"A"}, 9000, AsyncMock(return_value=False),
                self.status, checkpoint)))
            checkpoint.assert_called_once()


if __name__ == "__main__":
    unittest.main()
