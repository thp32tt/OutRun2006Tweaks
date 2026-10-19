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
