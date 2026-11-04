"""Hard 60-minute recovery regressions: independent DX11 and Model2 slots.

Standalone (no ChatGPT login, browser, hardware or repo clone):
python3 tools/chat-controller/v0.4/tests/test_hourly_hard_recovery.py
"""
import ast
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "".join((ROOT / "src-vr-v2" / f"controller.py.part{i:02d}").read_text() for i in range(4))
NODES = {n.name: n for n in ast.parse(SOURCE).body
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
TZ = ZoneInfo("Asia/Seoul")


def load_one(env, name):
    node = NODES[name]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 "<hourly-recovery>", "exec"), env)


class HourlyDX11Recovery(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 4, 11, 0, tzinfo=TZ)
        self.sent = []
        self.snapshots = []
        self.saved = 0
        self.active = {
            "task_id": "CONVERSION-DX11-01218", "slot": "A", "lane": "DX11",
            "phase": "WAIT_CHAT", "sent_at": (self.now - timedelta(hours=1)).isoformat()
        }
        self.q = {"active_by_lane": {"A": self.active}}
        self.env = {
            "CONTROLLER_MODE": "conversion", "BrowserContext": object, "Page": object,
            "VR_UNCONDITIONAL_RESUME_SECONDS": 3600,
            "VR_FORCE_ROLLOVER_SECONDS": 3600,
            "VR_CHECKPOINT_ENABLED": True,
            "datetime": SimpleNamespace(now=lambda tz: self.now),
            "_parse_iso": lambda s: datetime.fromisoformat(s) if s else None,
            "TZ": TZ, "save_queue_state": self.save, "write_runtime": lambda **kw: None,
            "vr_persist_checkpoint": self.persist,
            "queue_rollover_chat": self.rollover,
            "vr_checkpoint_path": lambda *args: "noop",
        }
        for fn in ("vr_forced_rollover_due", "vr_unconditional_resume_due",
                   "vr_checkpoint_and_rollover"):
            load_one(self.env, fn)

    def save(self, q):
        self.saved += 1
        self.snapshots.append(dict(q["active_by_lane"]["A"]))

    async def persist(self, q, task, now, purpose):
        self.snapshots.append({"checkpoint": purpose})
        return True

    async def rollover(self, context, pages, task, reason):
        self.sent.append((task["task_id"], reason))
        return True

    def tick(self):
        return asyncio.run(self.env["vr_checkpoint_and_rollover"](
            object(), {}, self.q, self.active, self.now))

    def test_60m_forced_without_schedule_even_when_owner_unconfirmed(self):
        self.now = datetime(2026, 11, 4, 11, 0, tzinfo=TZ)
        self.assertTrue(self.tick())
        self.assertEqual(self.sent, [("CONVERSION-DX11-01218", "VR_FORCED_60_MINUTE_NEW_CHAT")])
        self.assertIn({"checkpoint": "pre_rollover"}, self.snapshots)

    def test_59m_does_not_force(self):
        self.active["sent_at"] = (self.now - timedelta(minutes=59, seconds=59)).isoformat()
        self.assertFalse(self.tick())
        self.assertEqual(self.sent, [])

    def test_60m_no_remote_checkpoint_still_saves_local_and_recovers(self):
        async def failed(*args): return False
        self.env["vr_persist_checkpoint"] = failed
        self.assertTrue(self.tick())
        self.assertEqual(self.sent[0][1], "VR_FORCED_60_MINUTE_NEW_CHAT")
        self.assertEqual(self.active["vr_checkpoint_fallback"], "LOCAL_ONLY_AFTER_60M")
        self.assertGreaterEqual(self.saved, 1)

    def test_wait_actions_not_falsely_reissued_as_new_task(self):
        self.active["phase"] = "WAIT_ACTIONS"
        self.assertFalse(self.tick())
        self.assertEqual(self.sent, [])

    def test_hard_recovery_checked_before_frozen_dx11_ui_probe(self):
        code = ast.unparse(NODES["vr_continuous_conversion_cycle"])
        self.assertLess(code.index("vr_unconditional_resume_due(active, now)"),
                        code.index("await conversion_process_lane(context, pages, q, lane_key)"))

    def test_hard_replace_abandons_failed_tab_close(self):
        class DeadPage:
            url = "https://chatgpt.com/g/g-p-old/c/old"
            def is_closed(self): return False
            async def close(self, **kwargs): raise TimeoutError("hung renderer")
        class NewPage:
            url = "about:blank"
            async def goto(self, url, **kwargs):
                self.url = url
            async def wait_for_timeout(self, ms): return None
        class Context:
            async def new_page(self): return NewPage()
        env = {
            "BrowserContext": object, "Page": object, "Slot": object, "asyncio": asyncio,
            "slot_project_home": lambda name: "https://chatgpt.com/g/g-p-new-model2/project",
            "log": SimpleNamespace(warning=lambda *args: None)
        }
        load_one(env, "hard_replace_slot_page")
        slot = SimpleNamespace(name="C", url="old", last_assistant_hash="old",
                               last_assistant_change_at="old", last_watchdog_at="old",
                               watchdog_resumes_since_schedule=4)
        pages = {"C": DeadPage()}
        new_page = asyncio.run(env["hard_replace_slot_page"](Context(), pages, slot))
        self.assertIs(pages["C"], new_page)
        self.assertEqual(new_page.url, "https://chatgpt.com/g/g-p-new-model2/project")
        self.assertIsNone(slot.url)
        self.assertEqual(slot.watchdog_resumes_since_schedule, 0)

    def test_force_owner_wait_gate_only_before_hard_deadline(self):
        load_one(self.env, "vr_rollover_must_wait_for_owner")
        check = self.env["vr_rollover_must_wait_for_owner"]
        self.assertFalse(check(True, True))
        self.assertTrue(check(True, False))


if __name__ == "__main__":
    unittest.main()
