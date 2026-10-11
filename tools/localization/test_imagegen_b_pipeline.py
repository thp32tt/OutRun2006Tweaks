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



def synthetic_media_binding(root, requests_dir, ref, generation_id, target_text):
    """Synthetic fixture only; never real generator attachment evidence."""
    png = requests_dir / "synthetic_english.png"
    im = Image.new("RGBA", (48, 20), (0, 0, 0, 0))
    for x in range(4, 43):
        for y in range(4, 17):
            im.putpixel((x, y), (255, 170, 50, 255))
    im.save(png)
    receipt = requests_dir / "synthetic_tool_input_receipt.json"
    receipt.write_text(json.dumps({
        "tool": "image_gen.text2im", "media_attached": True,
        "source_image_sha256": ref(png)["sha256"],
        "generation_id": generation_id, "target_text": target_text,
        "image_input_field": "referenced_image_ids",
        "input_reference_id": "SYNTHETIC_FIXTURE_NOT_REAL",
    }))
    return {"english_reference": ref(png), "tool_request_receipt": ref(receipt)}


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

    def test_generator_unbound_source_hard_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            req = root / "imagegen_requests"
            req.mkdir()
            def ref(path):
                return {"path": str(path.relative_to(root)),
                        "sha256": b.digest(path.read_bytes())}
            raw = {"generator": {"generation_id": "synthetic-test-only-not-real"},
                   "target_text": "최고 기록:"}
            with self.assertRaisesRegex(ValueError, "SOURCE_REFERENCE_NOT_BOUND"):
                b.require_bound_english_reference(root, raw)
            binding = synthetic_media_binding(root,req,ref,"synthetic-test-only-not-real","최고 기록:")
            raw["source_media_binding"] = binding
            ok = b.require_bound_english_reference(root, raw)
            self.assertEqual(ok["binding_status"],
                             "DECLARED_TOOL_INPUT_RECEIPT_PRESENT_C2_VERIFICATION_REQUIRED")
            raw["generator"]["generation_id"] = "wrong-id"
            with self.assertRaisesRegex(ValueError, "SOURCE_REFERENCE_NOT_BOUND"):
                b.require_bound_english_reference(root, raw)
            raw["generator"]["generation_id"] = "synthetic-test-only-not-real"
            raw["source_media_binding"] = {
                **binding, "english_reference": {**binding["english_reference"], "sha256":"0"*64}}
            with self.assertRaisesRegex(ValueError, "SOURCE_REFERENCE_NOT_BOUND"):
                b.require_bound_english_reference(root, raw)

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

    def _synthetic_saved_dds(self, role, index):
        # Small synthetic Atlas A/B source, no real game/semantic PASS claim.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/f"localization/graphics/role_{role}/imagegen_requests"
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
              "schema":b.SCHEMA if role=="B" else b.C1_SCHEMA,"role":role,"queue_index":index,"target_text":"최고 기록:",
              "generator":{"provider":"chatgpt-image-generator",
                           "generation_id":"synthetic-test-only-not-real",
                           "prompt":"synthetic fixture only"},
              "source":ref(sourcefile),"official":ref(sourcefile),
              "clean":ref(clean_file),"removal_mask":ref(mask_file),
              "generated":ref(genfile),
              "source_media_binding":synthetic_media_binding(root,folder,ref,"synthetic-test-only-not-real","최고 기록:"),
              "plate_review":{"status":"PLATE_PASS","ref":ref(rfile)},
              "source_bbox":[10,5,52,19],"placement_bbox":[12,6,50,18],
              "replace_roi":[8,4,54,20],"fit_mode":"contain",
              "output_dir":f"localization/graphics/role_{role}/imagegen_trials/test-fixture"
            }
            mfile=folder/"trial.json"
            mfile.write_text(json.dumps(manifest))
            stats=b.run(root,mfile)
            self.assertEqual(stats["official_promoted"],0)
            self.assertEqual(stats["outside_roi_changed_pixels"],0)
            self.assertEqual(stats["persisted_roundtrip_mismatch"],0)
            self.assertNotEqual(stats["official_sha256"],stats["saved_trial_sha256"])
            dest=root/manifest["output_dir"]
            self.assertTrue((dest/f"{role}_IMAGEGEN_{index:03d}_UNAPPROVED.dds").exists())
            self.assertTrue((dest/f"{role}_IMAGEGEN_{index:03d}_SOURCE_CLEAN_OFFICIAL_GENERATED_RAW_100.png").exists())
            self.assertEqual(stats["C2"],"NOT_RUN")

    def test_end_to_end_synthetic_saved_dds_no_approval(self):
        self._synthetic_saved_dds("B", 60)
        self._synthetic_saved_dds("C1", 62)

    def test_distinct_b_c1_shard_guards(self):
        self.assertEqual(b.validate_role({"role":"B","schema":b.SCHEMA,"queue_index":60}),("B",60))
        self.assertEqual(b.validate_role({"role":"C1","schema":b.C1_SCHEMA,"queue_index":62}),("C1",62))
        self.assertEqual(b.validate_role({"role":"B","schema":b.SCHEMA,"queue_index":62,"legacy_b_inflight":True}),("B",62))
        for role,schema,index in [("B",b.SCHEMA,62),("C1",b.C1_SCHEMA,60),
                                  ("C1",b.C1_SCHEMA,61),("C1",b.SCHEMA,62),
                                  ("B",b.SCHEMA,True),("A",b.SCHEMA,60)]:
            with self.assertRaises(ValueError):
                b.validate_role({"role":role,"schema":schema,"queue_index":index})

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



