#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
from PIL import Image

HERE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE))
import gpt_vision_chat_ocr as g

class GPTChatOCRTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.src=root/"src";self.src.mkdir()
        self.out=root/"out";self.out.mkdir()
        self.gpt_out=root/"gpt_out";self.gpt_out.mkdir()
        self.report=root/"report";(self.report/"processed_v3").mkdir(parents=True)
        self.queue=root/"queue";self.queue.mkdir()
        self.old={k:getattr(g,k) for k in ("SRC","OUT","GPT_OUT","REPORT","QUEUE_DIR","STATE_PATH","AUDIT_PATH")}
        g.SRC=self.src;g.OUT=self.out;g.GPT_OUT=self.gpt_out;g.REPORT=self.report;g.QUEUE_DIR=self.queue
        g.STATE_PATH=self.queue/"state.json";g.AUDIT_PATH=self.queue/"audit.jsonl"
        self.addCleanup(self.restore)
        self.name="Q001_TEST_BASE_READABLE_FLIPY.png"
        im=Image.new("RGBA",(100,60),(0,0,0,0))
        for x in range(10,50):
            for y in range(10,30):
                im.putpixel((x,y),(255,255,255,255))
        self.path=self.src/self.name;im.save(self.path)
        sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.row={"png_filename":self.name,"png_sha256":sha,"png_size_bytes":str(self.path.stat().st_size),
                  "width":"100","height":"60","source_dds_path":"textures/test.dds",
                  "dds_sha256":"0"*64,"queue_indexes":"001"}
        self.old_manifest=g._manifest_rows
        self.old_margin=g._load_margin_check
        g._manifest_rows=lambda:{self.name:self.row}
        g._load_margin_check=lambda:(lambda image,box:None)
        self.addCleanup(lambda:setattr(g,"_manifest_rows",self.old_manifest))
        self.addCleanup(lambda:setattr(g,"_load_margin_check",self.old_margin))
        (self.report/"processed_v3"/(self.name+".json")).write_text(json.dumps({
            "source_png":self.name,"source_sha256":sha,"attempts":21,
            "unresolved_after":["HELLO"]
        }),encoding="utf-8")
    def restore(self):
        for k,v in self.old.items():setattr(g,k,v)

    def test_end_to_end_chat_response_to_direct_manifest(self):
        binding,reason=g.next_binding()
        self.assertIsNone(reason)
        self.assertEqual(binding["role"],"C1OCR")
        self.assertIn("이미지를 수정하거나 새 이미지를 만들지 마세요",binding["prompt"])
        self.assertIn("HELLO",binding["prompt"])
        self.assertEqual(g.stage_submission(binding["task_id"]),"SUBMITTING")
        url="https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc"
        self.assertEqual(g.record_chat_url(binding["task_id"],url),"URL_RECORDED")
        response=json.dumps({"task_id":binding["task_id"],"source_png":self.name,
          "detections":[{"english":"HELLO","bbox_xyxy":[10,10,50,30],"confidence":0.96}],
          "uncertain":[]})
        result=g.apply_response(binding["task_id"],response)
        self.assertEqual(result["status"],"APPLIED")
        self.assertEqual(result["applied"],1)
        manifests=list(self.gpt_out.glob("*/*/manifest.json"))
        self.assertEqual(len(manifests),1)
        m=json.loads(manifests[0].read_text())
        self.assertEqual(m["english"],"HELLO")
        self.assertEqual(m["bbox_xyxy"],[10,10,50,30])
        self.assertFalse(m["external_api_used"])
        self.assertFalse(m["image_generation_used"])
        self.assertEqual(m["status"],"DIRECT_IMAGEGEN_READY")
        self.assertTrue(m["direct_full_hd_reference"])
        self.assertFalse(m["crop_created"])
        self.assertEqual(m["target_dimensions"],[40,20])
        crop=manifests[0].parent/"english_original_native_crop.png"
        self.assertFalse(crop.exists())

    def test_wrong_task_response_is_held_and_retryable(self):
        binding,_=g.next_binding()
        g.stage_submission(binding["task_id"])
        g.record_chat_url(binding["task_id"],"https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc")
        response=json.dumps({"task_id":"WRONG","source_png":self.name,"detections":[],"uncertain":[]})
        result=g.apply_response(binding["task_id"],response)
        self.assertEqual(result["status"],"RESPONSE_HOLD")
        retry,reason=g.next_binding()
        self.assertIsNone(reason)
        self.assertTrue(retry["task_id"].endswith("-R1"))

    def test_unapproved_phrase_and_out_of_bounds_are_rejected(self):
        binding,_=g.next_binding();g.stage_submission(binding["task_id"])
        g.record_chat_url(binding["task_id"],"https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc")
        response=json.dumps({"task_id":binding["task_id"],"source_png":self.name,
          "detections":[
            {"english":"NOT APPROVED","bbox_xyxy":[1,1,20,20],"confidence":1.0},
            {"english":"HELLO","bbox_xyxy":[1,1,999,20],"confidence":1.0}
          ],"uncertain":[]})
        result=g.apply_response(binding["task_id"],response)
        self.assertEqual(result["status"],"NO_VALID_DETECTIONS")
        self.assertEqual(result["applied"],0)
        self.assertIn("PHRASE_NOT_APPROVED",result["rejected"])
        self.assertIn("BBOX_OUT_OF_RANGE",result["rejected"])

    def test_low_confidence_is_not_auto_queued(self):
        binding,_=g.next_binding();g.stage_submission(binding["task_id"])
        g.record_chat_url(binding["task_id"],"https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc")
        response=json.dumps({"task_id":binding["task_id"],"source_png":self.name,
          "detections":[{"english":"HELLO","bbox_xyxy":[10,10,50,30],"confidence":0.40}],
          "uncertain":[]})
        result=g.apply_response(binding["task_id"],response)
        self.assertEqual(result["status"],"NO_VALID_DETECTIONS")
        self.assertIn("CONFIDENCE_TOO_LOW",result["rejected"])
        self.assertEqual(list(self.gpt_out.glob("*/*/manifest.json")),[])

    def test_stale_response_auto_retries_then_skips(self):
        import datetime as dt
        binding,_=g.next_binding()
        g.stage_submission(binding["task_id"])
        g.record_chat_url(binding["task_id"],"https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc")
        st=g._state()
        st["active"]["sent_at"]=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=700)).isoformat()
        g._save_state(st)
        first=g.recover_stale_active(600)
        self.assertEqual(first["status"],"RESPONSE_TIMEOUT_RETRY")
        self.assertIsNone(g.active_task())
        retry,reason=g.next_binding()
        self.assertIsNone(reason)
        self.assertTrue(retry["task_id"].endswith("-R1"))
        g.stage_submission(retry["task_id"])
        g.record_chat_url(retry["task_id"],"https://chatgpt.com/c/22345678-1234-1234-1234-123456789abc")
        st=g._state()
        st["active"]["sent_at"]=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=700)).isoformat()
        g._save_state(st)
        second=g.recover_stale_active(600)
        self.assertEqual(second["status"],"RESPONSE_TIMEOUT_MAX_ATTEMPTS")
        self.assertIsNone(g.active_task())
        nxt,reason=g.next_binding()
        self.assertIsNone(nxt)
        self.assertEqual(reason,"GPT_CHAT_OCR_QUEUE_EMPTY_OR_EXHAUSTED")

    def test_response_extractor_upgrade_retries_timeout_only_fingerprint(self):
        binding,_=g.next_binding()
        fp=binding["fingerprint"]
        st=g._state()
        st["active"]=None
        st["attempts"][fp]=2
        st["completed"].append({
            "task_id":binding["task_id"],"source_png":self.name,"fingerprint":fp,
            "status":"RESPONSE_TIMEOUT_MAX_ATTEMPTS","applied":0
        })
        st["response_extractor_version"]="legacy-selector-v1"
        g._save_state(st)
        retry,reason=g.next_binding()
        self.assertIsNone(reason)
        self.assertEqual(retry["fingerprint"],fp)
        self.assertEqual(retry["attempt_index"],0)
        migrated=g._state()
        self.assertEqual(migrated["response_extractor_version"],g.RESPONSE_EXTRACTOR_VERSION)

    def test_fenced_json_parser(self):
        ticks=chr(96)*3
        raw=ticks+"json\n"+json.dumps({"task_id":"X","source_png":"Y","detections":[]})+"\n"+ticks
        obj=g._extract_json(raw)
        self.assertEqual(obj["task_id"],"X")

if __name__=="__main__":
    unittest.main(verbosity=2)