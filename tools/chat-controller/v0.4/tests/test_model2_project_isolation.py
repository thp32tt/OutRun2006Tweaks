"""Model2 C must never send to OutRun project or resume old UW2 web tasks.

Standalone: python3 tools/chat-controller/v0.4/tests/test_model2_project_isolation.py
No browser credentials, private ROMs, HMD or GitHub API needed.
"""
from __future__ import annotations

import ast
import asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import hashlib
import re
import unittest
import urllib.parse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SRC = "".join((ROOT / "src-vr-v2" / f"controller.py.part{i:02d}").read_text()
              for i in range(4))
NODES = {n.name: n for n in ast.parse(SRC).body
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
KST = ZoneInfo("Asia/Seoul")
MODEL_ID = "g-p-1234567890abcdef1234567890abcdef"
OUTRUN_ID = "g-p-6ab9a64fc428819198c7f39765d764bf"
MODEL_HOME = f"https://chatgpt.com/g/{MODEL_ID}-model2-vr/project"
OUTRUN_HOME = f"https://chatgpt.com/g/{OUTRUN_ID}/project"
MODEL_CHAT = f"https://chatgpt.com/g/{MODEL_ID}-model2-vr/c/1234"
OUTRUN_CHAT = f"https://chatgpt.com/g/{OUTRUN_ID}-ausreon/c/5678"


def compile_fun(env, name):
    node = NODES[name]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 "<model2-isolation>", "exec"), env)