class TestBC3ImageGenBridge(unittest.TestCase):
    """Synthetic pixels exercise real DXT5 on-disk bytes, not ImageGen provenance."""

    @staticmethod
    def blank_dds():
        h=bytearray(128)
        h[:4]=b"DDS "
        struct.pack_into("<I",h,4,124)
        struct.pack_into("<I",h,8,0x0002100F)
        struct.pack_into("<II",h,12,64,64)
        struct.pack_into("<I",h,20,4096)
        struct.pack_into("<I",h,28,1)
        struct.pack_into("<I",h,76,32)
        struct.pack_into("<I",h,80,4)
        h[84:88]=b"DXT5"
        struct.pack_into("<I",h,108,0x1000)
        return bytes(h)+b._bc3_block(np.zeros((4,4,4),np.uint8))*256

    def test_bc3_touched_blocks_only(self):
        original=self.blank_dds()
        rgba=b.dds_rgba_read(original)
        rgba[16:24,16:32]=[250,175,50,255]
        new=b.dds_rgba_encode(original,rgba)
        self.assertEqual(new[:128],original[:128])
        self.assertEqual(len(new),len(original))
        self.assertEqual(b.dds_format(new),(64,64,"BC3_DXT5"))
        self.assertGreater(int(b.dds_rgba_read(new)[16:24,16:32,3].sum()),0)
        changed=[i for i in range(256) if original[128+i*16:144+i*16]!=new[128+i*16:144+i*16]]
        self.assertEqual(len(changed),8)
        for i in changed:
            bx,by=i%16,i//16
            self.assertTrue(4<=bx<8 and 10<=by<12)  # DDS RAW is vertically inverted

    def test_bc3_full_pipeline_b_and_c1_unapproved(self):
        for role,index in (("B",60),("C1",102)):
            with self.subTest(role=role),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                req=root/f"localization/graphics/role_{role}/imagegen_requests"
                req.mkdir(parents=True)
                original=b.dds_rgba_read(self.blank_dds())
                original[16:24,16:32]=[255,130,30,255]
                canonical=b.dds_rgba_encode(self.blank_dds(),original)
                S=b.dds_rgba_read(canonical)
                clean=S.copy();clean[16:24,16:32]=0
                mask=np.zeros((64,64),np.uint8)
                mask[16:24,16:32]=255
                generated=np.zeros((24,80,4),np.uint8)
                generated[5:19,5:75]=[255,200,50,255]
                src=root/"source.dds";src.write_bytes(canonical)
                c=root/"clean.png";Image.fromarray(clean,"RGBA").save(c)
                m=root/"removal.png";Image.fromarray(mask,"L").save(m)
                g=req/"synthetic.png";Image.fromarray(generated,"RGBA").save(g)
                r=root/"C2_review.json"
                def ref(p):return {"path":str(p.relative_to(root)),"sha256":b.digest(p.read_bytes())}
                r.write_text(json.dumps({"status":"PLATE_PASS","reviewer":"C2",
                    "source_sha256":ref(src)["sha256"],"clean_sha256":ref(c)["sha256"],
                    "removal_sha256":ref(m)["sha256"]}))
                mf={"schema":b.SCHEMA if role=="B" else b.C1_SCHEMA,"role":role,
                    "queue_index":index,"target_text":"합성 시험","generator":{
                    "provider":"chatgpt-image-generator","generation_id":"TEST-ONLY-NO-REAL-IMAGEGEN",
                    "prompt":"SYNTHETIC FIXTURE ONLY"},
                    "source":ref(src),"official":ref(src),"clean":ref(c),
                    "removal_mask":ref(m),"generated":ref(g),
                    "source_media_binding":synthetic_media_binding(root,req,ref,"TEST-ONLY-NO-REAL-IMAGEGEN","합성 시험"),
                    "plate_review":{"status":"PLATE_PASS","ref":ref(r)},
                    "source_bbox":[8,8,40,32],"placement_bbox":[12,12,36,28],
                    "replace_roi":[8,8,40,32],"output_dir":
                    f"localization/graphics/role_{role}/imagegen_trials/unit-bc3"}
                manifest=req/"synthetic.json";manifest.write_text(json.dumps(mf))
                stats=b.run(root,manifest)
                self.assertEqual(stats["dds_format"],"BC3_DXT5")
                self.assertEqual(stats["saved_protected_pixels_changed"],0)
                self.assertEqual(stats["saved_outside_roi_pixels_changed"],0)
                self.assertEqual(stats["official_promoted"],0)
                self.assertEqual(stats["C2"],"NOT_RUN")
                f=root/mf["output_dir"]/f"{role}_IMAGEGEN_{index:03d}_UNAPPROVED.dds"
                self.assertEqual(b.digest(f.read_bytes()),stats["saved_trial_sha256"])
                self.assertEqual(canonical[:128],f.read_bytes()[:128])
                self.assertEqual(b.dds_format(f.read_bytes())[2],"BC3_DXT5")

    def test_unsupported_bc3_mips_rejected(self):
        d=self.blank_dds()+b"extra"
        with self.assertRaisesRegex(ValueError,"payload"):
            b.dds_rgba_read(d)



if __name__=="__main__":
    unittest.main()
