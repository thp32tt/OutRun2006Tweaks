#!/usr/bin/env python3
"""Offline tests for the separate post-tile ImageGen ROI queue."""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ab_batch_queue
import controller_png_attach
import text_roi_queue


class TextRoiQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        base = self.root / "text_roi_batches"
        (base / "inputs").mkdir(parents=True)
        self.image_path = base / "inputs" / "Q104_OutRunMode.png"
        Image.new("RGBA", (64, 24), (0, 0, 0, 0)).save(self.image_path)
        self.item = {
            "id": "Q104_OutRunMode", "role": "A", "queue_index": "104",
            "status": "ROI_APPROVED_FOR_IMAGEGEN",
            "source_provenance": "DIRECT_FULL_HD_PNG",
            "source_dds_path": "textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds",
            "source_dds_sha256": "a" * 64, "source_png_sha256": "b" * 64,
            "bbox_xyxy": [10, 8, 75, 40],
            "imagegen_input_png": self.image_path.name,
            "imagegen_input_sha256": hashlib.sha256(self.image_path.read_bytes()).hexdigest(),
            "alpha_crop_margin_checked": True,
            "english": "OutRun Mode", "korean": "아웃런 모드",
        }
        self.manifest = base / "production_manifest.json"
        self.write_manifest([self.item])
        env = patch.dict(os.environ, {
            "OUTRUN_AB_TEXT_ROI_QUEUE": "true", "OUTRUN_AB_BATCH_QUEUE": "false",
        })
        env.start()
        self.addCleanup(env.stop)

    def write_manifest(self, items):
        self.manifest.write_text(
            json.dumps({"schema": "outrun-text-roi-production-v1", "items": items}, ensure_ascii=False),
            encoding="utf-8"
        )

    def test_one_source_can_stage_and_is_sha_bound(self):
        binding, error = controller_png_attach.load_binding("A", root=self.root)
        self.assertIsNone(error)
        self.assertEqual(binding["expected_images"], 1)
        self.assertIn("아웃런 모드", binding["prompt"])
        self.assertIn("\n", binding["prompt"])
        self.assertTrue(Path(binding["path"]).is_file())
        retried, error = ab_batch_queue.next_binding("A", root=self.root)
        self.assertIsNone(error)
        self.assertEqual(retried["task_id"], binding["task_id"])
        self.assertEqual(ab_batch_queue.stage_submission("A", binding["task_id"], self.root), "SUBMITTING")
        blocked, reason = ab_batch_queue.next_binding("A", self.root)
        self.assertIsNone(blocked)
        self.assertIn("BATCH_AWAITING_RESULT_AND_LIBRARY", reason)

    def test_role_partition_never_steals_other_role(self):
        binding, reason = controller_png_attach.load_binding("B", self.root)
        self.assertIsNone(binding)
        self.assertEqual(reason, "ROI_ROLE_QUEUE_EMPTY_OR_FINISHED")

    def test_unreviewed_cannot_be_submitted(self):
        bad = dict(self.item, status="ROI_PROPOSAL_TEXT_CONTENT_NOT_REVIEWED")
        self.write_manifest([bad])
        binding, reason = controller_png_attach.load_binding("A", self.root)
        self.assertIsNone(binding)
        self.assertEqual(reason, "ROI_ROLE_QUEUE_EMPTY_OR_FINISHED")

    def test_sha_mismatch_holds(self):
        bad = dict(self.item, imagegen_input_sha256="0" * 64)
        self.write_manifest([bad])
        binding, reason = controller_png_attach.load_binding("A", self.root)
        self.assertIsNone(binding)
        self.assertIn("SHA_MISMATCH", reason)

    def test_unverified_source_provenance_holds(self):
        bad = dict(self.item, source_provenance="SHA_PINNED_TILE_REASSEMBLY_TEST_ONLY")
        self.write_manifest([bad])
        binding, reason = controller_png_attach.load_binding("A", self.root)
        self.assertIsNone(binding)
        self.assertIn("UNVERIFIED_FULL_SOURCE", reason)

    def test_legacy_tile_queue_remains_disabled(self):
        with patch.dict(os.environ, {"OUTRUN_AB_TEXT_ROI_QUEUE": "false",
                                    "OUTRUN_AB_BATCH_QUEUE": "true"}):
            binding, reason = ab_batch_queue.next_binding("A", self.root)
            self.assertIsNone(binding)
            self.assertEqual(reason, "HOLD_LEGACY_TILES_RETIRED_TEXT_ROI_QUEUE_REQUIRED")

    def test_redeploy_reopens_recorded_active_chat_before_result_probe(self):
        binding,error=text_roi_queue.next_binding("A",self.root)
        self.assertIsNone(error)
        text_roi_queue.stage_submission("A",binding["task_id"],self.root)
        target="https://chatgpt.com/c/active-batch-chat"
        text_roi_queue.record_chat_url("A",binding["task_id"],target,self.root)
        sent=self.root/"sent"
        sent.mkdir(parents=True,exist_ok=True)
        (sent/f'A_{binding["task_id"]}.json').write_text(json.dumps({
            "status":"CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS",
            "task_id":binding["task_id"],"role":"A",
            "tiles":[{"filename":Path(binding["path"]).name}]
        }),encoding="utf-8")

        class Page:
            def __init__(self):
                self.url="https://chatgpt.com/c/restored-old-slot"
                self.opened=[]
            async def goto(self,url,**kwargs):
                self.opened.append(url)
                self.url=url
            async def evaluate(self,*args,**kwargs):
                return {"count":0,"expected":1,"busy":False,"verified_by":"TEST","error":None}

        page=Page()
        can_continue,status=asyncio.run(text_roi_queue.inspect_slot("A",page,self.root))
        self.assertFalse(can_continue)
        self.assertEqual(page.opened,[target])
        self.assertTrue(status.startswith("IMAGEGEN_OUTPUT_COUNT_MISMATCH:"))

    def test_five_input_single_output_is_quarantined_and_retried_as_five(self):
        items=[]
        for i in range(5):
            name=f"Q121_Item_{i}.png"
            path=self.image_path.with_name(name)
            Image.new("RGBA",(80+i,30),(0,0,0,0)).save(path)
            items.append({
                **self.item,
                "id":f"Q121_Item_{i}",
                "role":"B",
                "queue_index":"121",
                "imagegen_input_png":name,
                "imagegen_input_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "english":f"English {i}",
                "korean":f"한글 {i}",
            })
        self.write_manifest(items)
        binding,error=text_roi_queue.next_binding("B",self.root)
        self.assertIsNone(error)
        self.assertEqual(binding["expected_images"],5)
        self.assertIn("BATCH_COUNT=5",binding["prompt"])
        self.assertIn("출력 개수(n)를 반드시 BATCH_COUNT=5",binding["prompt"])
        self.assertIn("총 5장을 생성하세요",binding["prompt"])
        old_task=binding["task_id"]
        text_roi_queue.stage_submission("B",old_task,self.root)
        target="https://chatgpt.com/c/five-image-batch"
        text_roi_queue.record_chat_url("B",old_task,target,self.root)
        sent=self.root/"sent"; sent.mkdir(parents=True,exist_ok=True)
        (sent/f"B_{old_task}.json").write_text(json.dumps({
            "status":"CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS",
            "task_id":old_task,"role":"B",
            "tiles":[{"filename":x["filename"]} for x in binding["tiles"]]
        }),encoding="utf-8")

        class Page:
            url=target
            async def evaluate(self,*args,**kwargs):
                return {"count":1,"expected":5,"busy":False,
                        "verified_by":"SINGLE_VISIBLE_PREVIEW_FALLBACK","error":None}

        can_continue,status=asyncio.run(text_roi_queue.inspect_slot("B",Page(),self.root))
        self.assertTrue(can_continue)
        self.assertEqual(status,"FIVE_IMAGE_BATCH_RETRY_STAGED")
        st=json.loads((self.root/"text_roi_batches/B_state.json").read_text())
        self.assertEqual(st["active"]["task_id"],old_task+"-R1")
        self.assertEqual(st["active"]["status"],"STAGED")
        self.assertEqual(st["active"]["retry_count"],1)
        self.assertEqual(st["active"]["ordinals"],[1,2,3,4,5])
        self.assertEqual(st["next_ordinal"],1)
        self.assertEqual(st["completed_files"],0)
        self.assertEqual(st["quarantined"][-1]["task_id"],old_task)
        self.assertEqual(st["quarantined"][-1]["observed_generated_images"],1)

        retry,error=text_roi_queue.next_binding("B",self.root)
        self.assertIsNone(error)
        self.assertEqual(retry["task_id"],old_task+"-R1")
        self.assertEqual(retry["expected_images"],5)
        self.assertEqual([x["ordinal"] for x in retry["tiles"]],[1,2,3,4,5])

    def test_zero_of_five_library_match_quarantines_exports_and_retries_same_ordinals(self):
        items=[]
        for i in range(5):
            name=f"Q205_Library_{i}.png"
            path=self.image_path.with_name(name)
            Image.new("RGBA",(96+i,36),(0,0,0,0)).save(path)
            items.append({
                **self.item,
                "id":f"Q205_Library_{i}",
                "role":"A",
                "queue_index":"205",
                "imagegen_input_png":name,
                "imagegen_input_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "english":f"Source {i}",
                "korean":f"번역 {i}",
            })
        self.write_manifest(items)
        binding,error=text_roi_queue.next_binding("A",self.root)
        self.assertIsNone(error)
        old_task=binding["task_id"]
        text_roi_queue.stage_submission("A",old_task,self.root)
        target="https://chatgpt.com/c/library-zero-five"
        text_roi_queue.record_chat_url("A",old_task,target,self.root)
        sent=self.root/"sent"; sent.mkdir(parents=True,exist_ok=True)
        (sent/f"A_{old_task}.json").write_text(json.dumps({
            "status":"CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS",
            "task_id":old_task,"role":"A",
            "tiles":[{"filename":x["filename"]} for x in binding["tiles"]]
        }),encoding="utf-8")

        outdir=self.root/"text_roi_batches/candidate_outputs/A"
        outdir.mkdir(parents=True)
        files=[]
        for item in binding["items"]:
            binary=(b"candidate-"+item["filename"].encode())*20
            name=item["output_filename"]
            (outdir/name).write_bytes(binary)
            files.append({"name":name,"sha256":hashlib.sha256(binary).hexdigest()})
        ev=self.root/"text_roi_batches/export_evidence"; ev.mkdir(parents=True)
        (ev/f"{old_task}.json").write_text(json.dumps({
            "task_id":old_task,"role":"A",
            "status":"UNAPPROVED_LOCAL_CANDIDATES_NOT_LIBRARY_PASS",
            "files":files
        }),encoding="utf-8")
        gv=self.root/"text_roi_batches/generated_visible"; gv.mkdir(parents=True)
        (gv/f"{old_task}.json").write_text(json.dumps({
            "task_id":old_task,"role":"A","distinct_generated_images":5,
            "verification_method":"TEST","status":"IMAGES_VISIBLE_NOT_LIBRARY_PROOF",
            "export_status":"EXISTING_CANDIDATES_VERIFIED"
        }),encoding="utf-8")

        class Page:
            url=target
            async def evaluate(self,*args,**kwargs):
                raise AssertionError("persisted evidence should skip source DOM")
        async def fake_verify(*args,**kwargs):
            return None,"PROJECT_LIBRARY_HASH_MATCH_INCOMPLETE:0/5:SCANNED=500:LOAD_ERRORS=0"

        import project_library_gate
        with patch.object(project_library_gate,"verify_project_library_images",new=fake_verify):
            can_continue,status=asyncio.run(text_roi_queue.inspect_slot("A",Page(),self.root))
        self.assertTrue(can_continue)
        self.assertEqual(status,"FIVE_IMAGE_BATCH_RETRY_STAGED")
        st=json.loads((self.root/"text_roi_batches/A_state.json").read_text())
        self.assertEqual(st["active"]["task_id"],old_task+"-R1")
        self.assertEqual(st["active"]["ordinals"],[1,2,3,4,5])
        self.assertEqual(st["next_ordinal"],1)
        self.assertEqual(st["completed_files"],0)
        self.assertFalse((ev/f"{old_task}.json").exists())
        self.assertFalse((gv/f"{old_task}.json").exists())
        qroot=self.root/"text_roi_batches/quarantine"/old_task
        self.assertTrue((qroot/"export_evidence.json").is_file())
        self.assertTrue((qroot/"generated_visible.json").is_file())
        for row in files:
            self.assertFalse((outdir/row["name"]).exists())
            self.assertTrue((qroot/"candidate_outputs"/row["name"]).is_file())

    def test_stale_generated_five_is_retried_before_library_scan(self):
        items=[]
        for i in range(5):
            name=f"Q231_Stale_{i}.png"
            path=self.image_path.with_name(name)
            Image.new("RGBA",(100+i,40),(0,0,0,0)).save(path)
            items.append({
                **self.item,
                "id":f"Q231_Stale_{i}",
                "role":"A",
                "queue_index":"231",
                "imagegen_input_png":name,
                "imagegen_input_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "english":f"Old {i}",
                "korean":f"오래됨 {i}",
            })
        self.write_manifest(items)
        binding,error=text_roi_queue.next_binding("A",self.root)
        self.assertIsNone(error)
        old_task=binding["task_id"]
        text_roi_queue.stage_submission("A",old_task,self.root)
        target="https://chatgpt.com/c/stale-five"
        text_roi_queue.record_chat_url("A",old_task,target,self.root)

        st=json.loads((self.root/"text_roi_batches/A_state.json").read_text())
        st["active"]["created_at"]="2026-10-19T00:00:00+00:00"
        (self.root/"text_roi_batches/A_state.json").write_text(json.dumps(st),encoding="utf-8")

        sent=self.root/"sent"; sent.mkdir(parents=True,exist_ok=True)
        (sent/f"A_{old_task}.json").write_text(json.dumps({
            "status":"CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS",
            "task_id":old_task,"role":"A",
            "tiles":[{"filename":x["filename"]} for x in binding["tiles"]]
        }),encoding="utf-8")

        outdir=self.root/"text_roi_batches/candidate_outputs/A"
        outdir.mkdir(parents=True)
        files=[]
        for item in binding["items"]:
            binary=(b"stale-"+item["filename"].encode())*20
            name=item["output_filename"]
            (outdir/name).write_bytes(binary)
            files.append({"name":name,"sha256":hashlib.sha256(binary).hexdigest()})
        ev=self.root/"text_roi_batches/export_evidence"; ev.mkdir(parents=True)
        (ev/f"{old_task}.json").write_text(json.dumps({
            "task_id":old_task,"role":"A",
            "status":"UNAPPROVED_LOCAL_CANDIDATES_NOT_LIBRARY_PASS",
            "files":files
        }),encoding="utf-8")
        gv=self.root/"text_roi_batches/generated_visible"; gv.mkdir(parents=True)
        (gv/f"{old_task}.json").write_text(json.dumps({
            "task_id":old_task,"role":"A","distinct_generated_images":5,
            "verification_method":"TEST","status":"IMAGES_VISIBLE_NOT_LIBRARY_PROOF",
            "export_status":"EXISTING_CANDIDATES_VERIFIED"
        }),encoding="utf-8")

        class Page:
            url=target
            async def evaluate(self,*args,**kwargs):
                raise AssertionError("stale generated evidence must avoid source DOM")
        async def should_not_verify(*args,**kwargs):
            raise AssertionError("stale batch must be restaged before Library scan")

        import project_library_gate
        with patch.object(project_library_gate,"verify_project_library_images",new=should_not_verify):
            can_continue,status=asyncio.run(text_roi_queue.inspect_slot("A",Page(),self.root))
        self.assertTrue(can_continue)
        self.assertEqual(status,"FIVE_IMAGE_BATCH_RETRY_STAGED")
        st=json.loads((self.root/"text_roi_batches/A_state.json").read_text())
        self.assertEqual(st["active"]["task_id"],old_task+"-R1")
        self.assertEqual(st["next_ordinal"],1)
        self.assertEqual(st["completed_files"],0)
        self.assertEqual(st["quarantined"][-1]["retry_reason"],
                         "STALE_GENERATED_NOT_LIBRARY_VERIFIED")

    def test_two_roles_do_not_share_state(self):
        b = dict(self.item, id="Q104_Second_Text", role="B", imagegen_input_png="Q104_OutRunModeB.png")
        dest = self.image_path.with_name(b["imagegen_input_png"])
        dest.write_bytes(self.image_path.read_bytes())
        self.write_manifest([self.item,b])
        aa,ea = text_roi_queue.next_binding("A",self.root)
        bb,eb = text_roi_queue.next_binding("B",self.root)
        self.assertIsNone(ea);self.assertIsNone(eb)
        self.assertNotEqual(aa["task_id"],bb["task_id"])
        self.assertEqual(aa["expected_images"],1)
        self.assertEqual(bb["expected_images"],1)


if __name__ == "__main__":
    unittest.main()
