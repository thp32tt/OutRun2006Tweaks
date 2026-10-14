"""Regression tests for ChatGPT multi-image carousel candidate export.

The real ChatGPT B batch shows one generated-image-preview and exactly five
'Show generated image N' buttons. The browser probe is tested against the
actual N100 account separately; these tests cover the exporter and gating.
"""
import asyncio
import base64
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
sp=importlib.util.spec_from_file_location('ab_batch_queue',BASE/'ab_batch_queue.py')
queue=importlib.util.module_from_spec(sp)
sp.loader.exec_module(queue)


class StubCarouselPage:
    def __init__(self, count=5, duplicated=False):
        self.count=count
        self.duplicated=duplicated
        self.calls=0

    async def evaluate(self, js, value):
        self.calls+=1
        if "task=>" in js:
            assert "Show generated image " in js and "button[aria-label^=" in js
            return [
                {"index":i+1,"src":"blob:fake-"+str(0 if self.duplicated else i),
                 "width":100,"height":50}
                for i in range(self.count)
            ]
        assert "async uri=>" in js
        n=int(value.split("-")[-1])
        img=Image.new("RGBA",(100+n,50),(n*15,25,120,255))
        buf=BytesIO();img.save(buf,format="PNG")
        return "data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()


def batch_active():
    return {
        "role":"B","task_id":"OUTRUN-AB-B-0001-20261014","count":5,
        "items":[
            {
                "ordinal":501+i,
                "filename":f"source_{i+1}.png",
                "output_filename":f"source_{i+1}_k.png",
                "width":100,"height":50,
            }
            for i in range(5)
        ]
    }


class CarouselExportTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)

    def test_five_separate_candidates_and_idempotent(self):
        page=StubCarouselPage(5)
        status=asyncio.run(queue.export_unapproved_k_candidates(page,batch_active(),self.root))
        self.assertEqual(status,"LOCAL_CANDIDATES_EXPORTED_UNAPPROVED")
        d=json.loads((self.root/"ab_batches/export_evidence/OUTRUN-AB-B-0001-20261014.json").read_text())
        self.assertEqual(len(d["files"]),5)
        self.assertEqual([x["name"] for x in d["files"]],[f"source_{i}_k.png" for i in range(1,6)])
        self.assertEqual([x["status"] for x in d["files"]],["PENDING_PIXEL_QA"]+["REWORK_DIMENSIONS"]*4)
        self.assertTrue(all(x["chatgpt_library"]=="UNVERIFIED" for x in d["files"]))
        self.assertTrue(all(x["pairing"]=="OUTPUT_ORDER_ONLY_NOT_VISUALLY_VERIFIED" for x in d["files"]))
        self.assertEqual(asyncio.run(queue.export_unapproved_k_candidates(StubCarouselPage(),batch_active(),self.root)),"EXISTING_CANDIDATES_VERIFIED")

    def test_one_preview_not_five_outputs(self):
        with self.assertRaisesRegex(ValueError,"WRONG_GENERATED_IMAGE_COUNT"):
            asyncio.run(queue.export_unapproved_k_candidates(StubCarouselPage(1),batch_active(),self.root))

    def test_duplicate_thumbnails_never_pass(self):
        with self.assertRaisesRegex(ValueError,"WRONG_GENERATED_IMAGE_COUNT"):
            asyncio.run(queue.export_unapproved_k_candidates(StubCarouselPage(5,duplicated=True),batch_active(),self.root))

    def test_exported_files_do_not_implicitly_pass_library_gate(self):
        asyncio.run(queue.export_unapproved_k_candidates(StubCarouselPage(),batch_active(),self.root))
        ok,why=queue._library_confirmed(self.root,batch_active())
        self.assertFalse(ok)
        self.assertEqual(why,"LIBRARY_OUTRUN_KOR_UNVERIFIED")

if __name__=="__main__":
    unittest.main()