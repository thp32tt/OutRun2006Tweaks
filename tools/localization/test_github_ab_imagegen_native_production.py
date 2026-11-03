"""A/B ImageGen native DDS integration gates, synthetic fixtures only."""
import importlib.util
import io
import struct
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

SOURCE=Path(__file__).with_name("github_ab_imagegen_native_production.py")
spec=importlib.util.spec_from_file_location("ab_imagegen_gitops",SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fake_dds():
    w,h=256,64
    header=bytearray(128)
    header[:4]=b"DDS "
    for offset,value in ((4,124),(12,h),(16,w),(28,1),(76,32),(80,65),(88,32)):
        struct.pack_into("<I",header,offset,value)
    struct.pack_into("<IIII",header,92,*m.MASKS)
    img=Image.new("RGBA",(w,h),(0,0,0,0))
    ImageDraw.Draw(img).rectangle((8,10,247,43),fill=(240,240,255,255))
    return bytes(header)+img.tobytes("raw","BGRA")

def candidate():
    im=Image.new("RGBA",(256,80))
    d=ImageDraw.Draw(im)
    d.rectangle((20,12,235,65),fill=(20,40,180,255))
    d.rectangle((24,16,231,61),fill=(245,245,250,255))
    b=io.BytesIO()
    im.save(b,format="PNG")
    return b.getvalue()

class ABFirstTest(unittest.TestCase):
    def test_source_native_unchanged_outside_text(self):
        original=fake_dds()
        art=candidate()
        new,preview,details=m.compose_one(
          original,art,{"orientation":"NORMAL","native_ink_box":[8,10,248,44],
                        "readable_source_dimensions":[256,64]})
        self.assertNotEqual(new,original)
        self.assertEqual(new[:128],original[:128])
        self.assertEqual(len(new),len(original))
        self.assertEqual(new[128:128+4*256*8],original[128:128+4*256*8])
        self.assertEqual(details["outside_native_ink_pixel_changes"],0)

    def test_flip_roundtrip(self):
        new,preview,details=m.compose_one(fake_dds(),candidate(),
           {"orientation":"FLIPY","native_ink_box":[8,20,248,54],
            "readable_source_dimensions":[256,64]})
        self.assertEqual(len(new),len(fake_dds()))
        self.assertNotEqual(new,fake_dds())

    def test_no_font_fallback(self):
        text=SOURCE.read_text()
        self.assertNotIn("ImageFont",text)
        self.assertNotIn("truetype",text)
        self.assertNotIn("draw.text(",text)

    def test_archive_path_safety(self):
        self.assertTrue(m.approved_target("textures/load/spr_etc_xst/D6DC1380_256x64.dds"))
        self.assertTrue(m.approved_target("textures/load/PlayStation/spr_a/x.dds"))
        for bad in ("../a.dds","textures/load/a/../x.dds","textures/load/a/x.png",
                    "textures/load/a/evil\\hack.dds","textures/load/random/spr_a/x.dds"):
            self.assertFalse(m.approved_target(bad))

    def test_non_native_dds_held(self):
        broken=bytearray(fake_dds())
        struct.pack_into("<I",broken,28,2)
        with self.assertRaisesRegex(ValueError,"SOURCE_DDS_NON_NATIVE"):
            m.native_rgba(bytes(broken))

    def test_bad_candidate_border(self):
        image=Image.new("RGBA",(200,60),(255,255,255,255))
        b=io.BytesIO()
        image.save(b,format="PNG")
        with self.assertRaisesRegex(ValueError,"CANDIDATE_TOUCHES_BORDER"):
            m.compose_one(fake_dds(),b.getvalue(),
              {"orientation":"NORMAL","native_ink_box":[8,10,248,44],
               "readable_source_dimensions":[256,64]})

if __name__=="__main__":
    unittest.main()
