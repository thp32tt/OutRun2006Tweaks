"""Regression checks for the production v2 localization Chrome-tab watchdog.

No Chrome, Docker, N100, token or network is required.
"""
from __future__ import annotations

import ast
import asyncio
import re
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "tools/chat-controller/v0.4/src"


def load_health_functions():
    source = "".join(p.read_text(encoding="utf-8") for p in sorted(PARTS.glob("controller.py.part*")))
    compile(source, "<assembled-controller>", "exec")
    names = {
        "_is_chrome_error_document", "_watch_slot_page_health",
        "monitor_slot_tab_health", "periodic_slot_tab_health",
    }
    nodes = [n for n in ast.parse(source).body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert len(nodes) == len(names), "production controller is missing health helpers"
    environment = {
        "asyncio": asyncio, "re": re, "time": time, "datetime": datetime,
        "TZ": timezone.utc, "log": Mock(), "Path": Path,
        "CONTROLLER_MODE": "localization",
        "TAB_HEALTH_CHECK_SECONDS": 30,
        "TAB_HEALTH_PROBE_TIMEOUT_SECONDS": 1,
        "TAB_HEALTH_FAILURE_THRESHOLD": 3,
        "TAB_ERROR_FAILURE_THRESHOLD": 2,
        "TAB_RECOVERY_COOLDOWN_SECONDS": 60,
        "BASE_URL": "https://chatgpt.com/g/g-p-test",
        "is_project_scoped_chat_url": lambda url: "/g/g-p-" in url,
        "runtime": {}, "write_runtime": Mock(),
    }
    mod = ast.Module(
        body=[ast.ImportFrom(module="__future__",
                             names=[ast.alias(name="annotations")], level=0)] + nodes,
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(mod), "<health-functions>", "exec"), environment)
    return environment


class FakePage:
    def __init__(self, url="https://chatgpt.com/g/g-p-test", probe=None, closed=False):
        self.url = url
        self.probe = probe or {"url": url, "title": "ChatGPT",
                               "body": "Ready", "composer": True}
        self.closed = closed
        self.events = {}
        self.goto_calls = []
        self.close_calls = 0

    def on(self, event, callback):
        self.events[event] = callback

    def is_closed(self):
        return self.closed

    async def evaluate(self, code):
        return self.probe

    async def screenshot(self, **kwargs):
        return b""

    async def close(self, **kwargs):
        self.closed = True
        self.close_calls += 1

    async def goto(self, url, **kwargs):
        self.goto_calls.append(url)
        self.url = url


class FakeContext:
    def __init__(self):
        self.browser = SimpleNamespace(is_connected=lambda: True)
        self.created = []

    async def new_page(self):
        page = FakePage()
        self.created.append(page)
        return page


class LocalizationTabRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.env = load_health_functions()
        self.context = FakeContext()
        self.saved_url = "https://chatgpt.com/g/g-p-test/c/existing"
        self.slot = SimpleNamespace(name="A", url=self.saved_url,
                                    runs=7, last_result="WAIT_CHAT")
        self.env["load_registry"] = lambda now: SimpleNamespace(slots=[self.slot])
        self.state = {}

    def monitor(self, pages):
        return asyncio.run(self.env["monitor_slot_tab_health"](
            self.context, pages, self.state))

    def test_closed_tab_reopens_saved_conversation_without_duplicate_send(self):
        old = FakePage(self.saved_url, closed=True)
        pages = {"A": old}
        self.monitor(pages)
        self.assertEqual(len(self.context.created), 1)
        self.assertEqual(pages["A"].goto_calls, [self.saved_url])
        self.assertEqual(self.slot.runs, 7)
        self.assertEqual(self.slot.url, self.saved_url)
        self.assertEqual(self.slot.last_result, "WAIT_CHAT")
        self.assertEqual(self.env["runtime"], {})
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["tab_recovery_last_reason"], "closed")

    def test_missing_tab_is_recreated(self):
        pages = {}
        self.monitor(pages)
        self.assertEqual(pages["A"].goto_calls, [self.saved_url])
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["tab_recovery_last_reason"], "missing")

    def test_chrome_error_page_reopens_after_two_checks(self):
        old = FakePage(self.saved_url, probe={
            "url": "chrome-error://chromewebdata/", "title": "Aw, Snap!",
            "body": "RESULT_CODE_KILLED_BAD_MESSAGE", "composer": False,
        })
        pages = {"A": old}
        self.monitor(pages)
        self.assertIs(pages["A"], old)
        self.monitor(pages)
        self.assertIsNot(pages["A"], old)
        self.assertEqual(old.close_calls, 1)
        self.assertEqual(pages["A"].goto_calls, [self.saved_url])
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["tab_recovery_last_reason"], "chrome_error_page")

    def test_chat_message_mentioning_crash_is_not_browser_crash(self):
        body = "The reply explains: Aw, Snap! RESULT_CODE_KILLED"
        probe = {"url": self.saved_url, "title": "ChatGPT",
                 "body": body, "composer": True}
        self.assertFalse(self.env["_is_chrome_error_document"](probe))
        pages = {"A": FakePage(self.saved_url, probe)}
        self.monitor(pages)
        self.monitor(pages)
        self.assertFalse(self.context.created)
        self.env["write_runtime"].assert_not_called()

    def test_renderer_crash_event_is_recovered(self):
        old = FakePage(self.saved_url)
        pages = {"A": old}
        self.monitor(pages)
        old.events["crash"]()
        self.monitor(pages)
        self.assertEqual(pages["A"].goto_calls, [self.saved_url])
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["tab_recovery_last_reason"], "renderer_crash")

    def test_four_worker_c2_crash_is_isolated(self):
        slots = [
            SimpleNamespace(name=name, url=f"https://chatgpt.com/g/g-p-test/c/{name.lower()}",
                            runs=3, last_result="WAIT_CHAT")
            for name in ("A", "B", "C1", "C2")
        ]
        self.env["load_registry"] = lambda now: SimpleNamespace(slots=slots)
        pages = {slot.name: FakePage(slot.url) for slot in slots}
        untouched = {name: pages[name] for name in ("A", "B", "C1")}
        self.monitor(pages)
        pages["C2"].events["crash"]()
        self.monitor(pages)
        self.assertEqual(set(pages), {"A", "B", "C1", "C2"})
        self.assertEqual(len(self.context.created), 1)
        self.assertEqual(pages["C2"].goto_calls, [slots[3].url])
        for name, page in untouched.items():
            self.assertIs(pages[name], page)
        self.assertEqual([slot.runs for slot in slots], [3, 3, 3, 3])
        self.assertEqual(self.env["write_runtime"].call_args.kwargs["tab_recovery_last_slot"], "C2")

    def test_other_slots_not_changed(self):
        slot_b = SimpleNamespace(name="B", url="https://chatgpt.com/g/g-p-test/c/b",
                                 runs=9)
        self.env["load_registry"] = lambda now: SimpleNamespace(slots=[self.slot, slot_b])
        page_b = FakePage(slot_b.url)
        pages = {"A": FakePage(self.saved_url, closed=True), "B": page_b}
        self.monitor(pages)
        self.assertIs(pages["B"], page_b)
        self.assertEqual(slot_b.runs, 9)


if __name__ == "__main__":
    unittest.main()
