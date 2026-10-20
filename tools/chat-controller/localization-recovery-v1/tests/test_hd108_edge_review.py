#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

BASE=Path(__file__).resolve().parents[1]
CROP=BASE/"c_english_crop"
sys.path.insert(0,str(CROP))
spec=importlib.util.spec_from_file_location("ocr_hd108",CROP/"ocr_hd108.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class EdgeReviewTests(unittest.TestCase):
    def test_warning_crop_can_be_rescued_by_safe_expansion(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"src"; out=root/"out"
            src.mkdir(); out.mkdir()
            name="Q051_TEST.png"
            full=Image.new("RGBA",(200,100),(0,0,0,0))
            draw=ImageDraw.Draw(full)
            draw.rectangle([50,30,99,59],fill=(255,255,255,255))
            full.save(src/name)
            source_sha=hashlib.sha256((src/name).read_bytes()).hexdigest()

            folder=out/"Q051_TEST"/"oldwarn"
            folder.mkdir(parents=True)
            crop=full.crop((50,30,100,60))
            crop.save(folder/"english_original_native_crop.png")
            crop_sha=hashlib.sha256((folder/"english_original_native_crop.png").read_bytes()).hexdigest()
            manifest={
                "status":"CROP_TEST_ONLY_REVIEW_REQUIRED",
                "source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
                "source_png":name,
                "source_sha256":source_sha,
                "reference_dds_path":"textures/Q051.dds",
                "reference_dds_sha256":"a"*64,
                "queue_indexes":"051",
                "english":"TEST",
                "bbox_xyxy":[50,30,100,60],
                "source_dimensions":[200,100],
                "crop_dimensions":[50,30],
                "crop_sha256":crop_sha,
                "edge_warning":"ALPHA_TOUCHES_CROP_BORDER_REVIEW",
                "human_review_required":True,
                "runtime_validation":"UNTESTED",
                "old_split_tiles_used":False,
            }
            (folder/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")

            result=mod.review_edge_warnings(max_items=10,src_root=src,out_root=out)
            self.assertEqual(result["reviewed"],1)
            self.assertEqual(result["rescued"],1)
            self.assertEqual(result["held"],0)
            receipt=json.loads((folder/"edge_review_v1.json").read_text())
            self.assertEqual(receipt["status"],"RESCUED_SAFE_EXPANDED_CROP")
            rescued=Path(receipt["rescued_manifest"])
            self.assertTrue(rescued.is_file())
            new=json.loads(rescued.read_text())
            self.assertIsNone(new["edge_warning"])
            self.assertEqual(new["edge_review_version"],mod.EDGE_REVIEW_VERSION)
            self.assertNotEqual(new["bbox_xyxy"],manifest["bbox_xyxy"])

    def test_tampered_warning_crop_is_held(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"src"; out=root/"out"
            src.mkdir(); out.mkdir()
            name="Q051_TEST.png"
            full=Image.new("RGBA",(100,60),(0,0,0,0)); full.save(src/name)
            folder=out/"Q051_TEST"/"oldwarn"; folder.mkdir(parents=True)
            (folder/"english_original_native_crop.png").write_bytes(b"not-the-original-png")
            manifest={
                "status":"CROP_TEST_ONLY_REVIEW_REQUIRED",
                "source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
                "source_png":name,
                "source_sha256":hashlib.sha256((src/name).read_bytes()).hexdigest(),
                "reference_dds_path":"textures/Q051.dds",
                "reference_dds_sha256":"a"*64,
                "queue_indexes":"051","english":"TEST",
                "bbox_xyxy":[10,10,50,30],"source_dimensions":[100,60],
                "crop_sha256":"b"*64,
                "edge_warning":"ALPHA_TOUCHES_CROP_BORDER_REVIEW",
                "old_split_tiles_used":False,
            }
            (folder/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
            result=mod.review_edge_warnings(max_items=10,src_root=src,out_root=out)
            self.assertEqual(result["reviewed"],1)
            self.assertEqual(result["rescued"],0)
            self.assertEqual(result["held"],1)
            receipt=json.loads((folder/"edge_review_v1.json").read_text())
            self.assertEqual(receipt["status"],"EDGE_REVIEW_HOLD")


if __name__=="__main__":
    unittest.main(verbosity=2)
