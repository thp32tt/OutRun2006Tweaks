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
 async def make_bridge(self,navigation_error=None):
  page=MagicMock()
  page.url="about:blank"
  page.is_closed.return_value=False
  page.bring_to_front=AsyncMock()
  page.goto=AsyncMock(side_effect=navigation_error)
  context=MagicMock()
  context.pages=[page]
  context.new_page=AsyncMock(return_value=page)
  browser=MagicMock()
  browser.contexts=[context]
  browser.close=AsyncMock()
  chromium=MagicMock()
  chromium.connect_over_cdp=AsyncMock(return_value=browser)
  playwright=MagicMock()
  playwright.chromium=chromium
  bridge=c.ChatBridge(None,playwright)
  return bridge,page,context,chromium

 async def test_vnc_browser_reuses_visible_chrome_login_tab_without_github(self):
  bridge,page,context,chromium=await self.make_bridge()
  result=await bridge.bootstrap_login_page()
  self.assertEqual(result,"CHATGPT_LOGIN_BROWSER_VISIBLE_NOT_AUTHENTICATED")
  chromium.connect_over_cdp.assert_awaited_once_with(
      "http://127.0.0.1:9222",timeout=30000)
  context.new_page.assert_not_awaited()
  page.bring_to_front.assert_awaited_once()
  page.goto.assert_awaited_once_with(c.PROJECT_URL,
      wait_until="domcontentloaded",timeout=30000)
  self.assertIn("A",bridge.pages)
  self.assertIsNone(bridge.gh)

 async def test_navigation_failure_leaves_same_visible_login_tab(self):
  bridge,page,context,chromium=await self.make_bridge(
      TimeoutError("network unavailable"))
  self.assertEqual(await bridge.bootstrap_login_page(),
      "HOLD_CHATGPT_PAGE_NAVIGATION_TimeoutError")
  self.assertIs(bridge.pages["A"],page)
  context.new_page.assert_not_awaited()

 async def test_browser_context_ambiguous_is_hold(self):
  playwright=MagicMock()
  browser=MagicMock()
  browser.contexts=[]
  browser.close=AsyncMock()
  playwright.chromium.connect_over_cdp=AsyncMock(return_value=browser)
  bridge=c.ChatBridge(None,playwright)
  with self.assertRaisesRegex(RuntimeError,"CONTEXT_NOT_EXACTLY_ONE"):
   await bridge.bootstrap_login_page()
  browser.close.assert_awaited_once()


# Fallback task identity, recovered ChatGPT conversation links, and safe PNG
# normalization are independent of the browser/network.
import copy


class FakeFallbackGithub:
 def __init__(self, records=None):
  self.records=copy.deepcopy(records or {})
  self.writes=[]
 def read_json(self,path,branch):
  assert branch==c.QUEUE_BRANCH
  value=copy.deepcopy(self.records.get(path))
  return value, ("synthetic-sha" if value is not None else None)
 def write_json(self,path,branch,data,expected=None,overwrite=False):
  assert branch==c.QUEUE_BRANCH
  if path in self.records:
   assert expected=="synthetic-sha"
  self.records[path]=copy.deepcopy(data)
  self.writes.append((path,data["status"]))
  return "synthetic-commit"


class FallbackQueueResumeAndPixelTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.old_root=c.ROOT
  c.ROOT=Path(self.temp.name)
  self.task={
   "task_id":"HDRW-A-"+("7"*20),"role":"A","roi_id":"Q044_65bad63fe0353b2b",
   "source_dds_sha256":"a"*64,"old_candidate_sha256":"b"*64,
   "reference":{"name":"HDRW-A-"+("7"*20)+"_HD_SOURCE.png","sha256":"c"*64},
  }
  self.url="https://chatgpt.com/g/g-p-6acdb8270260819190da244c0bf006a3-ausreon-hangeulhwa-singyu/c/6aebd722-0f74-83e8-8126-f723dca3a685"
  self.old_path=c.LEGACY_QROOT+"/state/"+self.task["task_id"]+".json"
  self.new_path=c.task_state_path(self.task["task_id"])
 def tearDown(self):
  c.ROOT=self.old_root
  self.temp.cleanup()
 def state(self,**overrides):
  result={"schema":"outrun-hd-qa-chat-status-v1",
          "task":copy.deepcopy(self.task),"task_id":self.task["task_id"],
          "role":"A","release_approved":False,"status":"AB_SENT",
          "ab_chat_url":self.url}
  result.update(overrides)
  return result
 def test_actual_project_chat_link_allowed(self):
  self.assertTrue(c.is_saved_chat_url(self.url))
  self.assertTrue(c.is_saved_chat_url("https://chatgpt.com/c/6aebd722-0f74-83e8-8126-f723dca3a685"))
 def test_chat_links_reject_cross_origin_and_query(self):
  for s in ["http://chatgpt.com/"+self.url.split("chatgpt.com/")[1],
            self.url+"?token=abc","https://bad.example/c/6aebd722-0f74-83e8-8126-f723dca3a685","https://chatgpt.com/"]:
   self.assertFalse(c.is_saved_chat_url(s))
 def test_original_ab_sent_is_resumed_not_resent(self):
  gh=FakeFallbackGithub({self.old_path:self.state()})
  self.assertEqual(c.recover_previous_sent_task(gh,self.task),"RECOVERED_AB_SENT_NO_RESEND")
  self.assertEqual(gh.records[self.new_path]["status"],"AB_SENT")
  self.assertEqual(gh.records[self.new_path]["ab_chat_url"],self.url)
  self.assertEqual(gh.records[self.old_path]["status"],"AB_SENT")
  self.assertEqual(len(gh.writes),1)
  self.assertEqual(json.loads(c.local_task_path(self.task["task_id"]).read_text())["status"],"AB_SENT")
 def test_no_prior_task_may_proceed_as_new(self):
  gh=FakeFallbackGithub()
  self.assertEqual(c.recover_previous_sent_task(gh,self.task),"NEW")
  self.assertEqual(gh.writes,[])
 def test_conflicting_previous_reference_is_hold(self):
  previous=self.state()
  previous["task"]["reference"]["sha256"]="f"*64
  gh=FakeFallbackGithub({self.old_path:previous})
  self.assertEqual(c.recover_previous_sent_task(gh,self.task),"HOLD_LEGACY_TASK_CONFLICT")
  self.assertEqual(gh.records[self.new_path]["status"],"HOLD")
 def test_prior_claim_never_resent(self):
  gh=FakeFallbackGithub({self.old_path:self.state(status="AB_CLAIMED")})
  self.assertEqual(c.recover_previous_sent_task(gh,self.task),"HOLD_LEGACY_TASK_NO_RESEND")
  self.assertEqual(gh.records[self.new_path]["status"],"HOLD")
 def test_untrusted_old_chat_never_resent(self):
  gh=FakeFallbackGithub({self.old_path:self.state(ab_chat_url="https://bad.example/")})
  self.assertEqual(c.recover_previous_sent_task(gh,self.task),"HOLD_LEGACY_TASK_NO_RESEND")
 def test_original_queue_write_immutable(self):
  self.assertNotEqual(c.QROOT,c.LEGACY_QROOT)
  gh=c.Github("unit-test-token")
  with self.assertRaisesRegex(ValueError,"LEGACY_QUEUE_IS_READ_ONLY"):
   gh.req(self.old_path,c.QUEUE_BRANCH,payload={"bad":True})
 def test_cropping_preserves_every_alpha_pixel(self):
  im=Image.new("RGBA",(1024,768),(0,0,0,0))
  for x in range(310,330):
   for y in range(210,224):
    im.putpixel((x,y),(230,180,80,(x+y)%256))
  data=io.BytesIO();im.save(data,format="PNG")
  packed=c.compact_generated_png_lossless(data.getvalue())
  self.assertEqual(packed[:8],b"\x89PNG\r\n\x1a\n")
  with Image.open(io.BytesIO(packed)) as actual:
   self.assertEqual(actual.size,(36,30))
   self.assertEqual(actual.getpixel((8,8)),im.getpixel((310,210)))
   self.assertEqual(actual.getpixel((27,21)),im.getpixel((329,223)))
  self.assertEqual(c.valid_generated_image(packed),[36,30])
 def test_alpha_touch_original_frame_still_fails(self):
  im=Image.new("RGBA",(100,70),(0,0,0,0))
  im.putpixel((0,10),(255,0,0,255))
  data=io.BytesIO();im.save(data,format="PNG")
  with self.assertRaisesRegex(ValueError,"ALPHA_TOUCHES_FRAME"):
   c.compact_generated_png_lossless(data.getvalue())


if __name__=="__main__":
 unittest.main()
