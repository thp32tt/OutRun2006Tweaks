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
        self.old={k:getattr(g,k) for k in ("SRC","OUT","GPT_OUT","REPORT","QUEUE_DIR","STATE_PATH","AUDIT_PATH","HOST_RETRY_PATH","PRODUCTION_MANIFEST","PIXEL_REVIEW_ROOT","VISUAL_ABSENCE_PATH")}
        g.SRC=self.src;g.OUT=self.out;g.GPT_OUT=self.gpt_out;g.REPORT=self.report;g.QUEUE_DIR=self.queue
        g.STATE_PATH=self.queue/"state.json";g.AUDIT_PATH=self.queue/"audit.jsonl"
        g.HOST_RETRY_PATH=self.queue/"host_verified_retries.json"
        g.PRODUCTION_MANIFEST=self.queue/"production_manifest.json"
        g.PIXEL_REVIEW_ROOT=self.queue/"pixel_review"
        g.VISUAL_ABSENCE_PATH=self.queue/"visual_absence.json"
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

    def test_stale_submitting_watchdog_recovers_to_staged(self):
        import datetime as dt
        binding,_=g.next_binding()
        self.assertEqual(g.stage_submission(binding["task_id"]),"SUBMITTING")
        st=g._state()
        st["active"]["submitting_at"]=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=g.SUBMISSION_STALL_SECONDS+5)).isoformat()
        g._save_state(st)
        result=g.recover_stale_active()
        self.assertEqual(result["status"],"STALE_SUBMITTING_RECOVERED")
        self.assertTrue(result["recovered"])
        active=g.active_task()
        self.assertEqual(active["status"],"STAGED")
        self.assertEqual(active["last_presend_failure"],"STALE_SUBMITTING_WATCHDOG_RECOVERY")

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

    def test_response_upgrade_recovers_c2_timeout_without_resetting_success(self):
        st=g._state()
        timed_out="a"*64
        succeeded="b"*64
        st["attempts"]={"C2:"+timed_out:2,"C2:"+succeeded:2}
        st["completed"]=[
            {"task_id":"OUTRUN-GPT-OCR-Q002-AAAAAAAA-C2-R1",
             "fingerprint":timed_out,"status":"RESPONSE_TIMEOUT_MAX_ATTEMPTS","applied":0},
            {"task_id":"OUTRUN-GPT-OCR-Q004-BBBBBBBB-C2",
             "fingerprint":succeeded,"status":"APPLIED","applied":1},
        ]
        st["response_extractor_version"]="search-unit-assistant-v3-slot-aligned-20261026"
        reset=g._migrate_response_extractor_state(st)
        self.assertEqual(reset,["C2:"+timed_out])
        self.assertEqual(st["attempts"]["C2:"+timed_out],0)
        self.assertEqual(st["attempts"]["C2:"+succeeded],2)
        self.assertEqual(g._migrate_response_extractor_state(st),[])

    def test_manual_visual_absence_is_sha_scoped_and_never_localization_pass(self):
        absent={"schema":"outrun.ocr.visual_absence_review.v1","items":[
          {"status":"NOT_VISIBLE_IN_THIS_VERIFIED_SPRITE_VARIANT",
            "visual_review":"ORIGINAL_HD_IMAGE_DIRECTLY_INSPECTED_BY_CHATGPT_AI2",
            "source_png":self.name,"source_sha256":self.row["png_sha256"],
            "english":"HELLO"}]}
        g.VISUAL_ABSENCE_PATH.write_text(json.dumps(absent),encoding="utf-8")
        g._visual_absence_cached.cache_clear()
        self.assertEqual(g.summary()["candidate_sources"],0)
        self.assertEqual(g.summary()["retryable_sources"],0)
        self.assertIsNone(g.next_binding("C1")[0])
        self.assertEqual(list(self.gpt_out.glob("*/*/manifest.json")),[])
        # A different source SHA or a changed positive judgement cannot hide
        # a new or edited original image from the review queue.
        absent["items"][0]["source_sha256"]="0"*64
        g.VISUAL_ABSENCE_PATH.write_text(json.dumps(absent),encoding="utf-8")
        g._visual_absence_cached.cache_clear()
        self.assertEqual(g.summary()["retryable_sources"],1)
        absent["items"][0]["source_sha256"]=self.row["png_sha256"]
        absent["items"][0]["status"]="PENDING_VISUAL_REVIEW"
        g.VISUAL_ABSENCE_PATH.write_text(json.dumps(absent),encoding="utf-8")
        g._visual_absence_cached.cache_clear()
        self.assertEqual(g.summary()["retryable_sources"],1)

    def test_visual_absent_restriction_does_not_hide_another_phrase(self):
        rec=self.report/"processed_v3"/(self.name+".json")
        j=json.loads(rec.read_text(encoding="utf-8"))
        j["unresolved_after"]=["HELLO","NEXT"]
        rec.write_text(json.dumps(j),encoding="utf-8")
        absent={"schema":"outrun.ocr.visual_absence_review.v1","items":[
          {"status":"NOT_VISIBLE_IN_THIS_VERIFIED_SPRITE_VARIANT",
           "visual_review":"ORIGINAL_HD_IMAGE_DIRECTLY_INSPECTED_BY_CHATGPT_AI2",
           "source_png":self.name,"source_sha256":self.row["png_sha256"],
           "english":"HELLO"}]}
        g.VISUAL_ABSENCE_PATH.write_text(json.dumps(absent),encoding="utf-8")
        g._visual_absence_cached.cache_clear()
        bind,reason=g.next_binding("C1")
        self.assertIsNone(reason)
        self.assertEqual(bind["target_phrases"],["NEXT"])

    def test_pixel_crop_review_only_never_promotes_ocr_region(self):
        import os
        from unittest.mock import patch
        rect=[10,10,50,30]
        p=g.PIXEL_REVIEW_ROOT/"crops"/"genuine.png"
        p.parent.mkdir(parents=True)
        with Image.open(self.path) as original:
            original.crop(tuple(rect)).save(p)
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        review={"schema":"outrun.pixel_ocr_review.v1","sources":[{
          "source_png":self.name,"source_png_sha256":self.row["png_sha256"],
          "proposals":[{"bbox_xyxy":rect,"display_name":p.name,
                         "crop_sha256":sha,"art_or_merged_risk":False}]}]}
        # The crop eligibility gate requires width >=70px, so create a
        # larger, verified 80px-wide thumbnail from the original source.
        rect=[5,5,90,40]
        with Image.open(self.path) as original:
            original.crop(tuple(rect)).save(p)
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        review["sources"][0]["proposals"][0].update(bbox_xyxy=rect,crop_sha256=sha)
        (g.PIXEL_REVIEW_ROOT/"latest.json").write_text(json.dumps(review))
        st=g._state()
        fp=g._fingerprint(self.row,["HELLO"])
        st["attempts"][fp]=2
        g._save_state(st)
        with patch.dict(os.environ,{"OUTRUN_PIXEL_OCR_REVIEW_ENABLED":"true"}):
            b,reason=g.next_binding("C1")
            self.assertIsNone(reason)
            self.assertTrue(b["pixel_review_only"])
            self.assertEqual(b["path"],str(p))
            self.assertEqual(g.stage_submission(b["task_id"]),"SUBMITTING")
            g.record_chat_url(b["task_id"],"https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc")
            response=json.dumps({"task_id":b["task_id"],"source_png":self.name,
              "detections":[{"english":"HELLO","bbox_xyxy":[5,5,45,25],"confidence":0.96}],
              "uncertain":[]})
            applied=g.apply_response(b["task_id"],response)
            self.assertEqual(applied["status"],"REVIEW_REQUIRED_PIXEL_ROI")
            self.assertEqual(applied["applied"],0)
            self.assertEqual(list(self.gpt_out.glob("*/*/manifest.json")),[])
            records=list((g.PIXEL_REVIEW_ROOT/"responses").glob("*.json"))
            self.assertEqual(len(records),1)
            item=json.loads(records[0].read_text())
            self.assertFalse(item["production_queue_modified"])
            self.assertEqual(item["proposals_not_approved"][0]["proposed_global_bbox_xyxy"],[10,10,50,30])

    def test_pixel_crop_rejects_tampered_image_sha(self):
        import os
        from unittest.mock import patch
        p=g.PIXEL_REVIEW_ROOT/"crops"/"genuine.png"
        p.parent.mkdir(parents=True)
        with Image.open(self.path) as original:
            original.crop((5,5,90,40)).save(p)
        item={"schema":"outrun.pixel_ocr_review.v1","sources":[{
           "source_png":self.name,"source_png_sha256":self.row["png_sha256"],
           "proposals":[{"bbox_xyxy":[5,5,90,40],"display_name":p.name,
                         "crop_sha256":"0"*64,"art_or_merged_risk":False}]}]}
        (g.PIXEL_REVIEW_ROOT/"latest.json").write_text(json.dumps(item))
        st=g._state();st["attempts"][g._fingerprint(self.row,["HELLO"])]=2
        g._save_state(st)
        with patch.dict(os.environ,{"OUTRUN_PIXEL_OCR_REVIEW_ENABLED":"true"}):
            b,reason=g.next_binding("C1")
            self.assertIsNone(b)
            self.assertEqual(reason,"GPT_CHAT_OCR_QUEUE_EMPTY_OR_EXHAUSTED")

    def test_registered_production_roi_is_not_requeued_for_chat_ocr(self):
        source_sha=self.row["png_sha256"]
        manifest={"schema":"outrun-text-roi-production-v1","item_count":1,
            "items":[{"id":"Q001_APPROVED","status":"ROI_APPROVED_FOR_IMAGEGEN",
                      "source_png_sha256":source_sha,"english":"HELLO",
                      "bbox_xyxy":[10,10,50,30]}]}
        g.PRODUCTION_MANIFEST.write_text(json.dumps(manifest),encoding="utf-8")
        g._production_regions_cached.cache_clear()
        self.assertIn("hello",g._covered_phrases(self.name,source_sha))
        self.assertIn(("HELLO",(10,10,50,30)),g._known_ocr_regions(self.name,source_sha))
        self.assertEqual(g.summary()["candidate_sources"],0)
        self.assertIsNone(g.next_binding("C1")[0])
        # A registered ROI needs independent image QA and DDS testing; the
        # lookup must not imply those stages have passed.

    def test_production_roi_coverage_rejects_wrong_source_sha_and_bad_manifest(self):
        entry={"id":"BAD","status":"ROI_APPROVED_FOR_IMAGEGEN",
               "source_png_sha256":"0"*64,"english":"HELLO",
               "bbox_xyxy":[10,10,50,30]}
        doc={"schema":"outrun-text-roi-production-v1","item_count":1,"items":[entry]}
        g.PRODUCTION_MANIFEST.write_text(json.dumps(doc),encoding="utf-8")
        g._production_regions_cached.cache_clear()
        self.assertEqual(g.summary()["retryable_sources"],1)
        doc["items"][0]["source_png_sha256"]=self.row["png_sha256"]
        doc["item_count"]=2
        g.PRODUCTION_MANIFEST.write_text(json.dumps(doc),encoding="utf-8")
        g._production_regions_cached.cache_clear()
        self.assertEqual(g.summary()["retryable_sources"],1)
        doc["item_count"]=1
        doc["items"][0]["status"]="ROI_REBALANCED_TO_B"
        g.PRODUCTION_MANIFEST.write_text(json.dumps(doc),encoding="utf-8")
        g._production_regions_cached.cache_clear()
        self.assertEqual(g.summary()["candidate_sources"],0)

    def _host_rescue_doc(self,phrases=None):
        phrases=phrases or ["HELLO"]
        record=self.report/"processed_v3"/(self.name+".json")
        return {"schema":"outrun.gpt_ocr.host_verified_retries.v1",
            "items":[{"source_png":self.name,
              "source_sha256":self.row["png_sha256"],
              "processed_sha256":hashlib.sha256(record.read_bytes()).hexdigest(),
              "target_phrases":phrases,
              "fingerprint":g._fingerprint(self.row,phrases)}]}

    def test_host_verified_snapshot_recovers_missing_container_source(self):
        # Simulate the real incident: the controller's local candidate
        # discovery has no records, but the verified host queue has one.
        old=g._exhausted_candidates
        g._exhausted_candidates=lambda:[]
        self.addCleanup(lambda:setattr(g,"_exhausted_candidates",old))
        g.HOST_RETRY_PATH.write_text(json.dumps(self._host_rescue_doc()),encoding="utf-8")
        summary=g.summary()
        self.assertEqual(summary["retryable_sources"],1)
        self.assertEqual(summary["retryable_phrases"],1)
        binding,reason=g.next_binding("C1")
        self.assertIsNone(reason)
        self.assertEqual(binding["source_png"],self.name)
        self.assertEqual(binding["target_phrases"],["HELLO"])
        self.assertEqual(binding["source_sha256"],self.row["png_sha256"])
        st=g._state()
        st["active"]=None
        st["attempts"][g._attempt_key(binding["fingerprint"],"C1")]=2
        g._save_state(st)
        retry,reason=g.next_binding("C1")
        self.assertIsNone(retry)
        self.assertEqual(reason,"GPT_CHAT_OCR_QUEUE_EMPTY_OR_EXHAUSTED")

    def test_host_verified_snapshot_rejects_tampering_and_covered_text(self):
        old=g._exhausted_candidates
        g._exhausted_candidates=lambda:[]
        self.addCleanup(lambda:setattr(g,"_exhausted_candidates",old))
        good=self._host_rescue_doc()
        for key,value in (("source_sha256","f"*64),
                           ("processed_sha256","f"*64),
                           ("target_phrases",["UNAPPROVED"])):
            bad=json.loads(json.dumps(good))
            bad["items"][0][key]=value
            g.HOST_RETRY_PATH.write_text(json.dumps(bad),encoding="utf-8")
            self.assertIsNone(g.next_binding("C1")[0],key)
        g.HOST_RETRY_PATH.write_text(json.dumps(good),encoding="utf-8")
        self.assertEqual(g.summary()["retryable_sources"],1)
        directory=self.out/Path(self.name).stem/"covered"
        directory.mkdir(parents=True)
        (directory/"manifest.json").write_text(json.dumps({
            "source_sha256":self.row["png_sha256"],"english":"HELLO",
            "bbox_xyxy":[10,10,50,30]}),encoding="utf-8")
        self.assertEqual(g.summary()["retryable_sources"],0)
        self.assertIsNone(g.next_binding("C1")[0])

    def test_duplicate_only_bbox_requires_manual_review_without_retry(self):
        # Same source area was already assigned to another English label.
        old=self.out/Path(self.name).stem/"older"
        old.mkdir(parents=True)
        (old/"manifest.json").write_text(json.dumps({
            "source_sha256":self.row["png_sha256"],"english":"OTHER",
            "bbox_xyxy":[10,10,50,30]}),encoding="utf-8")
        binding,_=g.next_binding()
        self.assertEqual(g.stage_submission(binding["task_id"]),"SUBMITTING")
        self.assertEqual(g.record_chat_url(binding["task_id"],
            "https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc"),"URL_RECORDED")
        response=json.dumps({"task_id":binding["task_id"],"source_png":self.name,
          "detections":[{"english":"HELLO","bbox_xyxy":[10,10,50,30],"confidence":0.96}],
          "uncertain":[]})
        result=g.apply_response(binding["task_id"],response)
        self.assertEqual(result["status"],"REVIEW_REQUIRED_DUPLICATE_BBOX")
        self.assertTrue(result["manual_review_required"])
        self.assertEqual(result["applied"],0)
        self.assertEqual(list(self.gpt_out.glob("*/*/manifest.json")),[])
        retry,reason=g.next_binding()
        self.assertIsNone(retry)
        self.assertEqual(reason,"GPT_CHAT_OCR_QUEUE_EMPTY_OR_EXHAUSTED")
        summary=g.summary()
        self.assertEqual(summary["manual_review_sources"],1)
        self.assertEqual(summary["manual_review_phrases"],1)
        self.assertEqual(summary["retryable_sources"],0)
        self.assertEqual(summary["exhausted_sources"],0)

        # Existing historical NO_VALID_DETECTIONS records must be honored too.
        st=g._state()
        st["completed"][-1]["status"]="NO_VALID_DETECTIONS"
        st["completed"][-1].pop("manual_review_required",None)
        g._save_state(st)
        self.assertEqual(g.summary()["manual_review_sources"],1)
        self.assertIsNone(g.next_binding()[0])

        # A changed unresolved phrase set has a distinct fingerprint and can
        # be reviewed without unblocking the original conflicting response.
        rec=self.report/"processed_v3"/(self.name+".json")
        processed=json.loads(rec.read_text())
        processed["unresolved_after"]=["HELLO","NEXT"]
        rec.write_text(json.dumps(processed),encoding="utf-8")
        fresh,reason=g.next_binding()
        self.assertIsNone(reason)
        self.assertEqual(fresh["target_phrases"],["HELLO","NEXT"])
        self.assertNotEqual(fresh["fingerprint"],binding["fingerprint"])

    def test_prompt_excludes_existing_regions_only_for_verified_source_sha(self):
        old=self.out/Path(self.name).stem/"older"
        old.mkdir(parents=True)
        (old/"manifest.json").write_text(json.dumps({
            "source_sha256":self.row["png_sha256"],"english":"OTHER",
            "bbox_xyxy":[10,10,50,30]}),encoding="utf-8")
        binding,_=g.next_binding()
        self.assertIn('기존 좌표와 90% 이상 겹치는 영역',binding["prompt"])
        self.assertIn('"english": "OTHER"',binding["prompt"])
        self.assertIn('"bbox_xyxy": [10, 10, 50, 30]',binding["prompt"])
        self.assertIn("uncertain",binding["prompt"])
        # Different source bytes never authorize old bounding-box exclusions.
        (old/"manifest.json").write_text(json.dumps({
            "source_sha256":"0"*64,"english":"POISON",
            "bbox_xyxy":[10,10,50,30]}),encoding="utf-8")
        self.assertNotIn("POISON",g._prompt(binding["task_id"],self.row,["HELLO"]))
        self.assertIn("- 없음",g._prompt(binding["task_id"],self.row,["HELLO"]))

    def test_low_confidence_invalid_bbox_remains_retryable(self):
        binding,_=g.next_binding();g.stage_submission(binding["task_id"])
        g.record_chat_url(binding["task_id"],
            "https://chatgpt.com/c/12345678-1234-1234-1234-123456789abc")
        response=json.dumps({"task_id":binding["task_id"],"source_png":self.name,
          "detections":[{"english":"HELLO","bbox_xyxy":[10,10,50,30],"confidence":0.3}],
          "uncertain":[]})
        self.assertEqual(g.apply_response(binding["task_id"],response)["status"],"NO_VALID_DETECTIONS")
        self.assertEqual(g.summary()["manual_review_sources"],0)
        retry,reason=g.next_binding()
        self.assertIsNone(reason)
        self.assertTrue(retry["task_id"].endswith("-R1"))

    def test_lane_partition_and_c2_independent_attempt_counter(self):
        even_name="Q002_TEST_BASE_READABLE_FLIPY.png"
        even_path=self.src/even_name
        even_path.write_bytes(self.path.read_bytes())
        even_sha=hashlib.sha256(even_path.read_bytes()).hexdigest()
        even_row={"png_filename":even_name,"png_sha256":even_sha,"png_size_bytes":str(even_path.stat().st_size),
                  "width":"100","height":"60","source_dds_path":"textures/even.dds",
                  "dds_sha256":"1"*64,"queue_indexes":"002"}
        g._manifest_rows=lambda:{self.name:self.row,even_name:even_row}
        (self.report/"processed_v3"/(even_name+".json")).write_text(json.dumps({
            "source_png":even_name,"source_sha256":even_sha,"attempts":21,
            "unresolved_after":["EVEN"]
        }),encoding="utf-8")

        summary=g.summary()
        self.assertEqual(summary["lanes"]["C1"]["retryable_sources"],1)
        self.assertEqual(summary["lanes"]["C2"]["retryable_sources"],1)

        binding,reason=g.next_binding("C2")
        self.assertIsNone(reason)
        self.assertEqual(binding["source_png"],even_name)
        self.assertEqual(binding["role"],"C2OCR")
        self.assertEqual(binding["ocr_lane"],"C2")
        self.assertIn("-C2",binding["task_id"])
        self.assertTrue(binding["attempt_key"].startswith("C2:"))
        self.assertEqual(g.stage_submission(binding["task_id"]),"SUBMITTING")
        self.assertEqual(g.record_chat_url(binding["task_id"],
            "https://chatgpt.com/c/32345678-1234-1234-1234-123456789abc"),"URL_RECORDED")
        st=g._state()
        self.assertEqual(st["attempts"][binding["attempt_key"]],1)
        self.assertNotIn(binding["fingerprint"],st["attempts"])

    def test_lane_selector_rejects_invalid_lane(self):
        with self.assertRaisesRegex(ValueError,"GPT_OCR_LANE_INVALID"):
            g.next_binding("C3")

    def test_fenced_json_parser(self):
        ticks=chr(96)*3
        raw=ticks+"json\n"+json.dumps({"task_id":"X","source_png":"Y","detections":[]})+"\n"+ticks
        obj=g._extract_json(raw)
        self.assertEqual(obj["task_id"],"X")

if __name__=="__main__":
    unittest.main(verbosity=2)