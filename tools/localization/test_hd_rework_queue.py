"""Fail-closed QA workqueue tests; no browser or network."""
import sys
import unittest
import tempfile
from unittest.mock import patch
from PIL import Image, ImageDraw
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
import hd_rework_queue as q
import publish_hd_rework_queue as publisher

class QueueSafety(unittest.TestCase):
 def sample(self):
  return {"schema":"outrun.ab-imagegen-hd-strict.v2",
          "active_roi_total":3, "translated_roi_generated":1,
          "generated":[{"painted":[{"roi_id":"Q200_aaaaaaaaaaaaaaaa"}],
                         "holds":[{"roi_id":"Q044_bbbbbbbbbbbbbbbb","reason":"QA_CANDIDATE_EDGE_CLIP"}]}],
          "holds":[{"roi_ids":["Q044_cccccccccccccccc"],"reason":"ROI_OVERLAP_NEEDS_MANUAL_QA"}],
          "pending_import_holds":[]}
 def test_exact_954_style_accounting(self):
  h,g=q.flatten_holds(self.sample())
  self.assertEqual(len(h),2)
  self.assertEqual(len(g),1)
  self.assertEqual(q.category(h["Q044_bbbbbbbbbbbbbbbb"]),"AB_IMAGE_AND_CLEAN_REWORK")
  self.assertEqual(q.category(h["Q044_cccccccccccccccc"]),"ENGINE_OR_COORDINATE_HOLD")
  self.assertEqual(q.category("QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE"),"ENGINE_OR_COORDINATE_HOLD")
  self.assertEqual(q.category("QA_ORIGINAL_LINE_COUNT_NOT_PRESERVED"),"AB_IMAGE_AND_CLEAN_REWORK")
  # Recreating Hangul glyphs cannot erase English embedded in background alpha.
  # Only verified CLEAN/source segmentation can clear these failures.
  self.assertEqual(q.category("QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT"),"SOURCE_CLEAN_MASK_OR_SEGMENTATION_HOLD")
  self.assertEqual(q.category("OPAQUE_PROTECTED_ART_HOLD"),"SOURCE_CLEAN_MASK_OR_SEGMENTATION_HOLD")
  self.assertEqual(q.category("QA_SOURCE_LINE_LAYOUT_UNVERIFIED"),"SOURCE_CLEAN_MASK_OR_SEGMENTATION_HOLD")
  self.assertEqual(q.category("QA_DOWNSCALE_LOST_GLYPHS"),"AB_IMAGE_AND_CLEAN_REWORK")
  self.assertEqual(q.category("QA_TRANSLATION_TOO_SMALL_TO_READ"),"AB_IMAGE_AND_CLEAN_REWORK")
 def test_no_fake_pass(self):
  x=self.sample()
  x["generated"][0]["holds"][0]["roi_id"]="Q200_aaaaaaaaaaaaaaaa"
  with self.assertRaisesRegex(ValueError,"DUPLICATE_PAINTED_OR_HOLD"):
   q.flatten_holds(x)
 def test_bounded_and_qa_status(self):
  self.assertEqual(q.MAX_ACTIVE,8)
  self.assertEqual(q.MAX_PER_ROLE,4)
  self.assertLess(q.MAX_REF_BYTES,750000)
  self.assertTrue(publisher.TASK_ID.fullmatch("HDRW-A-"+"a"*20))
  self.assertEqual(publisher.BRANCH,"korean-localization-qa-queue-20261104")
 def test_reuse_only_default_never_schedules_new_imagegen(self):
  report=self.sample()
  groups={"test.dds":[{"roi_id":"Q044_bbbbbbbbbbbbbbbb","roles":"A"},
                      {"roi_id":"Q044_cccccccccccccccc","roles":"A"}]}
  with tempfile.TemporaryDirectory() as directory:
   with patch.object(q.atlas,"load_cross",return_value=groups), \
        patch.object(q.atlas,"load_pinned_orientations",return_value={"test.dds":"NORMAL"}):
    result=q.build_queue(directory,report,Path(directory)/"output")
   self.assertEqual(result["tasks"],[])
   self.assertTrue(result["new_imagegen_disabled"])
   self.assertIn("NO_NEW_IMAGEGEN",result["selection_policy"])
   self.assertEqual(result["hold_count"],2)

 def test_unsafe_paths_and_missing_token_rejected(self):
  for s in ("../up","bad?query","/absolute"):
   with self.assertRaises(ValueError):
    publisher.content_path(s)
  with self.assertRaises(ValueError):
   publisher.api("/repos/unused","")
 def test_real_orientation_mapping_string_yields_hd_png_proof(self):
  import github_ab_imagegen_atlas_batch as atlas
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   target="textures/load/spr_fixture/ABCD0001_256x128.dds"
   raw=b"synthetic-sha-pinned-dds"
   src=root/atlas.ORIGINAL/target
   src.parent.mkdir(parents=True)
   src.write_bytes(raw)
   native=Image.new("RGBA",(256,128),(0,0,0,0))
   ImageDraw.Draw(native).rectangle((20,20,65,38),fill=(255,255,255,255))
   row={"source_dds_path":target,"source_dds_sha256":atlas.sha(raw),
        "_bbox":[12,12,77,47]}
   output=root/"proof.png"
   with patch.object(atlas,"native_image",return_value=native):
    proof=q.safe_hd_reference(root,row,{target:"NORMAL"},output)
   self.assertEqual(proof["sha256"],atlas.sha(output.read_bytes()))
   self.assertEqual(proof["source_native_size"],[256,128])
   self.assertTrue(output.is_file())
 def test_rework_is_not_release(self):
  from inspect import getsource
  body=getsource(q.build_queue)
  self.assertIn('"release_approved": False',body)
  self.assertIn('"qa_authority": "NOT_C1_APPROVED_NOT_GAME_APPROVED"',body)

if __name__=="__main__":
 unittest.main()
