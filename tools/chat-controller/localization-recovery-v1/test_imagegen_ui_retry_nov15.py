"""2026-11-15 A/B ImageGen browser selector and no-duplicate retry regressions."""
import copy
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import controller_png_attach as image_ui
import github_chat_rework_controller as bridge


def task():
    return {
        "task_id": "HDRW-A-" + "1"*20,
        "role": "A", "roi_id": "Q044_abcde12345678901",
        "source_dds_sha256": "a"*64,
        "old_candidate_sha256": "b"*64,
        "qa_authority":"NOT_C1_APPROVED_NOT_GAME_APPROVED",
        "reference": {"name": "HDRW-A-"+"1"*20+"_HD_SOURCE.png",
                      "sha256":"c"*64},
    }


def hold(t, **values):
    result = {
        "schema":"outrun-hd-qa-chat-status-v1",
        "task_id":t["task_id"], "task":copy.deepcopy(t),
        "role":t["role"], "roi_id":t["roi_id"],
        "source_dds_sha256":t["source_dds_sha256"],
        "old_candidate_sha256":t["old_candidate_sha256"],
        "release_approved":False, "runtime_validation":"UNTESTED",
        "status":"HOLD", "hold_reason":"HOLD_IMAGE_TOOL_NOT_VERIFIED",
        "updated_utc":"2026-11-14T03:00:00+00:00",
    }
    result.update(values)
    return result


class FakeGithub:
    def __init__(self, records=None):
        self.records=copy.deepcopy(records or {})
    def read_json(self,path,branch):
        assert branch == bridge.QUEUE_BRANCH
        value=copy.deepcopy(self.records.get(path))
        return value, ("sha" if value else None)
    def write_json(self,path,branch,data,expected=None,overwrite=False):
        self.records[path]=copy.deepcopy(data)
        return "commit"
    def req(self,path,branch,payload=None):
        return []


class SafePreSendRetryTests(unittest.TestCase):
    def test_only_exact_failed_tool_selection_can_retry(self):
        t=task()
        h=hold(t)
        self.assertTrue(bridge.image_tool_pre_send_retry_safe(h,t))
        self.assertTrue(bridge.image_tool_pre_send_retry_due(
            h,dt.datetime(2026,11,15,14,tzinfo=dt.timezone.utc)))
        for status in ("AB_CLAIMED","AB_SENT","C1_READY","C1_SENT"):
            self.assertFalse(bridge.image_tool_pre_send_retry_safe(
                hold(t,status=status),t))
        for reason in ("HOLD_CHAT_SENT_UNVERIFIED",
                       "HOLD_IMAGE_TOOL_LOST_BEFORE_SEND",
                       "HOLD_CHAT_UPLOAD_NOT_VERIFIED"):
            self.assertFalse(bridge.image_tool_pre_send_retry_safe(
                hold(t,hold_reason=reason),t))
        for evidence in ({"ab_chat_url":"https://chatgpt.com/c/already"},
                         {"candidate_sha256":"f"*64},
                         {"source_dds_sha256":"c"*64},
                         {"release_approved":True}):
            self.assertFalse(bridge.image_tool_pre_send_retry_safe(
                hold(t,**evidence),t))

    def test_pending_retry_backoff_and_legacy_safety(self):
        t=task()
        now=dt.datetime(2026,11,15,14,tzinfo=dt.timezone.utc)
        prior=hold(t,status=bridge.IMAGE_TOOL_RETRY_STATUS,
                   pre_send_no_message=True,
                   image_tool_last_attempt_utc=(now-dt.timedelta(minutes=5)).isoformat())
        self.assertTrue(bridge.image_tool_pre_send_retry_safe(prior,t))
        self.assertFalse(bridge.image_tool_pre_send_retry_due(prior,now))
        prior["image_tool_last_attempt_utc"]=(now-dt.timedelta(minutes=16)).isoformat()
        self.assertTrue(bridge.image_tool_pre_send_retry_due(prior,now))
        prior["pre_send_no_message"]=False
        self.assertFalse(bridge.image_tool_pre_send_retry_safe(prior,t))
        legacy=bridge.LEGACY_QROOT+"/state/"+t["task_id"]+".json"
        self.assertEqual(bridge.recover_previous_sent_task(
            FakeGithub({legacy:hold(t)}),t),"NEW")


class BridgePreflightTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=bridge.ROOT
        bridge.ROOT=Path(self.tmp.name)
        self.t=task()
        self.gh=FakeGithub()
        self.b=bridge.ChatBridge(self.gh,MagicMock())
    async def asyncTearDown(self):
        bridge.ROOT=self.root
        self.tmp.cleanup()

    async def test_preflight_failure_is_retryable_without_chat_send(self):
        self.b.page=AsyncMock(return_value=MagicMock())
        self.b.send_with_png=AsyncMock()
        with patch.object(bridge,"stage_source_ref",
                          return_value=Path("/tmp/exact-proven-source.png")),\
             patch.object(bridge,"ensure_image_tool",
                          new=AsyncMock(return_value="CREATE_IMAGE_OPTION_MISSING")):
            result=await self.b.submit_producer(self.t)
        self.assertEqual(result,"RETRY_IMAGE_TOOL_PRE_SEND")
        self.b.send_with_png.assert_not_awaited()
        state=self.gh.records[bridge.task_state_path(self.t["task_id"])]
        self.assertEqual(state["status"],bridge.IMAGE_TOOL_RETRY_STATUS)
        self.assertTrue(state["pre_send_no_message"])
        self.assertEqual(state["image_tool_retry_count"],1)

    async def test_cycle_can_retry_old_hold_but_never_ab_sent(self):
        latest={"schema":"outrun-hd-qa-chat-workqueue-v1",
                "tasks":[self.t],"release_approved":False,
                "runtime_validation":"UNTESTED",
                "new_imagegen_disabled":False,
                "source_reference_count_verified":1}
        self.gh.records[bridge.QROOT+"/latest.json"]=latest
        state=hold(self.t)
        self.gh.records[bridge.task_state_path(self.t["task_id"])]=state
        self.b.remote_state_recovered=True
        self.b.submit_producer=AsyncMock(return_value="RETRY_IMAGE_TOOL_PRE_SEND")
        with patch.object(bridge,"REUSE_ONLY",False):
            result=await self.b.cycle()
        self.assertEqual(len(result["sent"]),1)
        self.b.submit_producer.assert_awaited_once_with(self.t,prior=state)
        self.gh.records[bridge.task_state_path(self.t["task_id"])]=hold(
            self.t,status="AB_SENT",hold_reason=None,
            ab_chat_url="https://chatgpt.com/c/6aebd722-0f74-83e8-8126-f723dca3a685")
        self.b.submit_producer.reset_mock()
        with patch.object(bridge,"REUSE_ONLY",False):
            result=await self.b.cycle()
        self.assertEqual(result["sent"],[])
        self.b.submit_producer.assert_not_awaited()


class StaleAssistantReadOnlyRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_exact_chat_refresh_is_bounded_and_never_resends(self):
        t=task()
        url="https://chatgpt.com/c/6aebd722-0f74-83e8-8126-f723dca3a685"
        why="ASSISTANT_GENERATED_IMAGE_NOT_RENDERED_A0_G0_U1_L0"
        stale=hold(t,status="AB_SENT",hold_reason=None,
                   ab_chat_url=url,last_result_poll_reason=why,
                   last_result_poll_utc="2026-11-14T03:00:00+00:00")
        self.assertTrue(bridge.verified_assistant_refresh_due(
            stale,why,dt.datetime(2026,11,15,14,tzinfo=dt.timezone.utc)))
        recent=copy.deepcopy(stale)
        recent["last_assistant_page_refresh_utc"]="2026-11-15T13:50:00+00:00"
        self.assertFalse(bridge.verified_assistant_refresh_due(
            recent,why,dt.datetime(2026,11,15,14,tzinfo=dt.timezone.utc)))
        missing=copy.deepcopy(stale)
        del missing["ab_chat_url"]
        self.assertFalse(bridge.verified_assistant_refresh_due(missing,why))

        tmp=tempfile.TemporaryDirectory()
        old_root=bridge.ROOT
        bridge.ROOT=Path(tmp.name)
        try:
            gh=FakeGithub({bridge.task_state_path(t["task_id"]):stale})
            instance=bridge.ChatBridge(gh,MagicMock())
            page=MagicMock()
            page.url=url
            page.reload=AsyncMock()
            page.wait_for_timeout=AsyncMock()
            instance.page=AsyncMock(return_value=page)
            probe=AsyncMock(return_value=(
                "WAIT_ASSISTANT_RESULT_UI",why))
            with patch.object(bridge,"rescue_single_image_candidate",new=probe),\\
                 patch("text_roi_queue._probe_imagegen_result",
                       new=AsyncMock(return_value={"error":"USER_TURN_MISSING"})),\\
                 patch("text_roi_queue._recover_task_turn",
                       new=AsyncMock(return_value=False)):
                output=await instance.collect_producer(stale)
            self.assertIn("WAIT_IMAGEGEN",output)
            page.reload.assert_awaited_once_with(
                wait_until="domcontentloaded",timeout=45000)
            self.assertEqual(probe.await_count,3)
            self.assertEqual(gh.records[bridge.task_state_path(t["task_id"])]["status"],
                             "AB_SENT")
            self.assertIn("last_assistant_page_refresh_utc",
                          gh.records[bridge.task_state_path(t["task_id"])])
        finally:
            bridge.ROOT=old_root
            tmp.cleanup()


class CurrentChatGPTImagesMenuTests(unittest.IsolatedAsyncioTestCase):
    async def _ui(self,selected_on_click):
        page=MagicMock()
        state={"selected":False}
        class Loc:
            def __init__(self,kind):
                self.kind=kind
            async def count(self):
                return int(self.kind in ("more","images") or
                           (self.kind=="pill" and state["selected"]))
            def nth(self,i):
                return self
            async def is_visible(self):
                return True
            async def get_attribute(self,name):
                return None
            async def inner_text(self):
                return "Images"
            async def click(self,timeout=None):
                if self.kind=="images" and selected_on_click:
                    state["selected"]=True
            def filter(self,**kwargs):
                return self
        page.get_by_role.side_effect=lambda role,name=None,exact=None: Loc(
            "more" if role=="button" and name=="More" else
            "images" if role=="menuitem" and name=="Images" else "none")
        page.locator.side_effect=lambda css: Loc(
            "pill" if css=="[data-inline-selection-pill]" else "none")
        page.wait_for_timeout=AsyncMock()
        page.keyboard.press=AsyncMock()
        return await image_ui.ensure_image_tool(page)

    async def test_more_images_selected_chip_is_verified(self):
        self.assertEqual(await self._ui(True),"CREATE_IMAGE_TOOL_SELECTED")

    async def test_visible_menu_not_a_selected_tool(self):
        self.assertEqual(await self._ui(False),"CREATE_IMAGE_PILL_NOT_VISIBLE")


if __name__=="__main__":
    unittest.main()
