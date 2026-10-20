#!/usr/bin/env python3
"""Offline tests for verified C-native-crop -> A/B ImageGen manifest bridge."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import crop_to_imagegen_queue as bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.croot = self.root / "c"
        self.ig = self.root / "imagegen"
        self.trans = self.root / "transcriptions.jsonl"
        (self.croot / "hd108_outputs").mkdir(parents=True)
        (self.ig / "text_roi_batches").mkdir(parents=True)
        self.trans.write_text(
            json.dumps({"index":51,"status":"transcribed_reviewed",
                        "segments":[{"source":"Total Time","korean":"총 시간"}]},ensure_ascii=False)+"\n"+
            json.dumps({"index":52,"status":"transcribed_reviewed",
                        "segments":[{"source":"Extra Time","korean":"추가 시간"}]},ensure_ascii=False)+"\n",
            encoding="utf-8"
        )

    def make_crop(self, q, english, dds_sha="a"*64, source_sha="b"*64, edge=None, old_tiles=False):
        folder = self.croot / "hd108_outputs" / f"{q}_SOURCE" / hashlib.sha256(english.encode()).hexdigest()[:16]
        folder.mkdir(parents=True)
        crop = folder / "english_original_native_crop.png"
        Image.new("RGBA",(120,40),(255,255,255,128)).save(crop)
        crop_sha = bridge.digest(crop)
        manifest = {
            "status":"TEST_ONLY_UNTESTED_IN_GAME",
            "source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
            "source_png":f"{q}_SOURCE.png",
            "source_sha256":source_sha,
            "reference_dds_path":f"textures/{q}.dds",
            "reference_dds_sha256":dds_sha,
            "english":english,
            "bbox_xyxy":[10,20,130,60],
            "crop_sha256":crop_sha,
            "old_split_tiles_used":old_tiles,
            "edge_warning":edge,
        }
        (folder/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")

    def test_verified_odd_even_crops_become_ab_queue(self):
        self.make_crop("Q051","Total Time")
        self.make_crop("Q052","Extra Time",dds_sha="c"*64,source_sha="d"*64)
        result = bridge.scan_once(self.croot,self.trans,self.ig)
        self.assertEqual(result["added"],2)
        self.assertEqual((result["A"],result["B"]),(1,1))
        manifest=json.loads((self.ig/"text_roi_batches/production_manifest.json").read_text())
        self.assertEqual(manifest["activation"],bridge.ACTIVATION)
        self.assertFalse(manifest["legacy_986_tiles_used"])
        self.assertFalse(manifest["dds_auto_write"])
        self.assertFalse(manifest["game_pass_auto_promote"])
        roles={x["role"] for x in manifest["items"]}
        self.assertEqual(roles,{"A","B"})
        for item in manifest["items"]:
            self.assertEqual(item["status"],"ROI_APPROVED_FOR_IMAGEGEN")
            self.assertEqual(item["source_provenance"],"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG")
            self.assertFalse(item["old_split_tiles_used"])
            p=self.ig/"text_roi_batches/inputs"/item["imagegen_input_png"]
            self.assertTrue(p.is_file())
            self.assertEqual(bridge.digest(p),item["imagegen_input_sha256"])

    def test_duplicate_scan_does_not_requeue(self):
        self.make_crop("Q051","Total Time")
        self.assertEqual(bridge.scan_once(self.croot,self.trans,self.ig)["added"],1)
        self.assertEqual(bridge.scan_once(self.croot,self.trans,self.ig)["added"],0)

    def test_unmatched_edge_or_old_tile_never_admitted(self):
        self.make_crop("Q051","Unknown")
        self.make_crop("Q052","Extra Time",dds_sha="c"*64,source_sha="d"*64,edge="REVIEW")
        folder=self.croot/"hd108_outputs"/"Q053_SOURCE"/"oldtile"
        folder.mkdir(parents=True)
        crop=folder/"english_original_native_crop.png"
        Image.new("RGBA",(120,40),(255,255,255,128)).save(crop)
        (folder/"manifest.json").write_text(json.dumps({
            "status":"TEST_ONLY_UNTESTED_IN_GAME",
            "source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
            "source_png":"Q053_SOURCE.png","source_sha256":"e"*64,
            "reference_dds_path":"textures/Q053.dds","reference_dds_sha256":"f"*64,
            "english":"Anything","bbox_xyxy":[1,1,121,41],
            "crop_sha256":bridge.digest(crop),"old_split_tiles_used":True,
            "edge_warning":None
        }),encoding="utf-8")
        result=bridge.scan_once(self.croot,self.trans,self.ig)
        self.assertEqual(result["total"],0)

    def test_rebalance_preserves_completed_prefix_and_splits_only_pending_a(self):
        base=self.ig/"text_roi_batches"
        def row(ident,role):
            return {"id":ident,"role":role,"status":"ROI_APPROVED_FOR_IMAGEGEN",
                    "imagegen_input_png":ident+".png","source_key":"k-"+ident}
        data={"schema":bridge.SCHEMA,"activation":bridge.ACTIVATION,
              "items":[row("A1","A"),row("B1","B"),row("A2","A"),row("A3","A"),
                       row("B2","B"),row("A4","A"),row("A5","A"),row("A6","A")]}
        (base/"A_state.json").write_text(json.dumps({
            "version":3,"role":"A","range":[1,99999],"next_ordinal":1,
            "active":{"ordinals":[1,2],"next_ordinal_after":3,
                      "items":[{"region_id":"A1"},{"region_id":"A2"}]},
            "completed_files":0,"completed_batches":0
        }),encoding="utf-8")
        (base/"B_state.json").write_text(json.dumps({
            "version":3,"role":"B","range":[1,99999],"next_ordinal":3,
            "active":None,"completed_files":2,"completed_batches":1
        }),encoding="utf-8")
        summary=bridge.rebalance_existing_pending(data,self.ig)
        self.assertEqual(summary["status"],"REBALANCED")
        self.assertEqual(summary["protected_a"],2)
        self.assertEqual(summary["moved"],2)
        self.assertEqual([x["id"] for x in bridge._approved(data,"A")],["A1","A2","A3","A5"])
        self.assertEqual([x["id"] for x in bridge._approved(data,"B")][:2],["B1","B2"])
        self.assertEqual(len(bridge._approved(data,"B")),4)
        self.assertEqual(bridge.rebalance_existing_pending(data,self.ig)["status"],"REBALANCED")

    def test_old_pilot_state_is_archived_once(self):
        base=self.ig/"text_roi_batches"
        (base/"A_state.json").write_text('{"old":true}\n',encoding="utf-8")
        (base/"production_manifest.json").write_text(
            json.dumps({"schema":"outrun-text-roi-production-v1","items":[{"old":"Q104"}]}),
            encoding="utf-8")
        self.make_crop("Q051","Total Time")
        bridge.scan_once(self.croot,self.trans,self.ig)
        hist=base/"history"
        self.assertTrue((hist/"pre_auto_20261019_A_state.json").is_file())
        self.assertTrue((hist/"pre_auto_20261019_production_manifest.json").is_file())
        self.assertFalse((base/"A_state.json").exists())
        active=json.loads((base/"production_manifest.json").read_text())
        self.assertEqual(active["activation"],bridge.ACTIVATION)
        self.assertEqual(active["item_count"],1)


if __name__=="__main__":
    unittest.main(verbosity=2)
