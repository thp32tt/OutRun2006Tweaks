"""Synthetic A/B ImageGen batch atlas regression gates; no font fallback."""
import importlib.util, io, struct, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw

src=Path(__file__).with_name("github_ab_imagegen_atlas_batch.py")
spec=importlib.util.spec_from_file_location("ab_atlas",src)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fake_native(w=256,h=128,boxes=((8,12,95,32),(132,63,220,84))):
 b=bytearray(128);b[:4]=b"DDS "
 for off,n in ((4,124),(12,h),(16,w),(28,1),(76,32),(80,65),(88,32)):
  struct.pack_into("<I",b,off,n)
 struct.pack_into("<IIII",b,92,*m.MASKS)
 im=Image.new("RGBA",(w,h))
 d=ImageDraw.Draw(im)
 for box in boxes:d.rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(200,230,255,255))
 return bytes(b)+im.tobytes("raw","BGRA")

def make_candidate(p):
 im=Image.new("RGBA",(160,54))
 d=ImageDraw.Draw(im);d.ellipse((18,8,145,44),fill=(32,50,195,255))
 d.ellipse((22,12,141,40),fill=(255,246,230,255))
 im.save(p)

class MultiAtlasTest(unittest.TestCase):
 def test_two_candidates_merge_without_outside_damage(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   a=root/"candidateA.png";b=root/"candidateB.png"
   make_candidate(a);make_candidate(b)
   rows=[{"roi_id":"Q044_1234567890abcdef","english":"LOSE","korean":"패배",
     "_bbox":[3,7,101,40],"_candidate_rel":a.name},
    {"roi_id":"Q044_fedcba0987654321","english":"WIN","korean":"승리",
     "_bbox":[127,58,224,90],"_candidate_rel":b.name}]
   original=fake_native()
   result,preview,painted,holds=m.process_atlas(original,rows,root,"NORMAL")
   self.assertEqual(len(painted),2)
   self.assertEqual(holds,[])
   self.assertEqual(len(result),len(original))
   self.assertEqual(result[:128],original[:128])
   self.assertEqual(preview.getpixel((250,110)),(0,0,0,0))
 def test_overlap_roi_is_held_not_written(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"candidate.png";make_candidate(p)
   rows=[{"roi_id":"Q044_1234567890abcdef","english":"LOSE","korean":"패배",
     "_bbox":[3,7,101,40],"_candidate_rel":p.name},
    {"roi_id":"Q044_fedcba0987654321","english":"WIN","korean":"승리",
     "_bbox":[3,7,101,40],"_candidate_rel":p.name}]
   data,_,painted,holds=m.process_atlas(fake_native(),rows,Path(d),"NORMAL")
   self.assertEqual(len(painted),1)
   self.assertEqual(holds[0]["reason"],"ROI_OVERLAP_NEEDS_MANUAL_QA")
 def test_missing_input_is_held(self):
  with tempfile.TemporaryDirectory() as d:
   rows=[{"roi_id":"Q044_1234567890abcdef","_bbox":[3,7,101,40],
          "_candidate_rel":"candidate_not_imported.png"}]
   binary,_,painted,holds=m.process_atlas(fake_native(),rows,Path(d),"NORMAL")
   self.assertIsNone(binary);self.assertFalse(painted)
   self.assertEqual(holds[0]["reason"],"AB_PNG_NOT_YET_IMPORTED")
 def test_reject_opaque_art(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"candidate.png";make_candidate(p)
   all_opaque=fake_native(256,128,[(3,7,101,40)])
   # Solid opaque source ROI is treated as protected art.
   b=bytearray(all_opaque)
   with Image.open(io.BytesIO(all_opaque)) as im:
    im=im.convert("RGBA");ImageDraw.Draw(im).rectangle((3,7,100,39),fill=(255,255,255,255))
    b[128:]=im.tobytes("raw","BGRA")
   rows=[{"roi_id":"Q044_1234567890abcdef","english":"LOSE","korean":"패배",
     "_bbox":[3,7,101,40],"_candidate_rel":p.name}]
   result,_,painted,holds=m.process_atlas(bytes(b),rows,Path(d),"NORMAL")
   self.assertFalse(painted)
   self.assertEqual(holds[0]["reason"],"OPAQUE_PROTECTED_ART_HOLD")
 def test_safe_paths(self):
  self.assertTrue(m.good_path("textures/load/spr_etc_xst/D6DC1380_256x64.dds"))
  self.assertTrue(m.good_path("textures/load/PlayStation/spr_etc_xst/D6DC1380_256x64.dds"))
  for v in ("../../exfil.dds","textures/load/spr_etc_xst/../bad.dds","textures/load/a/b.png","textures/load/X/spr_a/b.dds"):
   self.assertFalse(m.good_path(v))
 def test_no_font_regeneration(self):
  s=src.read_text()
  for term in ("ImageFont","truetype(","draw.text(","font_path"):
   self.assertNotIn(term,s)

if __name__=="__main__":unittest.main()
