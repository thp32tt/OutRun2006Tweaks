"""Fast offline protocol gates; no login, browser session, or GitHub write."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
import github_chat_rework_controller as c

class ReworkBridgeProtocol(unittest.TestCase):
 def fixture_task(self):
  return {"task_id":"HDRW-A-"+"a"*20,"role":"A","roi_id":"Q044_abcde12345678901",
          "source_dds_path":"textures/load/spr_x/demo.dds",
          "source_dds_sha256":"a"*64,"old_candidate_sha256":"b"*64,
          "reference":{"name":"HDRW-A-"+"a"*20+"_HD_SOURCE.png","sha256":"c"*64}}
 def test_role_and_source_guards(self):
  t=self.fixture_task()
  self.assertTrue(c.valid_task(t))
  t["role"]="B"
  self.assertFalse(c.valid_task(t))
 def test_exact_c1_source_and_candidate_sha(self):
  t=self.fixture_task()
  response={"task_id":t["task_id"],"source_dds_sha256":"a"*64,
            "candidate_sha256":"c"*64,"decision":"PASS_PROVISIONAL",
            "reason":"원본 HD 글자 크기, 획과 줄 수를 동일 기준으로 검토했습니다."}
  parsed=c.c1_decision_from_text(json.dumps(response,ensure_ascii=False),
                     t["task_id"],"a"*64,"c"*64)
  self.assertEqual(parsed["decision"],"PASS_PROVISIONAL")
  self.assertIsNone(c.c1_decision_from_text(json.dumps(response,ensure_ascii=False),
                     t["task_id"],"a"*64,"e"*64))
  self.assertIsNone(c.c1_decision_from_text("PASS",t["task_id"],"a"*64,"c"*64))
 def test_candidate_transparency_and_bounds(self):
  im=Image.new("RGBA",(100,55),(0,0,0,0))
  ImageDraw.Draw(im).rectangle((10,10,78,42),fill=(255,255,255,255))
  out=io.BytesIO();im.save(out,format="PNG",optimize=True)
  self.assertEqual(c.valid_generated_image(out.getvalue()),[100,55])
  ImageDraw.Draw(im).rectangle((0,0,1,1),fill=(255,255,255,255))
  out=io.BytesIO();im.save(out,format="PNG",optimize=True)
  with self.assertRaisesRegex(ValueError,"ALPHA_TOUCHES_FRAME"):
   c.valid_generated_image(out.getvalue())
 def test_github_fail_closed_without_token(self):
  with self.assertRaisesRegex(ValueError,"TOKEN_REQUIRED"):
   c.Github("")
  self.assertTrue(c.QROOT.startswith("localization/automation_runs"))
  with self.assertRaises(ValueError):
   c.check_project_url("http://chatgpt.com/")
 def test_task_paths_and_state_bound(self):
  t=self.fixture_task()
  self.assertTrue(str(c.task_state_path(t["task_id"])).endswith(".json"))
  with self.assertRaises(ValueError):
   c.task_state_path("bad")
  self.assertLessEqual(c.MAX_CONTENTS_PNG,650*1024)

from unittest.mock import AsyncMock, MagicMock, patch


class BrowserBootstrapBeforeGithubTests(unittest.IsolatedAsyncioTestCase):
 async def test_vnc_browser_opens_without_github_token_or_queue(self):
  with tempfile.TemporaryDirectory() as root:
   with patch.object(c,"ROOT",Path(root)):
    page=MagicMock()
    page.url="about:blank"
    page.is_closed.return_value=False
    page.bring_to_front=AsyncMock()
    page.goto=AsyncMock()
    context=MagicMock()
    context.new_page=AsyncMock(return_value=page)
    chromium=MagicMock()
    chromium.launch_persistent_context=AsyncMock(return_value=context)
    browser=MagicMock()
    browser.chromium=chromium
    bridge=c.ChatBridge(None,browser)
    result=await bridge.bootstrap_login_page()
    self.assertEqual(result,"CHATGPT_LOGIN_BROWSER_VISIBLE_NOT_AUTHENTICATED")
    chromium.launch_persistent_context.assert_awaited_once()
    context.new_page.assert_awaited_once()
    page.bring_to_front.assert_awaited_once()
    page.goto.assert_awaited_once_with(c.PROJECT_URL,
        wait_until="domcontentloaded",timeout=30000)
    self.assertIn("A",bridge.pages)
    self.assertIsNone(bridge.gh)

 async def test_navigation_failure_leaves_browser_for_manual_login(self):
  with tempfile.TemporaryDirectory() as root:
   with patch.object(c,"ROOT",Path(root)):
    page=MagicMock()
    page.url="about:blank"
    page.is_closed.return_value=False
    page.bring_to_front=AsyncMock()
    page.goto=AsyncMock(side_effect=TimeoutError("network unavailable"))
    context=MagicMock()
    context.new_page=AsyncMock(return_value=page)
    chromium=MagicMock()
    chromium.launch_persistent_context=AsyncMock(return_value=context)
    browser=MagicMock()
    browser.chromium=chromium
    bridge=c.ChatBridge(None,browser)
    self.assertEqual(await bridge.bootstrap_login_page(),
        "HOLD_CHATGPT_PAGE_NAVIGATION_TimeoutError")
    self.assertIs(bridge.pages["A"],page)
    context.new_page.assert_awaited_once()


if __name__=="__main__":
 unittest.main()
