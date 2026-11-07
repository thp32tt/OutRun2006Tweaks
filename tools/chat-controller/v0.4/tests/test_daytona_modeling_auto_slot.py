"""Regression tests for Daytona Blender A independent of Model2 VR C."""
import ast
import asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = "".join((ROOT / "src-vr-v2" / f"controller.py.part{i:02d}").read_text()
              for i in range(4))
NODES = {n.name: n for n in ast.parse(SRC).body
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
KST = ZoneInfo("Asia/Seoul")
OUTRUN = "https://chatgpt.com/g/g-p-6ab9a64fc428819198c7f39765d764bf/project"
MODEL2 = "https://chatgpt.com/g/g-p-11111111111111111111111111111111/project"


class DaytonaBlenderALane(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 8, 9, 15, tzinfo=KST)
        self.sent = []
        self.rotations = 0
        self.busy = False
        self.reply = ""
        self.slot = SimpleNamespace(name="A", url=None, runs=0, last_sent_at=None,
                                    last_result=None, last_assistant_hash=None,
                                    last_assistant_change_at=None, watchdog_resumes_since_schedule=0)
        self.reg = SimpleNamespace(slots=[self.slot])
        self.q = {"car_model_simple": {"fresh_chat_required": True, "bootstrap_complete": False}}
        self.page = SimpleNamespace(url=OUTRUN)
        self.pages = {"A": self.page}
        async def yes(*args, **kw): return True
        async def no(*args, **kw): return False
        async def first_visible(page, selectors, **kw):
            return None if selectors == ["retry"] else object()
        async def get_page(*args): return self.page
        async def change_page(*args):
            self.page = SimpleNamespace(url=OUTRUN)
            self.pages["A"] = self.page
            self.slot.url = None
            return self.page
        async def hard_page(*args):
            self.rotations += 1
            return await change_page(*args)
        async def busy(*args): return self.busy
        async def get_reply(*args): return self.reply
        async def send(page, prompt, *, slot_name=None):
            self.assertEqual(slot_name, "A")
            self.assertTrue(page.url.startswith(OUTRUN))
            self.sent.append(prompt)
            return "sent"
        async def get_chat_url(page, **kw): return OUTRUN + "/c/test"
        self.env = {
            "CAR_MODEL_AUTODEV_ENABLED": True, "CAR_MODEL_SCOPE_READY": True,
            "AUTO_SEND": True, "CAR_MODEL_SCHEDULE_MINUTES": [15],
            "CAR_MODEL_CONTINUE_MIN_SECONDS": 1800,
            "CAR_MODEL_RESPONSE_STABLE_SECONDS": 30,
            "CAR_MODEL_HARD_NEW_CHAT_SECONDS": 3600,
            "CAR_MODEL_GITHUB_REPO": "thp32tt/OutRun2006Tweaks",
            "CAR_MODEL_TARGET_BRANCH": "feature/daytona365-blender-v8-20261108",
            "CONVERSION_ONLY_SLOT": "", "TZ": KST,
            "datetime": SimpleNamespace(now=lambda tz: self.now, fromisoformat=datetime.fromisoformat),
            "load_registry": lambda _: self.reg, "save_registry": lambda *_: None,
            "save_queue_state": lambda *_: None, "send_guard_reason": lambda *_: None,
            "slot_page": get_page, "replace_with_fresh_slot_page": change_page,
            "hard_replace_slot_page": hard_page,
            "detect_conversation_limit": no, "first_visible": first_visible,
            "detect_busy": busy, "ensure_logged_in": yes,
            "recover_slot_composer": lambda *a: change_page(*a),
            "detect_rate_limit": no, "detect_limit": no,
            "last_assistant_text": get_reply,
            "stable_hash": lambda x: hashlib.sha256(x.encode()).hexdigest(),
            "is_slot_project_url": lambda url, slot: slot == "A" and OUTRUN in (url or ""),
            "send_message": send, "wait_for_chat_url": get_chat_url,
            "note_successful_request": lambda *_: None,
            "mark_rate_limit": lambda *_: None, "write_runtime": lambda **_: None,
            "_parse_iso": lambda x: datetime.fromisoformat(x) if x else None,
            "INPUT_SELECTORS": ["textarea"], "RETRY_SELECTORS": ["retry"],
        }
        node = NODES["car_model_simple_cycle"]
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                     "<daytona-model-lane>", "exec"), self.env)

    def tick(self, h, m, s=0):
        self.now = datetime(2026, 11, 8, h, m, s, tzinfo=KST)
        return asyncio.run(self.env["car_model_simple_cycle"](object(), self.pages, self.q, self.now))

    def test_compose_wires_a_and_preserves_c(self):
        yml = (ROOT / "docker-compose.portainer-vr.yml").read_text()
        self.assertIn('CONVERSION_DX11_ENABLED: "false"', yml)
        self.assertIn('CAR_MODEL_AUTODEV_ENABLED: "true"', yml)
        self.assertIn('CAR_MODEL_SCHEDULE_MINUTES: "15"', yml)
        self.assertIn('MODEL2_AUTODEV_ENABLED: "true"', yml)
        self.assertIn('CONVERSION_DX9EX_ENABLED: "false"', yml)
        src = ast.unparse(NODES["conversion_parallel_cycle"])
        self.assertIn("await model2_simple_cycle", src)
        self.assertIn("await car_model_simple_cycle", src)
        self.assertIn('active_by_lane.pop(\'A\'', src)
        self.assertNotIn("await conversion_send_lane_task(context, pages, q, \"A\")", src)

    def test_first_modeling_send_then_hourly_hard_fresh_chat(self):
        self.assertTrue(self.tick(9, 15))
        self.assertIn("365 GTS/4", self.sent[0])
        self.assertIn("DAYTONA365_CAR_MODEL_AUTODEV_MASTER_PLAN.md", self.sent[0])
        self.assertFalse(self.tick(9, 45))
        self.busy = True
        self.assertFalse(self.tick(10, 14, 59))
        self.assertTrue(self.tick(10, 15))
        self.assertEqual(self.rotations, 1)
        self.assertIn("새 세션", self.sent[1])
        self.assertEqual(self.q["car_model_simple"]["last_send_reason"], "60m_hard_new_chat")
        self.assertEqual(len(self.sent), 2)

    def test_missing_or_wrong_project_blocks(self):
        self.env["CAR_MODEL_SCOPE_READY"] = False
        self.assertFalse(self.tick(9, 15))
        self.assertFalse(self.sent)
        self.env["CAR_MODEL_SCOPE_READY"] = True
        self.page.url = MODEL2
        self.q["car_model_simple"]["fresh_chat_required"] = False
        self.assertFalse(self.tick(9, 15))
        self.assertFalse(self.sent)


if __name__ == "__main__":
    unittest.main()
