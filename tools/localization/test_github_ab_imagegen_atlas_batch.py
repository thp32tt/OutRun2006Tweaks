"""Synthetic A/B ImageGen batch atlas regression gates; no font fallback."""
import importlib.util, io, struct, tempfile, unittest
from unittest.mock import patch
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
   self.assertIsNone(data)
   self.assertFalse(painted)
   self.assertEqual(len(holds),2)
   self.assertTrue(all(h["reason"]=="ROI_OVERLAP_NEEDS_MANUAL_QA" for h in holds))
 def test_overlap_with_unimported_roi_still_holds_existing_candidate(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"candidate.png";make_candidate(p)
   rows=[{"roi_id":"Q044_1234567890abcdef","_bbox":[3,7,101,40],"_candidate_rel":p.name},
    {"roi_id":"Q044_fedcba0987654321","_bbox":[20,7,110,40],"_candidate_rel":"missing.png"}]
   data,_,painted,holds=m.process_atlas(fake_native(),rows,Path(d),"NORMAL")
   self.assertIsNone(data)
   self.assertFalse(painted)
   self.assertEqual({h["roi_id"] for h in holds},{r["roi_id"] for r in rows})
   self.assertTrue(all(h["reason"]=="ROI_OVERLAP_NEEDS_MANUAL_QA" for h in holds))
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
 def test_preview_names_are_unique_per_controller_variant(self):
  base="textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds"
  variants=[base]+[base.replace("textures/load/","textures/load/"+platform+"/") for platform in ("PlayStation","Switch","Xbox")]
  names=[m.preview_name(path) for path in variants]
  self.assertEqual(len(set(names)),len(variants))
  self.assertTrue(all(name.startswith("PREVIEW_39229D64_") and name.endswith(".png") for name in names))
 def test_imported_candidate_rejects_missing_or_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   row={"_candidate_rel":"candidate.png"}
   self.assertFalse(m.imported_candidate(root,row))
   make_candidate(root/"candidate.png")
   self.assertTrue(m.imported_candidate(root,row))
   (root/"alias.png").symlink_to(root/"candidate.png")
   self.assertFalse(m.imported_candidate(root,{"_candidate_rel":"alias.png"}))
 def test_q047_orientation_is_exact_source_pinned(self):
  self.assertEqual(m.ORIENTATIONS["AD720950"],"FLIPY")
 def test_pinned_orientation_accepts_all_104_sha_matching_targets(self):
  import json
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/"localization/automation_inputs").mkdir(parents=True)
   entries=[]
   groups={}
   for i in range(104):
    target=f"textures/load/spr_etc_xst/{i:08X}_256x64.dds"
    dds_sha=f"{i+1:064x}"
    orient="NORMAL" if i==0 else "FLIPY"
    entries.append({"target":target,"orientation":orient,
                    "original_dds_sha256":dds_sha,
                    "original_png_sha256":f"{i+201:064x}"})
    groups[target]=[{"source_dds_sha256":dds_sha}]
   (root/m.SOURCE_PLAN).write_text(json.dumps({"entries":entries}))
   directions=m.load_pinned_orientations(root,groups)
   self.assertEqual(len(directions),104)
   self.assertEqual(directions[entries[0]["target"]],"NORMAL")
   self.assertEqual(directions[entries[1]["target"]],"FLIPY")
   entries[1]["original_dds_sha256"]="0"*64
   (root/m.SOURCE_PLAN).write_text(json.dumps({"entries":entries}))
   with self.assertRaisesRegex(ValueError,"SHA_CONFLICT"):
    m.load_pinned_orientations(root,groups)

 def test_dominant_coarse_roi_held_but_children_can_be_painted(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/"candidate.png";make_candidate(p)
   rows=[
    {"roi_id":"Q044_1234567890abcdef","english":"BANNER",
     "korean":"배너","_bbox":[0,0,240,120],"_candidate_rel":p.name},
    {"roi_id":"Q044_fedcba0987654321","english":"WIN",
     "korean":"승리","_bbox":[3,7,101,40],"_candidate_rel":p.name},
    {"roi_id":"Q044_ffffffffffffffff","english":"LOSE",
     "korean":"패배","_bbox":[127,58,224,90],"_candidate_rel":p.name}]
   original=fake_native()
   binary,_,painted,holds=m.process_atlas(original,rows,root,"NORMAL")
   self.assertIsNotNone(binary)
   self.assertEqual(len(painted),2)
   self.assertEqual(len(holds),1)
   self.assertEqual(holds[0]["reason"],"COARSE_ROI_CONTAINS_OTHER_TEXT_HOLD")
   self.assertEqual(holds[0]["roi_id"],rows[0]["roi_id"])

 def test_dominant_subsets_never_resolve_ambiguous_partial_overlap(self):
  rows=[
   {"roi_id":"a","_bbox":[0,0,240,120]},
   {"roi_id":"b","_bbox":[5,5,80,35]},
   {"roi_id":"c","_bbox":[40,15,120,45]}]
  self.assertEqual(m.dominant_container_holds(rows),{"a"})
  self.assertEqual(m.conflicting_rois(rows[1:]),{"b","c"})

 def test_bc3_exact_failure_quarantines_only_offending_roi(self):
   rows=[{"roi_id":"Q052_1111111111111111","_bbox":[4,4,60,32]},
         {"roi_id":"Q052_2222222222222222","_bbox":[80,4,120,32]}]
   error=m.NativeBC3Hold("QA_BC3_TRANSLATED_COLOR_LOSS")
   error.native_xy=(8,12)
   receipt=(b"native-dds",None,None,[{"roi_id":rows[1]["roi_id"]}],
            [{"roi_id":rows[0]["roi_id"],"reason":"QA_BC3_TRANSLATED_COLOR_LOSS"}])
   with patch.object(m,"process_strict_atlas",side_effect=[error,receipt]) as fn:
    result=m.process_strict_with_bc3_quarantine(fake_native(),rows,Path("."),"NORMAL")
    self.assertEqual(result,receipt)
    self.assertEqual(fn.call_count,2)
    self.assertEqual(fn.call_args.kwargs["excluded_bc3"],{rows[0]["roi_id"]})

 def test_bc3_ambiguous_failure_stays_held(self):
   rows=[{"roi_id":"a","_bbox":[4,4,60,32]},
         {"roi_id":"b","_bbox":[8,8,70,40]}]
   error=m.NativeBC3Hold("QA_BC3_TRANSLATED_COLOR_LOSS")
   error.native_xy=(8,12)
   with patch.object(m,"process_strict_atlas",side_effect=error) as fn:
    with self.assertRaisesRegex(m.NativeBC3Hold,"COLOR_LOSS"):
     m.process_strict_with_bc3_quarantine(fake_native(),rows,Path("."),"NORMAL")
    self.assertEqual(fn.call_count,1)

 def test_bc3_flipy_failure_maps_native_y_to_source_row(self):
   rows=[{"roi_id":"a","_bbox":[4,96,60,125]},
         {"roi_id":"b","_bbox":[80,4,120,32]}]
   error=m.NativeBC3Hold("QA_BC3_TRANSLATED_COLOR_LOSS")
   error.native_xy=(8,15)
   with patch.object(m,"process_strict_atlas",side_effect=[
       error,(b"dd",None,None,[],[])]) as fn:
    m.process_strict_with_bc3_quarantine(fake_native(),rows,Path("."),"FLIPY")
    self.assertEqual(fn.call_args.kwargs["excluded_bc3"],{"a"})

 def test_no_font_regeneration(self):
  s=src.read_text()
  for term in ("ImageFont","truetype(","draw.text(","font_path"):
   self.assertNotIn(term,s)

if __name__=="__main__":unittest.main()
