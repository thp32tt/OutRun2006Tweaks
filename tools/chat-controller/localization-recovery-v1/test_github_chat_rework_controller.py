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
  self.assertEqual(result,"CHATGPT_BROWSER_TAB_VISIBLE_AUTH_UNVERIFIED")
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



# Tests below simulate browser-returned ImageGen evidence. They do not claim
# to test a live authenticated ChatGPT session.
import base64
import hashlib
import chat_image_result_rescue as rescue


class GeneratedImageRescueTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.task="HDRW-A-"+"c"*20
  self.out=Path(self.temp.name)/"text_roi_batches"/"candidate_outputs"/"A"/(self.task+".png")
  self.evidence=Path(self.temp.name)/"text_roi_batches"/"export_evidence"/(self.task+".json")
  im=Image.new("RGBA",(96,48),(0,0,0,0))
  ImageDraw.Draw(im).rectangle((10,8,70,40),fill=(255,240,170,255))
  data=io.BytesIO();im.save(data,format="PNG")
  self.encoded="data:image/png;base64,"+base64.b64encode(data.getvalue()).decode()
 async def asyncTearDown(self):
  self.temp.cleanup()
 async def test_one_verified_assistant_output_is_exported_and_reused(self):
  class FakePage:
   def __init__(self,outer):self.outer=outer
   async def evaluate(self,js,arg):
    if js==rescue.ASSISTANT_IMAGE_JS:
     return {"status":"ASSISTANT_IMAGE_SOURCE_VERIFIED",
             "url":"blob:https://chatgpt.com/valid","width":96,"height":48}
    return self.outer.encoded
  page=FakePage(self)
  result,reason=await rescue.rescue_single_image_candidate(
   page,self.task,"A",self.temp.name)
  self.assertEqual(result,"LOCAL_CANDIDATES_EXPORTED_UNAPPROVED")
  self.assertTrue(self.out.is_file())
  self.assertTrue(self.evidence.is_file())
  self.assertEqual(hashlib.sha256(self.out.read_bytes()).hexdigest(),
                   json.loads(self.evidence.read_text())["files"][0]["sha256"])
  again,_=await rescue.rescue_single_image_candidate(
   page,self.task,"A",self.temp.name)
  self.assertEqual(again,"EXISTING_CANDIDATES_VERIFIED")
 async def test_generic_or_unrelated_image_never_exported(self):
  class FakePage:
   async def evaluate(self,js,arg):
    return {"status":"ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING"}
  status,why=await rescue.rescue_single_image_candidate(
   FakePage(),self.task,"A",self.temp.name)
  self.assertEqual(status,"WAIT_ASSISTANT_RESULT_UI")
  self.assertEqual(why,"ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING")
  self.assertFalse(self.out.exists())
 async def test_ambiguous_assistant_image_never_exported(self):
  class FakePage:
   async def evaluate(self,js,arg):
    return {"status":"ASSISTANT_IMAGE_AMBIGUOUS","count":2}
  status,_=await rescue.rescue_single_image_candidate(
   FakePage(),self.task,"A",self.temp.name)
  self.assertEqual(status,"WAIT_ASSISTANT_RESULT_UI")
  self.assertFalse(self.out.exists())
 async def test_invalid_external_image_url_fails_without_export(self):
  class FakePage:
   async def evaluate(self,js,arg):
    return {"status":"ASSISTANT_IMAGE_SOURCE_VERIFIED",
            "url":"http://127.0.0.1/private","width":96,"height":48}
  status,why=await rescue.rescue_single_image_candidate(
   FakePage(),self.task,"A",self.temp.name)
  self.assertEqual(status,"WAIT_ASSISTANT_RESULT_EXPORT")
  self.assertIn("UNTRUSTED_GENERATED_IMAGE_URL",why)
  self.assertFalse(self.out.exists())
 def test_assistant_image_dom_selector_is_strict_and_user_excluded(self):
  js=rescue.ASSISTANT_IMAGE_JS
  self.assertIn("data-message-author-role",js)
  self.assertIn("==='assistant'",js)
  self.assertIn("UPLOAD_TASK_ID=",js)
  self.assertNotIn("querySelectorAll('img')",js)
  self.assertTrue(rescue.safe_image_url("blob:https://chatgpt.com/abc"))
  self.assertTrue(rescue.safe_image_url("https://files.oaiusercontent.com/f.png"))
  self.assertFalse(rescue.safe_image_url("http://localhost:8000/img.png"))
  self.assertFalse(rescue.safe_image_url("https://openai.com.evil.example/png"))


class RoundRobinAndDiagnosticsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.old_root=c.ROOT
  c.ROOT=Path(self.temp.name)
 def tearDown(self):
  c.ROOT=self.old_root
  self.temp.cleanup()
 def test_round_robin_polls_all_16_jobs_instead_of_first_three(self):
  names=[f"HDRW-A-{i:020x}" for i in range(16)]
  files=[Path(name+".json") for name in names]
  cursor=None
  visited=[]
  for _ in range(6):
   ordered=c.fair_task_files(files,cursor)
   batch=ordered[:3]
   visited.extend(p.stem for p in batch)
   cursor=batch[-1].stem
  self.assertEqual(len(set(visited)),16)
  self.assertEqual(visited[:3],names[:3])
  self.assertEqual(visited[-2:],names[:2])
 def test_unchanged_wait_reason_is_throttled_with_remote_readback(self):
  task={"task_id":"HDRW-A-"+"1"*20,"role":"A",
        "roi_id":"Q044_65bad63fe0353b2b",
        "source_dds_sha256":"a"*64,
        "old_candidate_sha256":"b"*64,
        "reference":{"name":"HDRW-A-"+"1"*20+"_HD_SOURCE.png","sha256":"c"*64}}
  path=c.task_state_path(task["task_id"])
  state={"task":task,"status":"AB_SENT","task_id":task["task_id"],
         "role":"A","source_dds_sha256":"a"*64}
  gh=FakeFallbackGithub({path:state})
  self.assertTrue(c.result_poll_diagnostic(gh,state,"ASSISTANT_TURN_NOT_READY"))
  saved=gh.records[path]
  self.assertEqual(saved["status"],"AB_SENT")
  self.assertFalse(saved["release_approved"])
  self.assertEqual(saved["last_result_poll_reason"],"ASSISTANT_TURN_NOT_READY")
  self.assertFalse(c.result_poll_diagnostic(gh,saved,"ASSISTANT_TURN_NOT_READY"))
  self.assertEqual(len(gh.writes),1)


class CollectorIntegrationTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.old_root=c.ROOT
  c.ROOT=Path(self.temp.name)
  self.task={
   "task_id":"HDRW-A-"+("9"*20),"role":"A","roi_id":"Q044_65bad63fe0353b2b",
   "source_dds_sha256":"a"*64,"old_candidate_sha256":"b"*64,
   "reference":{"name":"HDRW-A-"+("9"*20)+"_HD_SOURCE.png",
                "sha256":"c"*64,"width":180,"height":75},
  }
  self.state={"status":"AB_SENT","task":self.task,"task_id":self.task["task_id"],
              "role":"A","source_dds_sha256":"a"*64}
  self.gh=FakeFallbackGithub()
  self.gh.pngs={}
  def put_png(path,branch,png,**kwargs):
   self.gh.pngs[path]=png
   return "commit-sha"
  self.gh.write=put_png
  self.bridge=c.ChatBridge(self.gh,MagicMock())
  self.bridge.page=AsyncMock(return_value=MagicMock(
   url="https://chatgpt.com/c/6aebd722-0f74-83e8-8126-f723dca3a685"))
 async def asyncTearDown(self):
  c.ROOT=self.old_root
  self.temp.cleanup()
 async def test_legacy_probe_miss_uses_assistant_rescue_without_resend(self):
  im=Image.new("RGBA",(200,110),(0,0,0,0))
  ImageDraw.Draw(im).rectangle((10,10,160,82),fill=(245,230,180,255))
  buffer=io.BytesIO();im.save(buffer,format="PNG")
  raw=buffer.getvalue()
  async def fake_rescue(page,task_id,role,root,binding=None):
   self.assertEqual(binding["source_dds_sha256"],"a"*64)
   self.assertEqual(binding["task_id"],task_id)
   p=Path(root)/"text_roi_batches"/"candidate_outputs"/role/(task_id+".png")
   p.parent.mkdir(parents=True,exist_ok=True)
   p.write_bytes(raw)
   return "LOCAL_CANDIDATES_EXPORTED_UNAPPROVED","ASSISTANT_ONLY_ONE_IMAGE_SHA_VERIFIED"
  with patch("text_roi_queue._probe_imagegen_result",
             new=AsyncMock(return_value={"error":"USER_TURN_MISSING"})), \
       patch("text_roi_queue._recover_task_turn",new=AsyncMock(return_value=False)) as reload_chat, \
       patch.object(c,"rescue_single_image_candidate",new=AsyncMock(side_effect=fake_rescue)) as method:
   status=await self.bridge.collect_producer(self.state)
   self.assertEqual(status,"C1_READY")
   method.assert_awaited_once()
   reload_chat.assert_not_awaited()
  self.assertEqual(len(self.gh.pngs),1)
  saved=self.gh.records[c.task_state_path(self.task["task_id"])]
  self.assertEqual(saved["status"],"C1_READY")
  self.assertEqual(saved["candidate_sha256"],
                   hashlib.sha256(next(iter(self.gh.pngs.values()))).hexdigest())
  self.assertFalse(saved["release_approved"])
 async def test_no_image_keeps_ab_sent_and_emits_remote_diagnostic(self):
  with patch("text_roi_queue._probe_imagegen_result",
             new=AsyncMock(return_value={"error":"USER_TURN_MISSING"})), \
       patch("text_roi_queue._recover_task_turn",new=AsyncMock(return_value=False)), \
       patch.object(c,"rescue_single_image_candidate",new=AsyncMock(
          return_value=("WAIT_ASSISTANT_RESULT_UI",
                        "ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING"))):
   status=await self.bridge.collect_producer(self.state)
  self.assertIn("WAIT_IMAGEGEN_",status)
  saved=self.gh.records[c.task_state_path(self.task["task_id"])]
  self.assertEqual(saved["status"],"AB_SENT")
  self.assertEqual(saved["last_result_poll_reason"],
                   "ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING")
  self.assertEqual(len(self.gh.pngs),0)


class ImagegenPollEfficiencyTests(CollectorIntegrationTests):
 async def test_no_assistant_media_never_reloads_verified_chat(self):
  page=self.bridge.page.return_value
  with patch("text_roi_queue._probe_imagegen_result",
             new=AsyncMock(return_value={"error":"USER_TURN_MISSING"})) as legacy, \
       patch("text_roi_queue._recover_task_turn",
             new=AsyncMock(return_value=False)) as reload_chat, \
       patch.object(c,"rescue_single_image_candidate",new=AsyncMock(
           return_value=("WAIT_ASSISTANT_RESULT_UI",
                         "ASSISTANT_GENERATED_IMAGE_NOT_RENDERED_A0_G0_U1_L0"))) as rescue_probe:
   status=await self.bridge.collect_producer(self.state)
  self.assertEqual(status,
      "WAIT_IMAGEGEN_ASSISTANT_GENERATED_IMAGE_NOT_RENDERED_A0_G0_U1_L0")
  self.assertEqual(rescue_probe.await_count,2)
  legacy.assert_awaited_once()
  reload_chat.assert_not_awaited()
  page.wait_for_timeout.assert_not_called()
  self.assertEqual(len(self.gh.pngs),0)
  saved=self.gh.records[c.task_state_path(self.task["task_id"])]
  self.assertEqual(saved["status"],"AB_SENT")
  self.assertEqual(saved["last_result_poll_reason"],
      "ASSISTANT_GENERATED_IMAGE_NOT_RENDERED_A0_G0_U1_L0")


class ImageGenFailureRecoveryTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.task="HDRW-B-"+"2"*20
 async def asyncTearDown(self):
  self.temp.cleanup()
 async def test_explicit_generation_failure_does_not_write_candidate(self):
  class FakePage:
   async def evaluate(self,js,arg):
    return {"status":"IMAGEGEN_FAILED_UI"}
  outcome,reason=await rescue.rescue_single_image_candidate(
   FakePage(),self.task,"B",self.temp.name)
  self.assertEqual(outcome,"WAIT_ASSISTANT_RESULT_UI")
  self.assertEqual(reason,"IMAGEGEN_FAILED_UI")
  self.assertFalse((Path(self.temp.name)/"text_roi_batches").exists())
 async def test_explicit_error_detection_does_not_resend(self):
  import inspect
  js=rescue.ASSISTANT_IMAGE_JS
  self.assertIn("something went wrong while generating your image",js)
  self.assertIn("isWithinBoundedReply",js)
  source=inspect.getsource(c.ChatBridge.collect_producer)
  self.assertIn("result_poll_diagnostic",source)
  self.assertNotIn("submit_producer(",source)


class ExistingChatReadOnlyTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.url="https://chatgpt.com/c/6aebd722-0f74-83e8-8126-f723dca3a685"
  self.bridge=c.ChatBridge(MagicMock(),MagicMock())
  self.bridge.ensure_context=AsyncMock()
  self.page=MagicMock()
  self.page.is_closed.return_value=False
  self.page.url=self.url
  self.page.goto=AsyncMock()
  self.bridge.pages["A"]=self.page
 async def test_collector_reads_same_persisted_chat_without_composer(self):
  self.page.locator.side_effect=AssertionError("COMPOSER_MUST_NOT_BLOCK_RESULT_READ")
  got=await self.bridge.page("A",self.url,read_only=True)
  self.assertIs(got,self.page)
  self.page.locator.assert_not_called()
  self.page.goto.assert_not_awaited()
 async def test_missing_source_chat_url_fails_closed(self):
  got=await self.bridge.page("A",None,read_only=True)
  self.assertIsNone(got)
  self.bridge.ensure_context.assert_not_awaited()
 async def test_redirected_chat_fails_closed_without_composer(self):
  self.page.url="https://chatgpt.com/auth/login"
  self.page.goto=AsyncMock()
  # A login redirect stays at /auth/login, never a verified source chat.
  got=await self.bridge.page("A",self.url,read_only=True)
  self.assertIsNone(got)
  self.page.goto.assert_awaited_once()
 async def test_producer_send_still_requires_visible_composer(self):
  textbox=MagicMock()
  textbox.wait_for=AsyncMock(side_effect=TimeoutError("composer not visible"))
  self.page.locator.return_value=MagicMock(first=textbox)
  got=await self.bridge.page("A",self.url)
  self.assertIsNone(got)
  self.page.locator.assert_called_once()
  textbox.wait_for.assert_awaited_once()
 async def test_c1_and_a_b_read_only_call_sites_explicit(self):
  import inspect
  source=inspect.getsource(c.ChatBridge.collect_producer)
  self.assertIn("read_only=True",source)
  source_c1=inspect.getsource(c.ChatBridge.inspect_c1)
  self.assertIn("read_only=True",source_c1)


class CurrentProjectDOMContractTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.task="HDRW-A-"+("d"*20)
  self.source={"task_id":self.task,
               "english":"Ghost Forest",
               "korean":"고스트 포레스트",
               "source_dds_sha256":"a"*64}
 async def asyncTearDown(self):
  self.temp.cleanup()
 async def test_bound_fields_sent_to_modern_browser_dom_probe(self):
  args=[]
  class FakePage:
   async def evaluate(self,js,arg):
    args.append(arg)
    return {"status":"SOURCE_BOUND_USER_TURN_MISSING"}
  outcome,detail=await rescue.rescue_single_image_candidate(
    FakePage(),self.task,"A",self.temp.name,binding=self.source)
  self.assertEqual(outcome,"WAIT_ASSISTANT_RESULT_UI")
  self.assertEqual(detail,"SOURCE_BOUND_USER_TURN_MISSING")
  self.assertEqual(args[0],{
    "task":self.task,"english":"Ghost Forest",
    "korean":"고스트 포레스트","sha":"a"*64})
 async def test_current_ui_is_selected_as_well_as_legacy(self):
  js=rescue.ASSISTANT_IMAGE_JS
  self.assertIn('[data-markdown-text-tone="user-message"]',js)
  self.assertIn('[data-markdown-text-tone="assistant"]',js)
  self.assertIn("data-chatgpt-search-unit-key",js)
  self.assertIn("data-message-author-role",js)
  self.assertIn("UPLOAD_TASK_ID=",js)
  self.assertIn("영문 원문: ",js)
  self.assertIn("한국어 번역: ",js)
  self.assertIn("원본 DDS SHA: ",js)
 async def test_ui_diagnostic_exposes_only_bounded_node_counts(self):
  class FakePage:
   async def evaluate(self,js,arg):
    return {"status":"ASSISTANT_GENERATED_IMAGE_NOT_RENDERED",
            "ui":{"assistant":0,"generated":0,"user":1,"auth":1}}
  status,reason=await rescue.rescue_single_image_candidate(
    FakePage(),self.task,"A",self.temp.name,binding=self.source)
  self.assertEqual(status,"WAIT_ASSISTANT_RESULT_UI")
  self.assertEqual(reason,
     "ASSISTANT_GENERATED_IMAGE_NOT_RENDERED_A0_G0_U1_L1")
  self.assertFalse((Path(self.temp.name)/"text_roi_batches").exists())
 async def test_out_of_range_ui_counts_are_never_exported(self):
  class FakePage:
   async def evaluate(self,js,arg):
    return {"status":"ASSISTANT_GENERATED_IMAGE_NOT_RENDERED",
            "ui":{"assistant":-1,"generated":999,"user":1,"auth":1}}
  status,reason=await rescue.rescue_single_image_candidate(
    FakePage(),self.task,"A",self.temp.name,binding=self.source)
  self.assertEqual(reason,"ASSISTANT_GENERATED_IMAGE_NOT_RENDERED")
  self.assertEqual(status,"WAIT_ASSISTANT_RESULT_UI")

 async def test_unbound_or_ambiguous_chat_cannot_advance(self):
  class FakePage:
   async def evaluate(self,js,arg):
    return {"status":"SOURCE_BOUND_USER_TURN_AMBIGUOUS"}
  state,detail=await rescue.rescue_single_image_candidate(
    FakePage(),self.task,"A",self.temp.name,binding=self.source)
  self.assertEqual(state,"WAIT_ASSISTANT_RESULT_UI")
  self.assertEqual(detail,"SOURCE_BOUND_USER_TURN_AMBIGUOUS")
  self.assertFalse((Path(self.temp.name)/"text_roi_batches").exists())
 def test_source_triple_evidence_never_lies_about_marker(self):
  png,dimensions=rescue.checked_image_bytes(self.make_png())
  status=rescue.save_candidate_evidence(
    self.temp.name,"A",self.task,png,dimensions,
    hashlib.sha256(png).hexdigest(),match_method="SOURCE_TRIPLE")
  self.assertEqual(status,"LOCAL_CANDIDATES_EXPORTED_UNAPPROVED")
  proof=json.loads((Path(self.temp.name)/"text_roi_batches"/"export_evidence"/
                    (self.task+".json")).read_text())
  self.assertIn("SOURCE_TRIPLE",proof["files"][0]["pairing"])
  self.assertNotIn("EXACT_USER_MARKER",proof["files"][0]["pairing"])
 def make_png(self):
  image=Image.new("RGBA",(128,64),(0,0,0,0))
  ImageDraw.Draw(image).rectangle((11,10,100,50),fill=(255,255,255,255))
  buf=io.BytesIO(); image.save(buf,format="PNG")
  return buf.getvalue()
 def test_unknown_proof_kind_is_rejected_before_writing(self):
  png,dimensions=rescue.checked_image_bytes(self.make_png())
  with self.assertRaisesRegex(ValueError,"UNSUPPORTED_ASSISTANT_TURN_PROOF"):
   rescue.save_candidate_evidence(self.temp.name,"A",self.task,png,dimensions,
        hashlib.sha256(png).hexdigest(),match_method="FAKE")
  self.assertFalse((Path(self.temp.name)/"text_roi_batches").exists())


if __name__=="__main__":
 unittest.main()
