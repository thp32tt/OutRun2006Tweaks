"""Pure admission/dispatch regressions for external Ferrari16 automation."""
import base64
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

_SOURCE = Path(__file__).resolve().parents[1] / "ferrari_external.py"
_spec = importlib.util.spec_from_file_location("ferrari_external_under_test", _SOURCE)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

REPO = "thp32tt/OutRun2006Tweaks"
BRANCH = "automation/ferrari16-external-20261123"


def fixture():
    return {
        "schema_version": 1,
        "repository": REPO,
        "target_branch": BRANCH,
        "one_owner_slot": "A",
        "cadence_kst_minutes": [0, 30],
        "active_work_id": "EXT16-001",
        "work": [{"id": "EXT16-001", "stage": "source_fix", "status": "ACTIVE",
                  "title": "both-eye stereo", "acceptance": ["left+right exact-SHA"]}],
    }


class ExternalModelQueueTests(unittest.TestCase):
    def test_active_model_is_selected(self):
        self.assertEqual(_module.choose_external_work(fixture(), REPO, BRANCH)["id"], "EXT16-001")

    def test_old_cockpit_repo_rejected(self):
        with self.assertRaises(ValueError):
            _module.choose_external_work(fixture(), "thp32tt/imsi1", "main")

    def test_wrong_branch_rejected(self):
        with self.assertRaises(ValueError):
            _module.choose_external_work(fixture(), REPO, "vr-d3d9ex-focus")

    def test_duplicate_work_id_rejected(self):
        queue = fixture()
        queue["work"].append(dict(queue["work"][0]))
        with self.assertRaises(ValueError):
            _module.choose_external_work(queue, REPO, BRANCH)

    def test_no_completed_work_dispatch(self):
        queue = fixture()
        queue["work"][0]["status"] = "COMPLETE_STATIC"
        self.assertIsNone(_module.choose_external_work(queue, REPO, BRANCH))

    def test_no_quest_hmd_auto_pass(self):
        queue = fixture()
        queue["work"][0]["requires_user_headset"] = True
        self.assertIsNone(_module.choose_external_work(queue, REPO, BRANCH))

    def test_no_cross_project_car_owner(self):
        queue = fixture()
        queue["one_owner_slot"] = "C"
        with self.assertRaises(ValueError):
            _module.choose_external_work(queue, REPO, BRANCH)

    def test_prompt_keeps_same_id_and_hardware_untested(self):
        queue = fixture()
        work = _module.choose_external_work(queue, REPO, BRANCH)
        text = _module.make_external_prompt(work, queue, "f" * 40, True)
        self.assertIn("TASK_ID=EXT16-001", text)
        self.assertIn("CONTINUATION=1", text)
        self.assertIn("RUNTIME_VALIDATION=UNTESTED", text)
        self.assertIn("left+right exact-SHA", text)


class ExternalModelCycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_half_hour_idempotence_and_no_progress_hold(self):
        q = {"ferrari_external_initialized": True,
             "ferrari_external_simple_A": {"new_chat_required": True}}
        repo = REPO
        branch = BRANCH
        queue = fixture()
        head = "a" * 40
        zone = timezone(timedelta(hours=9))
        page = SimpleNamespace(url="https://chatgpt.com/g/g-p-6ab9a64fc428819198c7f39765d764bf/project")
        slot = SimpleNamespace(name="A", url=None, runs=0, last_sent_at=None,
            last_result=None, last_assistant_hash=None, last_assistant_change_at=None,
            watchdog_resumes_since_schedule=0)
        reg = SimpleNamespace(slots=[slot])
        sends = AsyncMock(return_value="sent")

        def api(path):
            if "/contents/" in path:
                return {"encoding": "base64", "content":
                    base64.b64encode(json.dumps(queue).encode()).decode()}
            if "/branches/" in path:
                return {"commit": {"sha": head}}
            raise AssertionError(path)

        host = {
            "AUTO_SEND": True, "CAR_MODEL_AUTODEV_ENABLED": True,
            "EXTERNAL_MODEL_AUTODEV_ENABLED": True,
            "CAR_MODEL_GITHUB_REPO": repo, "CAR_MODEL_TARGET_BRANCH": branch,
            "load_registry": lambda _now: reg,
            "save_registry": Mock(), "save_queue_state": Mock(), "write_runtime": Mock(),
            "send_guard_reason": lambda *args: "",
            "_parse_iso": lambda raw: datetime.fromisoformat(raw) if raw else None,
            "github_api_json": api,
            "replace_with_fresh_slot_page": AsyncMock(return_value=page),
            "hard_replace_slot_page": AsyncMock(return_value=page),
            "slot_page": AsyncMock(return_value=page),
            "detect_busy": AsyncMock(return_value=False),
            "detect_conversation_limit": AsyncMock(return_value=False),
            "ensure_logged_in": AsyncMock(return_value=True),
            "is_slot_project_url": lambda url, slot: True,
            "detect_rate_limit": AsyncMock(return_value=False),
            "detect_limit": AsyncMock(return_value=False),
            "ensure_thinking_level": AsyncMock(return_value=True),
            "send_message": sends,
            "wait_for_chat_url": AsyncMock(return_value=page.url + "/c/test"),
            "note_successful_request": Mock(), "mark_rate_limit": Mock(), "TZ": zone,
        }
        now = datetime(2026, 11, 23, 22, 0, 0, tzinfo=zone)
        self.assertTrue(await _module.external_model_cycle(None, {}, q, now, host))
        self.assertEqual(sends.await_count, 1)
        # Exact same scheduled window may never generate a duplicate send.
        self.assertFalse(await _module.external_model_cycle(None, {}, q, now, host))
        self.assertEqual(sends.await_count, 1)
        for minute in (30, 60):
            self.assertTrue(await _module.external_model_cycle(None, {}, q,
                now + timedelta(minutes=minute), host))
        self.assertEqual(sends.await_count, 3)
        self.assertFalse(await _module.external_model_cycle(None, {}, q,
            now + timedelta(minutes=90), host))
        self.assertEqual(sends.await_count, 3)
        self.assertEqual(host["write_runtime"].call_args.kwargs["status"],
                         "external_model_waiting_for_progress")
        # New material GitHub SHA unblocks the same task without changing its ID.
        head = "b" * 40
        self.assertTrue(await _module.external_model_cycle(None, {}, q,
            now + timedelta(minutes=120), host))
        self.assertEqual(sends.await_count, 4)
        self.assertEqual(q["ferrari_external_simple_A"]["last_task_id"], "EXT16-001")



class ContinuousDebugTests(unittest.TestCase):
    def test_hmd_stage_falls_back_to_perpetual_debug_without_claiming_hmd(self):
        q = fixture()
        q["work"].append({"id": "EXT16-006", "stage": "hardware_qa",
                          "status": "QUEUED", "requires_user_headset": True})
        q["work"].append({"id": "EXT16-011", "stage": "source_fix",
                          "status": "ACTIVE", "continuous_debug": True,
                          "title": "repeat debug", "acceptance": ["real tests"]})
        q["active_work_id"] = "EXT16-006"
        q["continuous_debug_policy"] = {"enabled": True, "work_id": "EXT16-011",
                                        "focus_rotation": ["eyes", "PBR"]}
        self.assertIsNone(_module.choose_external_work(q, REPO, BRANCH))
        work = _module.choose_continuous_debug_work(q, REPO, BRANCH)
        self.assertEqual(work["id"], "EXT16-011")
        self.assertFalse(work.get("requires_user_headset", False))
        self.assertEqual(q["active_work_id"], "EXT16-006")
        prompt = _module.make_external_prompt(work, q, "a"*40, True, 7, "PBR")
        self.assertIn("DEBUG_ITERATION=7", prompt)
        self.assertIn("ROTATING_FOCUS=PBR", prompt)
        self.assertIn("커밋이 없어도", prompt)
        self.assertIn("EXT16-011", prompt)

    def test_blocked_continuous_task_still_available_for_next_debug_cycle(self):
        q = fixture()
        q["active_work_id"] = "EXT16-011"
        q["work"].append({"id": "EXT16-011", "stage": "source_fix",
                          "status": "BLOCKED", "continuous_debug": True})
        q["continuous_debug_policy"] = {"enabled": True, "work_id": "EXT16-011"}
        self.assertIsNone(_module.choose_external_work(q, REPO, BRANCH))
        selected = _module.choose_continuous_debug_work(q, REPO, BRANCH)
        self.assertEqual(selected["status"], "ACTIVE")
        self.assertEqual(q["work"][-1]["status"], "BLOCKED")  # do not fake success

    def test_perpetual_debug_requires_explicit_enable_and_valid_scope(self):
        q = fixture()
        q["work"].append({"id": "EXT16-011", "stage": "source_fix",
                          "status": "ACTIVE", "continuous_debug": True})
        self.assertIsNone(_module.choose_continuous_debug_work(q, REPO, BRANCH))
        q["continuous_debug_policy"] = {"enabled": True, "work_id": "EXT16-011"}
        with self.assertRaises(ValueError):
            _module.choose_continuous_debug_work(q, "thp32tt/imsi1", "main")
        self.assertEqual(_module.choose_continuous_debug_work(q, REPO, BRANCH)["id"],
                         "EXT16-011")


class ContinuousDebugCycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_debug_keeps_dispatching_without_sha_change_and_rotates_focus(self):
        zone = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 24, 14, 0, tzinfo=zone)
        queue = fixture()
        queue["active_work_id"] = "EXT16-006"
        queue["work"].append({"id": "EXT16-006", "stage": "hardware_qa",
                              "requires_user_headset": True, "status": "QUEUED"})
        queue["work"].append({"id": "EXT16-011", "stage": "source_fix",
                              "continuous_debug": True, "status": "ACTIVE",
                              "title": "Continuous trace", "acceptance": ["fix only proven defects"]})
        queue["continuous_debug_policy"] = {
            "enabled": True, "work_id": "EXT16-011",
            "focus_rotation": ["left eye", "normal map", "fallback"]}
        state = {"ferrari_external_initialized": True,
                 "ferrari_external_simple_A": {"new_chat_required": True}}
        page = SimpleNamespace(url="https://chatgpt.com/g/g-p-6ab9a64fc428819198c7f39765d764bf/project")
        slot = SimpleNamespace(name="A", url=None, runs=0, last_sent_at=None,
            last_result=None, last_assistant_hash=None, last_assistant_change_at=None,
            watchdog_resumes_since_schedule=0)
        reg = SimpleNamespace(slots=[slot])
        sends = AsyncMock(return_value="sent")
        api = lambda path: ({"encoding": "base64", "content":
            base64.b64encode(json.dumps(queue).encode()).decode()}
            if "/contents/" in path else {"commit": {"sha": "a"*40}})
        host = {
            "AUTO_SEND": True, "CAR_MODEL_AUTODEV_ENABLED": True,
            "EXTERNAL_MODEL_AUTODEV_ENABLED": True,
            "CAR_MODEL_GITHUB_REPO": REPO, "CAR_MODEL_TARGET_BRANCH": BRANCH,
            "load_registry": lambda _now: reg,
            "save_registry": Mock(), "save_queue_state": Mock(), "write_runtime": Mock(),
            "send_guard_reason": lambda *args: "",
            "_parse_iso": lambda raw: datetime.fromisoformat(raw) if raw else None,
            "github_api_json": api,
            "replace_with_fresh_slot_page": AsyncMock(return_value=page),
            "hard_replace_slot_page": AsyncMock(return_value=page),
            "slot_page": AsyncMock(return_value=page),
            "detect_busy": AsyncMock(return_value=False),
            "detect_conversation_limit": AsyncMock(return_value=False),
            "ensure_logged_in": AsyncMock(return_value=True),
            "is_slot_project_url": lambda url, slot: True,
            "detect_rate_limit": AsyncMock(return_value=False),
            "detect_limit": AsyncMock(return_value=False),
            "ensure_thinking_level": AsyncMock(return_value=True),
            "send_message": sends,
            "wait_for_chat_url": AsyncMock(return_value=page.url + "/c/test"),
            "note_successful_request": Mock(), "mark_rate_limit": Mock(), "TZ": zone
        }
        # 6 consecutive half-hour windows on identical GitHub SHA; no hard hold.
        for k in range(6):
            self.assertTrue(await _module.external_model_cycle(
                None, {}, state, now + timedelta(minutes=30*k), host))
        self.assertEqual(sends.await_count, 6)
        prompts = [x.args[1] for x in sends.await_args_list]
        self.assertIn("ROTATING_FOCUS=left eye", prompts[0])
        self.assertIn("ROTATING_FOCUS=normal map", prompts[1])
        self.assertIn("ROTATING_FOCUS=fallback", prompts[2])
        self.assertIn("ROTATING_FOCUS=left eye", prompts[3])
        self.assertEqual(state["ferrari_external_simple_A"]["debug_cycle_count"], 6)
        self.assertEqual(state["ferrari_external_simple_A"]["same_progress_dispatches"], 6)
        self.assertEqual(host["hard_replace_slot_page"].await_count, 2)
        self.assertFalse(await _module.external_model_cycle(
            None, {}, state, now + timedelta(minutes=150), host))  # no double send
        self.assertEqual(sends.await_count, 6)


if __name__ == "__main__":
    unittest.main()
