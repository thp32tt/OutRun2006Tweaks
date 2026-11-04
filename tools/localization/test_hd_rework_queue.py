"""Fail-closed QA workqueue tests; no browser or network."""
import sys
import unittest
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
 def test_unsafe_paths_and_missing_token_rejected(self):
  for s in ("../up","bad?query","/absolute"):
   with self.assertRaises(ValueError):
    publisher.content_path(s)
  with self.assertRaises(ValueError):
   publisher.api("/repos/unused","")
 def test_rework_is_not_release(self):
  from inspect import getsource
  body=getsource(q.build_queue)
  self.assertIn('"release_approved": False',body)
  self.assertIn('"qa_authority": "NOT_C1_APPROVED_NOT_GAME_APPROVED"',body)

if __name__=="__main__":
 unittest.main()
