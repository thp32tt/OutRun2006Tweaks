#!/usr/bin/env python3
"""No full game needed: strict B ImageGen conversion unit/guard smoke tests."""
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parent))
import imagegen_b_pipeline as b


class TestBImageGen(unittest.TestCase):
    def make_png(self, mode="RGBA"):
        im=Image.new(mode,(180,50),(0,0,0,0) if mode=="RGBA" else (0,0,0))
        if mode=="RGBA":
            for y in range(10,40):
                for x in range(15,165):
                    im.putpixel((x,y),(255,165,0,255))
        bio=io.BytesIO()
        im.save(bio,format="PNG")
        return bio.getvalue()

    def test_alpha_fit_preserves_nonzero_bounds(self):
        a=b.png_rgba(self.make_png())
        z=b.premul_fit(a,75,18,"contain")
        self.assertLessEqual(z.shape[1],75)
        self.assertLessEqual(z.shape[0],18)
        self.assertGreater(int((z[:,:,3]>0).sum()),0)
        self.assertEqual(z.dtype,np.uint8)

    def test_width_priority_fit(self):
        a=b.png_rgba(self.make_png())
        z=b.premul_fit(a,75,18,"width_priority")
        self.assertEqual(z.shape,(18,75,4))

    def test_missing_true_alpha_rejected(self):
        a=Image.new("RGBA",(40,20),(255,190,0,255))
        bio=io.BytesIO();a.save(bio,format="PNG")
        with self.assertRaisesRegex(ValueError,"no transparency"):
            b.png_rgba(bio.getvalue())

    def test_bbox_one_pixel_overflow_rejected(self):
        self.assertEqual(b.bbox([1,2,10,11],10,11),(1,2,10,11))
        for candidate in [[-1,2,10,11],[0,2,11,11],[0,0,5,12],[4,0,4,10]]:
            with self.assertRaises(ValueError):
                b.bbox(candidate,10,11)

    def test_unpinned_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            target=root/"input.png";target.write_bytes(self.make_png())
            with self.assertRaisesRegex(ValueError,"SHA256"):
                b.bound(root,{"path":"input.png"})
            with self.assertRaisesRegex(ValueError,"escapes repository"):
                b.bound(root,{"path":"../outside.png","sha256":"0"*64})
            blob=b.bound(root,{"path":"input.png","sha256":b.digest(target.read_bytes())})
            self.assertEqual(blob,target.read_bytes())

    def test_dds_header_scope_and_codec_hold(self):
        # Missing DDS or mip chain should fail before any misleading pass.
        for bad in [b"",b"DDS "+bytes(124), b"junk"]:
            with self.assertRaises(ValueError):
                b.dds_rgba_read(bad)

    def test_end_to_end_synthetic_saved_dds_no_approval(self):
        # Small synthetic Atlas A/B source, no real game/semantic PASS claim.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"localization/graphics/role_B/imagegen_requests"
            folder.mkdir(parents=True)
            C2=root/"localization/graphics/plate_library/reviews"
            C2.mkdir(parents=True)
            h,w=32,64
            source=np.zeros((h,w,4),np.uint8)
            source[5:19,10:52]=[255,155,20,255]
            base=Image.fromarray(source[::-1].copy(),"RGBA")
            sourcefile=root/"source.dds"
            base.save(sourcefile,format="DDS")
            baseline=b.dds_rgba_read(sourcefile.read_bytes())
            clean=baseline.copy()
            clean[5:19,10:52]=0
            clean_file=root/"clean.png"
            Image.fromarray(clean,"RGBA").save(clean_file)
            mask=np.zeros((h,w),np.uint8)
            mask[5:19,10:52]=255
            mask_file=root/"mask.png"
            Image.fromarray(mask,"L").save(mask_file)
            gen=Image.new("RGBA",(120,40),(0,0,0,0))
            for y in range(6,34):
                for x in range(8,110):
                    gen.putpixel((x,y),(255,195,5,255))
            genfile=folder/"trial.png"
            gen.save(genfile)
            def ref(p):
                return {"path":str(p.relative_to(root)),"sha256":b.digest(p.read_bytes())}
            review={
               "status":"PLATE_PASS","reviewer":"C2",
               "source_sha256":ref(sourcefile)["sha256"],
               "clean_sha256":ref(clean_file)["sha256"],
               "removal_sha256":ref(mask_file)["sha256"]
            }
            rfile=C2/"approval.json"
            rfile.write_text(json.dumps(review))
            manifest={
              "schema":b.SCHEMA,"role":"B","queue_index":60,"target_text":"최고 기록:",
              "generator":{"provider":"chatgpt-image-generator",
                           "generation_id":"synthetic-test-only-not-real",
                           "prompt":"synthetic fixture only"},
              "source":ref(sourcefile),"official":ref(sourcefile),
              "clean":ref(clean_file),"removal_mask":ref(mask_file),
              "generated":ref(genfile),
              "plate_review":{"status":"PLATE_PASS","ref":ref(rfile)},
              "source_bbox":[10,5,52,19],"placement_bbox":[12,6,50,18],
              "replace_roi":[8,4,54,20],"fit_mode":"contain",
              "output_dir":"localization/graphics/role_B/imagegen_trials/test-fixture"
            }
            mfile=folder/"trial.json"
            mfile.write_text(json.dumps(manifest))
            stats=b.run(root,mfile)
            self.assertEqual(stats["official_promoted"],0)
            self.assertEqual(stats["outside_roi_changed_pixels"],0)
            self.assertEqual(stats["persisted_roundtrip_mismatch"],0)
            self.assertNotEqual(stats["official_sha256"],stats["saved_trial_sha256"])
            dest=root/manifest["output_dir"]
            self.assertTrue((dest/"B_IMAGEGEN_060_UNAPPROVED.dds").exists())
            self.assertTrue((dest/"B_IMAGEGEN_060_SOURCE_CLEAN_OFFICIAL_GENERATED_RAW_100.png").exists())
            self.assertEqual(stats["C2"],"NOT_RUN")

    def test_file_contact_lossless(self):
        src=np.zeros((32,64,4),np.uint8)
        src[3:15,4:28]=[255,180,0,255]
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"compare.png"
            b.save_contact(p,[src,src],(0,0,64,32),128,50,False)
            with Image.open(p) as im:
                self.assertEqual(im.format,"PNG")
                self.assertEqual(im.size,(80,16))
            p2=Path(temp)/"compare_raw.png"
            b.save_contact(p2,[src,src],(0,0,64,32),128,100,True)
            self.assertTrue(p2.exists())


if __name__=="__main__":
    unittest.main()
