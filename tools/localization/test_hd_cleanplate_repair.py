import io
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
import hd_cleanplate_repair as m
import hd_cleanplate_flat_background as flat

class RepairTests(unittest.TestCase):
    def test_95_percent_caps_actual_native_ink_not_canvas(self):
        glyph=Image.new("RGBA",(500,200))
        ImageDraw.Draw(glyph).ellipse((30,30,469,169),fill=(255,255,255,255))
        out=m.fit_line95(glyph,(10,20,110,60))
        self.assertLessEqual(out.width,95)
        self.assertLessEqual(out.height,38)
        self.assertAlmostEqual(out.width/out.height,440/140,delta=0.2)
    def test_opaque_rectangle_rejected(self):
        x=Image.new("RGBA",(100,50))
        ImageDraw.Draw(x).rectangle((3,3,96,46),fill=(0,0,0,255))
        b=io.BytesIO();x.save(b,format="PNG")
        with self.assertRaisesRegex(ValueError,"REPAIR_CANDIDATE_OPAQUE_RECTANGLE"):
            m.candidate_no_panel(b.getvalue())
    def test_transparent_candidate_accepted(self):
        x=Image.new("RGBA",(100,50))
        ImageDraw.Draw(x).ellipse((4,6,95,44),fill=(255,255,255,255))
        b=io.BytesIO();x.save(b,format="PNG")
        self.assertIsNotNone(m.candidate_no_panel(b.getvalue())[0].getbbox())
    def test_feedback_sha_and_containment(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"f.json"
            groups={"a":[{"roi_id":"id1","source_dds_sha256":"a"*64,"_bbox":[0,0,100,100]},
                         {"roi_id":"id2","source_dds_sha256":"b"*64,"_bbox":[0,0,100,100]}]}
            p.write_text(json.dumps({"schema":"outrun.hd.cleanplate-feedback.v1","proposals":[
                {"roi_id":"id1","target":"a","source_dds_sha256":"a"*64,"bbox_xyxy":[5,5,90,80]},
                {"roi_id":"id2","target":"a","source_dds_sha256":"b"*64,"bbox_xyxy":[-1,5,90,80]}]}))
            got,n=m.load_refinements(p,groups)
            self.assertEqual(n,1);self.assertEqual(got,{"id1":[5,5,90,80]})
    def test_opaque_flat_cleanplate_restores_only_text_mask(self):
        x=Image.new("RGBA",(160,70),(80,90,100,255))
        d=ImageDraw.Draw(x)
        for off in (35,57,79,101):
            d.rectangle((off,25,off+10,43),fill=(255,255,255,255))
        cand=Image.new("RGBA",(120,50))
        ImageDraw.Draw(cand).ellipse((15,10,104,39),fill=(255,230,40,255))
        raw=io.BytesIO();cand.save(raw,format="PNG")
        clean=x.copy();final=x.copy()
        row={"roi_id":"Q001_"+"a"*16,"english":"GO","korean":"출발","_bbox":[10,10,150,60]}
        rec=flat.trial(x,clean,final,row,raw.getvalue(),m.fit_line95,m.candidate_no_panel)
        self.assertEqual(rec["clean_type"],"EXACT_UNIFORM_OPAQUE_BORDER_BACKGROUND_TEST_ONLY")
        self.assertIsNone(flat.diff_mask(clean,Image.new("RGBA",x.size,(80,90,100,255))).getbbox())
        self.assertEqual(final.getpixel((2,2)),x.getpixel((2,2)))
        self.assertIsNotNone(flat.diff_mask(clean,final).getbbox())
    def test_nonuniform_panel_rejected(self):
        x=Image.new("RGBA",(80,40),(80,90,100,255))
        x.putpixel((1,1),(81,90,100,255))
        with self.assertRaisesRegex(ValueError,"NOT_UNIFORM"):
            flat.flat_source_mask(x)
    def test_family_first(self):
        self.assertLess(m.priority("textures/load/Keyboard/x/FA7BBB13_1024x512.dds"),
                        m.priority("textures/load/x/FF2462BB_1024x512.dds"))

if __name__=="__main__":unittest.main()
