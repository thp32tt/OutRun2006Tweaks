"""Synthetic consumer tests: ChatGPT C1 provisional cannot bypass native DDS QA."""
import json
import tempfile
import unittest
from pathlib import Path
import github_ab_imagegen_atlas_batch as m

class C1OverrideSafety(unittest.TestCase):
 def setup_tree(self,root):
  row={"roi_id":"Q044_aabbccddeeff0000","roles":"A",
       "source_dds_path":"textures/load/spr_test/D6DC1380_256x64.dds",
       "source_dds_sha256":"a"*64,
       "_candidate_rel":"localization/automation_inputs/candidate_outputs/A/old.png"}
  orig=root/row["_candidate_rel"]
  orig.parent.mkdir(parents=True)
  orig.write_bytes(b"old png fixture")
  ident="HDRW-A-"+"b"*20
  approved=root/m.APPROVED
  approved.mkdir(parents=True)
  candidate=b"new png fixture"
  (approved/(ident+".png")).write_bytes(candidate)
  receipt={"schema":"outrun-hd-rework-c1-provisional-v1",
     "task_id":ident,"roi_id":row["roi_id"],"role":"A",
     "source_dds_path":row["source_dds_path"],
     "source_dds_sha256":row["source_dds_sha256"],
     "old_candidate_sha256":m.sha(orig.read_bytes()),
     "candidate_sha256":m.sha(candidate),
     "c1_decision":"C1_PRELIMINARY_PASS_NOT_C3",
     "release_approved":False,"runtime_validation":"UNTESTED"}
  p=approved/(ident+".json")
  p.write_text(json.dumps(receipt))
  return row,receipt,p,approved/(ident+".png")
 def test_only_exact_c1_replaces_candidate_for_strict_reprocessing(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   row,receipt,p,img=self.setup_tree(root)
   groups={row["source_dds_path"]:[row]}
   self.assertEqual(m.apply_c1_preliminary_overrides(root,groups),1)
   self.assertEqual(root/row["_candidate_rel"],img)
 def test_fake_c1_game_approval_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   row,receipt,p,img=self.setup_tree(root)
   receipt["release_approved"]=True
   p.write_text(json.dumps(receipt))
   with self.assertRaisesRegex(ValueError,"C1_RECEIPT_NOT_PINNED"):
    m.apply_c1_preliminary_overrides(root,{row["source_dds_path"]:[row]})
 def test_changed_image_sha_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   row,receipt,p,img=self.setup_tree(root)
   img.write_bytes(b"tamper")
   with self.assertRaisesRegex(ValueError,"C1_NEW_CANDIDATE_SHA_CHANGED"):
    m.apply_c1_preliminary_overrides(root,{row["source_dds_path"]:[row]})
 def test_source_provenance_conflict_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   row,receipt,p,img=self.setup_tree(root)
   receipt["source_dds_sha256"]="0"*64
   p.write_text(json.dumps(receipt))
   with self.assertRaisesRegex(ValueError,"C1_RECEIPT_NOT_PINNED"):
    m.apply_c1_preliminary_overrides(root,{row["source_dds_path"]:[row]})

if __name__=="__main__":
 unittest.main()
