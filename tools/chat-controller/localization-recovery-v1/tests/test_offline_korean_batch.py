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

    def test_overlap_trim_repositions_full_korean_phrase(self):
        source=Image.new("RGBA",(200,100),(0,0,0,0))
        rows=[
            {"id":"first","english":"first","korean":"첫째","bbox_xyxy":[0,0,85,60]},
            {"id":"second","english":"second","korean":"둘째","bbox_xyxy":[50,20,150,90]}
        ]
        initial,painted,held,_,outside=batch.render(source,rows)
        self.assertEqual(outside,0)
        self.assertEqual(len(held),1)
        new,done,still,changes,outside=batch.overlap_resolver.resolve(
            source,initial,rows,painted,held,
            make_glyph=batch.sprite.make_glyph,fontfile=batch.sprite.font_path())
        self.assertEqual(len(done),2)
        self.assertEqual(still,[])
        self.assertEqual(outside,0)
        self.assertGreater(changes,0)
        last=done[-1]
        self.assertEqual(last["resolution"],"TRIM_TO_FREE_RECT")
        x0,y0,x1,y1=last["placement_bbox"]
        self.assertGreater(x1-x0,15)
        self.assertGreater(y1-y0,15)
        self.assertTrue(50<=x0<x1<=150 and 20<=y0<y1<=90)
        # New output may only modify free portions of second ROI.
        self.assertTrue(np.array_equal(
            np.asarray(new)[:60,:85],np.asarray(initial)[:60,:85]))
        self.assertTrue(np.array_equal(
            np.asarray(new)[90:,:],np.asarray(source)[90:,:]))

    def test_overlap_full_coverage_remains_hold(self):
        source=Image.new("RGBA",(100,100),(0,0,0,0))
        rows=[{"id":"old","english":"old","korean":"기존","bbox_xyxy":[0,0,90,90]},
              {"id":"inside","english":"inside","korean":"내부","bbox_xyxy":[20,20,45,45]}]
        first=[{"id":"old","bbox":[0,0,90,90]}]
        held=[{"id":"inside","reason":"OVERLAPPING_ROI"}]
        output,accepted,rejected,changed,outside=batch.overlap_resolver.resolve(
            source,source.copy(),rows,first,held,
            make_glyph=batch.sprite.make_glyph,fontfile=batch.sprite.font_path())
        self.assertEqual(len(accepted),1)
        self.assertEqual(rejected[0]["reason"],"OVERLAP_FULLY_COVERED")
        self.assertEqual(changed,0)
        self.assertEqual(outside,0)

    def test_overlap_clipping_partition_has_no_shared_pixels(self):
        box=(10,10,100,100)
        blockers=[(25,25,55,55),(70,40,95,90)]
        pieces=batch.overlap_resolver.subtract_rectangles(box,blockers)
        seen=set()
        for x0,y0,x1,y1 in pieces:
            for x in range(x0,x1):
                for y in range(y0,y1):
                    self.assertNotIn((x,y),seen)
                    self.assertFalse(any(b[0]<=x<b[2] and b[1]<=y<b[3] for b in blockers))
                    seen.add((x,y))
        self.assertEqual(len(seen),8100-900-1250)

if __name__=="__main__":
    unittest.main(verbosity=2)