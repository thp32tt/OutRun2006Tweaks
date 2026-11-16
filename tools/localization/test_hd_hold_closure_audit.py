"""Native exact-owner C1 handoff safety tests: NEVER claim game approval."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from hd_hold_closure_audit import verify_pixel_ownership

RID="Q044_0123456789abcdef"

class NativeFullOwnerPixelAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)
        (self.p/"native_masks").mkdir()
        self.source=Image.new("RGBA",(100,45),(0,0,0,0))
        ImageDraw.Draw(self.source).rectangle((10,10,38,28),fill=(250,250,250,255))
        ImageDraw.Draw(self.source).rectangle((70,10,90,29),fill=(0,100,200,255))
        self.owned=Image.new("L",self.source.size,0)
        ImageDraw.Draw(self.owned).rectangle((10,10,38,28),fill=255)
        self.protected=Image.new("L",self.source.size,0)
        ImageDraw.Draw(self.protected).rectangle((70,10,90,29),fill=255)
        self.ambiguous=Image.new("L",self.source.size,0)
        self.edited=Image.new("RGBA",self.source.size,(0,0,0,0))
        ImageDraw.Draw(self.edited).rectangle((12,12,35,26),fill=(255,150,40,255))
        self.ticket={"roi_id":RID,"ambiguous_component_pixels":0,
                     "native_bc3_four_mips_requires_separate_codec_gate":False,
                     "mask_pngs":{k:f"native_masks/{RID}_{k}.png" for k in
                                  ("owned","protected","ambiguous","source")}}
        self.write_all()
    def tearDown(self):
        self.tmp.cleanup()
    def write_all(self):
        for name,im in [("source",self.source),("owned",self.owned),
                        ("protected",self.protected),("ambiguous",self.ambiguous)]:
            im.save(self.p/"native_masks"/f"{RID}_{name}.png")
        b=self.p/f"{RID}_korean_fit_RGBA.png"
        self.edited.save(b)
        self.record={"status":"EDITED_SOURCE_BOUND_PREVIEW_REVIEW_REQUIRED",
                     "edited_transparent_png":b.name,
                     "edited_transparent_sha256":hashlib.sha256(b.read_bytes()).hexdigest()}
    def test_static_gate_accepts_glyph_only_next_c1_not_final(self):
        self.assertEqual(verify_pixel_ownership(self.ticket,self.record,self.p,self.p),
                         "READY_FOR_C1_STATIC_SOURCE_OWNER_TEST_ONLY")
    def test_near_protected_art_never_passes(self):
        ImageDraw.Draw(self.edited).rectangle((69,12,72,22),fill=(255,0,0,255))
        self.write_all()
        self.assertEqual(verify_pixel_ownership(self.ticket,self.record,self.p,self.p),
                         "TRANSLATED_INK_TOUCHES_FOREIGN_SOURCE")
    def test_ambiguous_never_passes(self):
        self.ticket["ambiguous_component_pixels"]=1
        self.assertEqual(verify_pixel_ownership(self.ticket,self.record,self.p,self.p),
                         "AMBIGUOUS_NATIVE_SOURCE_EXISTS")
    def test_bc3_quarantined_even_if_geometry_safe(self):
        self.ticket["native_bc3_four_mips_requires_separate_codec_gate"]=True
        self.assertEqual(verify_pixel_ownership(self.ticket,self.record,self.p,self.p),
                         "BC3_MIP_NATIVE_CODEC_GATE_PENDING")
    def test_candidate_sha_conflicts_fail_closed(self):
        self.record["edited_transparent_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"SHA_CONFLICT"):
            verify_pixel_ownership(self.ticket,self.record,self.p,self.p)

if __name__=="__main__":
    unittest.main()
