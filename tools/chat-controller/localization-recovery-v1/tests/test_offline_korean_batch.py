#!/usr/bin/env python3
"""Fast pure-local regressions for TEST_ONLY Korean DDS batch renderer."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import numpy as np

HERE=Path(__file__).resolve().parent
MOD=HERE.parent/"offline_korean_batch.py"
if not MOD.is_file():
    MOD=HERE/"outrun_offline_all_sources_20261102.py"
spec=importlib.util.spec_from_file_location("offline_korean_batch",MOD)
batch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)

class TestOfflineKoreanBatch(unittest.TestCase):
    def test_path_gate(self):
        self.assertEqual(str(batch.verify_path("textures/load/spr/demo.dds")),
                         "textures/load/spr/demo.dds")
        for bad in ("../escape.dds","/tmp/evil.dds","textures/load/../../evil.dds",
                    "textures/other/demo.dds","textures/load/demo.exe"):
            with self.assertRaises(ValueError):
                batch.verify_path(bad)

    def test_orientation(self):
        self.assertEqual(batch.source_orientation("Q012_BASE_READABLE_NORMAL.png"),"NORMAL")
        self.assertEqual(batch.source_orientation("Q054_BASE_READABLE_FLIPY.png"),"FLIPY")
        with self.assertRaises(ValueError):
            batch.source_orientation("Q054_BAD.png")

    def test_rgba_roundtrip_flip_and_mips(self):
        image=Image.new("RGBA",(16,8),(32,101,234,176))
        image.putpixel((0,0),(253,44,28,255))
        with tempfile.TemporaryDirectory() as t:
            for direction in ("NORMAL","FLIPY"):
                for mips in (1,3):
                    dds=batch.encode_rgba_dds(image,direction,mips)
                    p=Path(t)/(direction+str(mips)+".dds")
                    p.write_bytes(dds)
                    with Image.open(p) as result:
                        expected=image if direction=="NORMAL" else image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                        self.assertEqual(result.format,"DDS")
                        self.assertEqual(result.size,image.size)
                        self.assertTrue(np.array_equal(np.asarray(result.convert("RGBA")),np.asarray(expected)))
                    self.assertEqual(int.from_bytes(dds[28:32],"little"),mips)

    def test_sha_bound_render_roi_outside_unchanged(self):
        image=Image.new("RGBA",(128,64),(0,0,0,0))
        entries=[{"id":"Q001_TEST","english":"START","korean":"시작","bbox_xyxy":[10,5,100,55]}]
        output,painted,held,changed,outside=batch.render(image,entries)
        self.assertEqual(len(painted),1)
        self.assertEqual(held,[])
        self.assertGreater(changed,0)
        self.assertEqual(outside,0)
        self.assertEqual(output.getpixel((0,0)),(0,0,0,0))
        self.assertNotEqual(output.getpixel((50,32)),(0,0,0,0))

    def test_explicit_preserve_original_translation_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"transcriptions.jsonl"
            rows=[
                {"index":143,"status":"transcribed_reviewed",
                 "segments":[{"source":"Song title","korean":"Song title"}]},
                {"index":152,"status":"transcribed_reviewed",
                 "segments":[{"source":"PRO.","korean":"PRO."}]},
                {"index":44,"status":"transcribed_reviewed",
                 "segments":[{"source":"WIN","korean":"승리"}]}
            ]
            path.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows))
            self.assertEqual(batch.unchanged_translation_qids(path),{"Q143","Q152"})

    def test_overlap_hold_is_not_a_second_pass(self):
        image=Image.new("RGBA",(200,100),(0,0,0,0))
        rows=[{"id":"first","english":"First","korean":"첫째","bbox_xyxy":[0,0,85,60]},
              {"id":"second","english":"Second","korean":"둘째","bbox_xyxy":[50,20,120,80]}]
        _,painted,held,_,outside=batch.render(image,rows)
        self.assertEqual(len(painted),1)
        self.assertEqual(len(held),1)
        self.assertEqual(held[0]["reason"],"OVERLAPPING_ROI")
        self.assertEqual(outside,0)

if __name__=="__main__":
    unittest.main(verbosity=2)