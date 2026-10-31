"""C-slot UW2 must send exactly one sentence; no TASK_ID or terminal gates.

Run: python3 tools/chat-controller/v0.4/tests/test_uw2_simple_loop.py
No network, ChatGPT login, N100 deployment, or original-game assets required.
"""
from __future__ import annotations

import ast
import asyncio
import datetime
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SRC = "".join((ROOT / "src-vr-v2" / f"controller.py.part{i:02d}").read_text()
              for i in range(4))
TREE = ast.parse(SRC)
FUNCS = {n.name: n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
KST = ZoneInfo("Asia/Seoul")
PROMPT = "웹포팅 개발 계속진행해"


class Uw2SimpleLoopTest(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.new_pages = 0
        self.busy = False
        self.answer = ""
        self.slot = SimpleNamespace(
            name="C", url="https://chatgpt.com/g/g-p-example/c/existing",
            runs=0, last_sent_at=None, last_result=None,
            last_assistant_hash=None, last_assistant_change_at=None,
            watchdog_resumes_since_schedule=0)
        self.reg = SimpleNamespace(slots=[self.slot])
        self.q = {"active_by_lane": {"A": {"task_id": "UNCHANGED_DX11"}}}
        self.ctx = object()
        self.page = SimpleNamespace(url=self.slot.url)
        self.pages = {"C": self.page}
        self.ns = {
            "datetime": datetime.datetime, "TZ": KST,
            "UW2_WEB_PORT_ENABLED": True, "UW2_SCHEDULE_MINUTES": [0, 30],
            "UW2_CONTINUE_MIN_SECONDS": 120, "UW2_RESPONSE_STABLE_SECONDS": 20,
            "_parse_iso": lambda x: datetime.datetime.fromisoformat(x) if x else None,
            "last_assistant_text": self.last_answer,
            "stable_hash": lambda x: hashlib.sha256(x.encode()).hexdigest(),
            "CONVERSION_ONLY_SLOT": "",
            "load_registry": lambda now: self.reg,
            "save_registry": lambda reg: None,
            "save_queue_state": lambda q: None,
            "send_guard_reason": lambda reg, slot, now: None,
            "slot_page": self.slot_page,
            "replace_with_fresh_slot_page": self.new_page,
            "detect_busy": self.detect_busy,
            "detect_conversation_limit": self.false,
            "first_visible": self.visible,
            "ensure_logged_in": self.true,
            "detect_rate_limit": self.false,
            "detect_limit": self.false,
            "send_message": self.send_message,
            "wait_for_chat_url": self.get_url,
            "recover_slot_composer": self.restore_page,
            "note_successful_request": lambda *a: None,
            "mark_rate_limit": lambda *a: None,
            "write_runtime": lambda **kw: None,
            "INPUT_SELECTORS": ["textarea"],
            "RETRY_SELECTORS": ["retry"],
        }
        node = FUNCS["uw2_simple_cycle"]
        module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
        exec(compile(module, "<uw2>", "exec"), self.ns)

    async def true(self, *args, **kw):
        return True

    async def false(self, *args, **kw):
        return False

    async def visible(self, page, selectors, **kw):
        return None if selectors == ["retry"] else object()

    async def slot_page(self, context, pages, slot):
        return self.page

    async def new_page(self, context, pages, slot):
        self.new_pages += 1
        self.slot.url = None
        self.page = SimpleNamespace(url="https://chatgpt.com/g/g-p-example")
        pages["C"] = self.page
        return self.page

    async def detect_busy(self, page):
        return self.busy

    async def last_answer(self, page):
        return self.answer

    async def send_message(self, page, message):
        self.sent.append(message)
        return "sent"

    async def get_url(self, page, timeout_sec=8):
        return "https://chatgpt.com/g/g-p-example/c/new"

    async def restore_page(self, context, pages, slot, page):
        return page

    def tick(self, hour, minute, second=0):
        # The isolated function calls datetime.now(TZ) after sending; keep it
        # aligned with synthetic scheduler time rather than wall-clock time.
        at = datetime.datetime(2026, 10, 31, hour, minute, second, tzinfo=KST)
        self.ns["datetime"] = SimpleNamespace(now=lambda tz: at, fromisoformat=datetime.datetime.fromisoformat)
        return asyncio.run(self.ns["uw2_simple_cycle"](
            self.ctx, self.pages, self.q, at))

    def test_one_sentence_and_dedup_same_chat(self):
        self.assertTrue(self.tick(9, 0))
        self.assertEqual(self.sent, [PROMPT])
        self.assertFalse(self.tick(9, 0, 45))
        self.assertTrue(self.tick(9, 30))
        self.assertEqual(self.sent, [PROMPT, PROMPT])
        self.assertEqual(self.new_pages, 0)
        self.assertNotIn("C", self.q["active_by_lane"])
        self.assertNotIn("production_id", str(self.q["uw2_simple"]).lower())
        self.assertNotIn("task_id", str(self.q["uw2_simple"]).lower())

    def test_busy_is_never_interrupted_and_pending_resumes(self):
        self.busy = True
        self.assertFalse(self.tick(9, 0))
        self.assertEqual(self.sent, [])
        self.busy = False
        self.assertTrue(self.tick(9, 4))
        self.assertEqual(self.sent, [PROMPT])
        self.assertFalse(self.tick(9, 5))
        self.assertEqual(self.new_pages, 0)

    def test_no_backlog_of_missed_half_hours(self):
        self.busy = True
        self.assertFalse(self.tick(9, 0))
        self.assertFalse(self.tick(9, 30))
        self.busy = False
        self.assertTrue(self.tick(9, 31))
        self.assertEqual(self.sent, [PROMPT])
        self.assertEqual(self.q["uw2_simple"]["last_sent_window"],
                         "2026-10-31T09:30:00+09:00")

    def test_migration_fresh_chat_once_then_reuse(self):
        self.q["uw2_simple"] = {"fresh_chat_required": True}
        self.assertTrue(self.tick(9, 0))
        self.assertEqual(self.new_pages, 1)
        self.assertTrue(self.tick(9, 30))
        self.assertEqual(self.new_pages, 1)
        self.assertEqual(self.sent, [PROMPT, PROMPT])

    def test_auto_resumes_after_completed_stable_response(self):
        self.assertTrue(self.tick(9, 0))
        self.answer = "One new source feature committed and tests passed."
        self.assertFalse(self.tick(9, 2, 10))  # first observed, still stabilizing
        self.assertTrue(self.tick(9, 2, 35))   # response finished, next work starts
        self.assertEqual(self.sent, [PROMPT, PROMPT])
        self.assertEqual(self.q["uw2_simple"]["last_send_reason"], "response_complete")
        self.assertFalse(self.tick(9, 4, 50))  # identical old answer is not new work
        self.assertEqual(self.new_pages, 0)

    def test_does_not_follow_up_while_busy_even_if_reply_text_exists(self):
        self.assertTrue(self.tick(9, 0))
        self.answer = "Finished part of game logic"
        self.busy = True
        self.assertFalse(self.tick(9, 3))
        self.busy = False
        self.assertFalse(self.tick(9, 4))
        self.assertTrue(self.tick(9, 4, 25))
        self.assertEqual(self.sent, [PROMPT, PROMPT])

    def test_response_must_stabilize_and_message_stays_exact(self):
        self.assertTrue(self.tick(9, 0))
        self.answer = "partially generated"
        self.assertFalse(self.tick(9, 2, 10))
        self.answer = "full response with actual GitHub result"
        self.assertFalse(self.tick(9, 2, 25))   # different fingerprint resets
        self.assertTrue(self.tick(9, 2, 50))
        self.assertEqual(self.sent, [PROMPT, PROMPT])

    def test_without_any_assistant_reply_only_scheduled_fallback(self):
        self.assertTrue(self.tick(9, 0))
        self.assertFalse(self.tick(9, 4))
        self.assertFalse(self.tick(9, 20))
        self.assertTrue(self.tick(9, 30))
        self.assertEqual(self.q["uw2_simple"]["last_send_reason"], "schedule_fallback")

    def test_scheduled_fallback_never_interrupts_changing_reply(self):
        self.assertTrue(self.tick(9, 0))
        self.answer = "working on web port"
        self.assertFalse(self.tick(9, 29, 40))
        self.answer = "new changed output still being finalized"
        self.assertFalse(self.tick(9, 30))
        self.assertTrue(self.tick(9, 30, 25))
        self.assertEqual(self.sent, [PROMPT, PROMPT])

    def test_cooldown_delays_half_hour_boundary_after_fast_reply(self):
        self.assertTrue(self.tick(9, 0))
        self.answer = "passed"
        self.assertFalse(self.tick(9, 28, 45))
        self.assertTrue(self.tick(9, 29, 10))
        self.assertFalse(self.tick(9, 30))  # 50s since send, do not spam
        self.assertTrue(self.tick(9, 31, 30))
        self.assertEqual(self.sent, [PROMPT, PROMPT, PROMPT])

    def test_production_cooldown_is_30_minutes_not_2_minutes(self):
        self.ns["UW2_CONTINUE_MIN_SECONDS"] = 1800
        self.assertTrue(self.tick(9, 0))
        self.answer = "Implemented a complete integration batch."
        self.assertFalse(self.tick(9, 4))
        self.assertFalse(self.tick(9, 10))
        self.assertFalse(self.tick(9, 20))
        self.assertFalse(self.tick(9, 29, 59))
        self.assertEqual(self.sent, [PROMPT])
        self.assertTrue(self.tick(9, 30))
        self.assertEqual(self.sent, [PROMPT, PROMPT])
        self.assertEqual(self.q["uw2_simple"]["last_send_reason"], "schedule_fallback")

    def test_30_minute_boundary_cannot_interrupt_busy_development(self):
        self.ns["UW2_CONTINUE_MIN_SECONDS"] = 1800
        self.assertTrue(self.tick(9, 0))
        self.busy = True
        self.assertFalse(self.tick(9, 30))
        self.assertEqual(self.sent, [PROMPT])
        self.busy = False
        self.answer = "Long-running work completed"
        self.assertFalse(self.tick(9, 32))
        self.assertTrue(self.tick(9, 32, 30))
        self.assertEqual(self.sent, [PROMPT, PROMPT])
        self.assertEqual(self.new_pages, 0)

    def test_live_configuration_enforces_low_input_floor(self):
        source = (ROOT / "src-vr-v2" / "controller.py.part00").read_text()
        self.assertIn('UW2_CONTINUE_MIN_SECONDS = max(1800,', source)
        self.assertIn('os.getenv("UW2_CONTINUE_MIN_SECONDS", "1800")', source)

    def test_prompt_router_early_return_has_no_extra_text(self):
        node = FUNCS["prompt_for_slot"]
        module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
        env = {"CONTROLLER_MODE": "conversion", "UW2_WEB_PORT_ENABLED": True}
        exec(compile(module, "<prompt>", "exec"), env)
        self.assertEqual(env["prompt_for_slot"](SimpleNamespace(name="C"), "parallel"), PROMPT)
        self.assertEqual(env["prompt_for_slot"](SimpleNamespace(name="C"), "watchdog"), PROMPT)

    def test_one_time_migration_clears_old_uw2_ids_not_dx11(self):
        previous_c = {"lane": "UW2", "task_id": "CONVERSION-UW2-01609"}
        old_a = {"lane": "DX11", "task_id": "CONVERSION-DX11-01184"}
        completed = [previous_c, old_a]
        q = {"active_by_lane": {"A": old_a, "C": previous_c},
             "completed": completed, "blocked": [previous_c],
             "vr_scheduled_dispatch_windows": {"A": "old_a", "C": "old_c"},
             "vr_continuous_last_dispatch_at": {"A": "old_a", "C": "old_c"}}
        cycle = FUNCS["conversion_parallel_cycle"]
        section = next(node for node in ast.walk(cycle)
                       if isinstance(node, ast.If)
                       and "uw2_simple_initialized" in ast.unparse(node.test))
        reg = SimpleNamespace(slots=[self.slot])
        env = {"UW2_WEB_PORT_ENABLED": True,
               "q": q, "active_by_lane": q["active_by_lane"],
               "now": datetime.datetime(2026, 10, 31, 9, 0, tzinfo=KST),
               "load_registry": lambda now: reg,
               "save_registry": lambda reg: None,
               "save_queue_state": lambda q: None}
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=[section], type_ignores=[])), "<uw2-migrate>", "exec"), env)
        self.assertNotIn("C", q["active_by_lane"])
        self.assertEqual(q["active_by_lane"]["A"], old_a)
        self.assertEqual(q["completed"], [old_a])
        self.assertEqual(q["blocked"], [])
        self.assertEqual(q["vr_scheduled_dispatch_windows"], {"A": "old_a"})
        self.assertTrue(q["uw2_simple"]["fresh_chat_required"])
        self.assertTrue(q["uw2_simple_initialized"])

    def test_old_id_dispatch_excluded_when_uw2_is_on(self):
        src = ast.get_source_segment(SRC, FUNCS["vr_continuous_conversion_cycle"])
        self.assertIn('("C", CONVERSION_DX9EX_ENABLED and not UW2_WEB_PORT_ENABLED)', src)
        self.assertIn('if UW2_WEB_PORT_ENABLED and slot_name == "C":', SRC)
        self.assertNotIn("allocate_lane_production_id", ast.get_source_segment(SRC, FUNCS["uw2_simple_cycle"]))
        self.assertNotIn("queue_rollover_chat", ast.get_source_segment(SRC, FUNCS["uw2_simple_cycle"]))
        self.assertNotIn("github_find_task_commit", ast.get_source_segment(SRC, FUNCS["uw2_simple_cycle"]))


if __name__ == "__main__":
    unittest.main()