class Model2ProjectIsolation(unittest.TestCase):
    def test_distinct_project_ownership(self):
        env = {
            "CONTROLLER_MODE": "conversion", "MODEL2_AUTODEV_ENABLED": True,
            "MODEL2_SCOPE_READY": True, "MODEL2_PROJECT_URL": MODEL_HOME,
            "MODEL2_PROJECT_ID": MODEL_ID, "BASE_URL": OUTRUN_HOME,
            "REQUIRE_PROJECT_URL": True, "CONFIGURED_PROJECT_ID": OUTRUN_ID,
            "urllib": SimpleNamespace(parse=urllib.parse),
            "is_configured_project_url": lambda url: OUTRUN_ID in (url or ""),
            "is_persistable_chat_url": lambda url: bool(url and "/c/" in url),
            "Optional": __import__("typing").Optional,
        }
        for name in ("slot_project_home", "is_slot_project_url",
                     "is_project_scoped_chat_url"):
            compile_fun(env, name)
        self.assertEqual(env["slot_project_home"]("C"), MODEL_HOME)
        self.assertEqual(env["slot_project_home"]("A"), OUTRUN_HOME)
        self.assertTrue(env["is_project_scoped_chat_url"](MODEL_CHAT, "C"))
        self.assertFalse(env["is_project_scoped_chat_url"](OUTRUN_CHAT, "C"))
        self.assertFalse(env["is_project_scoped_chat_url"](MODEL_CHAT, "A"))
        self.assertTrue(env["is_project_scoped_chat_url"](OUTRUN_CHAT, "A"))
        env["MODEL2_SCOPE_READY"] = False
        self.assertEqual(env["slot_project_home"]("C"), "about:blank")
        self.assertFalse(env["is_project_scoped_chat_url"](MODEL_CHAT, "C"))

    def test_real_shared_send_guard_honors_explicit_model2_slot(self):
        # Regression for the live C 'wrong_project' error: source-level
        # model2_simple_cycle guard alone is insufficient if send_message()
        # subsequently hardcodes the configured OutRun project.
        env = {
            "CONTROLLER_MODE": "conversion",
            "MODEL2_AUTODEV_ENABLED": True,
            "MODEL2_PROJECT_ID": MODEL_ID,
            "CONFIGURED_PROJECT_ID": OUTRUN_ID,
            "REQUIRE_PROJECT_URL": True,
            "Optional": __import__("typing").Optional,
            "log": SimpleNamespace(error=lambda *args: None, exception=lambda *args: None),
            "write_runtime": lambda **kw: None,
            "is_slot_project_url": lambda url, slot_name=None: (
                (MODEL_ID if slot_name == "C" else OUTRUN_ID) in (url or "")
            ),
            "first_visible": lambda *a, **kw: None,
            "INPUT_SELECTORS": ["textarea"],
        }
        async def not_found(*args, **kw): return None
        env["first_visible"] = not_found
        compile_fun(env, "send_message")
        send = env["send_message"]
        self.assertEqual(asyncio.run(send(SimpleNamespace(url=MODEL_HOME),
                                          "test", slot_name="C")), "not_found")
        self.assertEqual(asyncio.run(send(SimpleNamespace(url=OUTRUN_HOME),
                                          "test", slot_name="C")), "wrong_project")
        self.assertEqual(asyncio.run(send(SimpleNamespace(url=OUTRUN_HOME),
                                          "test")), "not_found")
        self.assertEqual(asyncio.run(send(SimpleNamespace(url=MODEL_HOME),
                                          "test")), "wrong_project")
        self.assertEqual(asyncio.run(send(SimpleNamespace(url=MODEL_HOME),
                                          "test", slot_name="A")), "wrong_project")

    def test_config_switch_disables_webport_and_targets_real_model2(self):
        compose = (ROOT / "docker-compose.portainer-vr.yml").read_text()
        self.assertIn('UW2_WEB_PORT_ENABLED: "false"', compose)
        self.assertIn('MODEL2_AUTODEV_ENABLED: "true"', compose)
        self.assertIn('MODEL2_GITHUB_REPO: "thp32tt/Model2VR-tools"', compose)
        self.assertIn('MODEL2_TARGET_BRANCH: "main"', compose)
        self.assertIn('MODEL2_PROJECT_URL: "${MODEL2_PROJECT_URL:-}"', compose)
        self.assertIn('CONVERSION_DX11_ENABLED: "true"', compose)
        self.assertIn('DXVK_FROZEN: "true"', compose)
        self.assertIn("not MODEL2_AUTODEV_ENABLED", ast.unparse(NODES["vr_continuous_conversion_cycle"]))
        self.assertIn("await model2_simple_cycle", ast.unparse(NODES["conversion_parallel_cycle"]))
        self.assertIn("MODEL2_GITHUB_REPO", ast.unparse(NODES["queue_target_for_slot"]))

    def setUp(self):
        self.sent = []
        self.hard_rotations = 0
        self.busy = False
        self.reply = ""
        self.now = datetime(2026, 11, 4, 9, 0, tzinfo=KST)
        self.q = {"model2_simple": {"fresh_chat_required": True, "bootstrap_complete": False}}
        self.slot = SimpleNamespace(
            name="C", url=None, runs=0, last_sent_at=None, last_result=None,
            last_assistant_hash=None, last_assistant_change_at=None,
            watchdog_resumes_since_schedule=0,
        )
        self.reg = SimpleNamespace(slots=[self.slot])
        self.page = SimpleNamespace(url=MODEL_HOME)
        self.pages = {"C": self.page}
        self.env = {
            "MODEL2_AUTODEV_ENABLED": True, "MODEL2_SCOPE_READY": True,
            "AUTO_SEND": True, "MODEL2_SCHEDULE_MINUTES": [0, 30],
            "MODEL2_CONTINUE_MIN_SECONDS": 1800, "MODEL2_RESPONSE_STABLE_SECONDS": 30,
            "MODEL2_HARD_NEW_CHAT_SECONDS": 3600,
            "CONVERSION_ONLY_SLOT": "", "datetime": SimpleNamespace(
                now=lambda tz: self.now, fromisoformat=datetime.fromisoformat),
            "TZ": KST, "load_registry": lambda now: self.reg,
            "save_registry": lambda x: None, "save_queue_state": lambda x: None,
            "send_guard_reason": lambda *args: None, "slot_page": self.get_page,
            "replace_with_fresh_slot_page": self.replace_page,
            "hard_replace_slot_page": self.hard_replace_page,
            "detect_conversation_limit": self.no, "first_visible": self.visible,
            "detect_busy": self.is_busy, "ensure_logged_in": self.yes,
            "recover_slot_composer": self.recover, "detect_rate_limit": self.no,
            "detect_limit": self.no, "last_assistant_text": self.get_reply,
            "stable_hash": lambda x: hashlib.sha256(x.encode()).hexdigest(),
            "is_slot_project_url": lambda url, slot_name: (url or "").startswith(
                f"https://chatgpt.com/g/{MODEL_ID}"),
            "send_message": self.send, "wait_for_chat_url": self.chat_url,
            "note_successful_request": lambda *args: None,
            "mark_rate_limit": lambda *args: None,
            "write_runtime": lambda **kw: None,
            "_parse_iso": lambda value: datetime.fromisoformat(value) if value else None,
            "INPUT_SELECTORS": ["textarea"], "RETRY_SELECTORS": ["retry"],
        }
        compile_fun(self.env, "model2_simple_cycle")

    async def yes(self, *args, **kw): return True
    async def no(self, *args, **kw): return False
    async def get_page(self, *args): return self.page
    async def replace_page(self, *args):
        self.page = SimpleNamespace(url=MODEL_HOME)
        self.pages["C"] = self.page
        self.slot.url = None
        return self.page
    async def hard_replace_page(self, *args):
        self.hard_rotations += 1
        return await self.replace_page(*args)
    async def visible(self, page, selectors, **kw):
        return None if selectors == ["retry"] else object()
    async def is_busy(self, *args): return self.busy
    async def recover(self, *args): return self.page
    async def get_reply(self, *args): return self.reply
    async def send(self, page, message, *, slot_name=None):
        self.assertEqual(slot_name, "C")
        self.sent.append(message)
        return "sent"
    async def chat_url(self, page, **kwargs): return MODEL_CHAT

    def tick(self, hour, minute, second=0):
        self.now = datetime(2026, 11, 4, hour, minute, second, tzinfo=KST)
        return asyncio.run(self.env["model2_simple_cycle"](
            object(), self.pages, self.q, self.now))

    def test_missing_project_url_blocks_every_send(self):
        self.env["MODEL2_SCOPE_READY"] = False
        self.assertFalse(self.tick(9, 0))
        self.assertEqual(self.sent, [])
        self.assertTrue(self.q["model2_simple"]["fresh_chat_required"])

    def test_first_bootstrap_then_30_minute_short_followup(self):
        self.assertTrue(self.tick(9, 0))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("Model2VR-tools@main", self.sent[0])
        self.assertIn("MODEL2_VR_AUTODEV_MASTER_PLAN.md", self.sent[0])
        self.assertNotIn("웹포팅 개발 계속진행해", self.sent[0])
        self.assertFalse(self.tick(9, 4))
        self.assertFalse(self.tick(9, 29, 59))
        self.assertTrue(self.tick(9, 30))
        self.assertEqual(self.sent[1], "모델2 VR 개발 계속진행해")
        self.assertEqual(self.slot.url, MODEL_CHAT)

    def test_busy_worker_not_interrupted_and_coldown_kept(self):
        self.assertTrue(self.tick(9, 0))
        self.busy = True
        self.assertFalse(self.tick(9, 30))
        self.assertEqual(len(self.sent), 1)
        self.busy = False
        self.assertTrue(self.tick(9, 31))
        self.assertEqual(self.sent[-1], "모델2 VR 개발 계속진행해")

    def test_one_hour_frozen_busy_forces_new_model2_chat_and_task(self):
        self.assertTrue(self.tick(9, 0))
        self.assertFalse(self.tick(9, 59, 59))
        self.busy = True
        self.assertTrue(self.tick(10, 0))
        self.assertEqual(self.hard_rotations, 1)
        self.assertEqual(len(self.sent), 2)
        self.assertIn("Model2VR-tools@main", self.sent[-1])
        self.assertIn("새 세션", self.sent[-1])
        self.assertEqual(self.q["model2_simple"]["hard_rotation_sent_total"], 1)
        self.assertEqual(self.q["model2_simple"]["last_send_reason"], "60m_hard_new_chat")
        self.assertEqual(self.slot.last_result, "model2_60m_new_chat_sent")
        self.assertFalse(self.tick(10, 0, 15))
        self.assertEqual(self.hard_rotations, 1)

    def test_hard_new_chat_send_retry_keeps_only_one_new_tab(self):
        self.assertTrue(self.tick(9, 0))
        original_send = self.env["send_message"]
        async def fail_one(page, message, *, slot_name=None):
            self.env["send_message"] = original_send
            return "send_failed"
        self.env["send_message"] = fail_one
        self.assertFalse(self.tick(10, 0))
        self.assertEqual(self.hard_rotations, 1)
        self.assertTrue(self.q["model2_simple"]["hard_rotation_pending"])
        self.assertTrue(self.tick(10, 0, 15))
        self.assertEqual(self.hard_rotations, 1)
        self.assertEqual(self.q["model2_simple"]["hard_rotation_sent_total"], 1)

    def test_wrong_project_url_never_sends(self):
        self.page.url = OUTRUN_CHAT
        self.q["model2_simple"]["fresh_chat_required"] = False
        self.assertFalse(self.tick(9, 0))
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
