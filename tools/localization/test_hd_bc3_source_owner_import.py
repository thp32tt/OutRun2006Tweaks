"""Source-owned machine canary is TEST_ONLY, never C1/C3 approval."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from hd_bc3_source_owner_import import apply_test_only_source_owner_overrides,BASE,SCHEMA

def h(b):return hashlib.sha256(b).hexdigest()

class OwnerCandidateImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        p=self.root/"localization/automation_inputs/candidate_outputs/A"
        p.mkdir(parents=True)
        self.old=b"ORIGINAL-UNALTERED-A-B-ART"
        (p/"old.png").write_bytes(self.old)
        self.rid="Q044_0123456789abcdef"
        self.new=b"PNG-RGBA-EXISTING-PIXEL-SALVAGE"
        self.row={"roi_id":self.rid,"roles":"A","source_dds_path":"original.dds",
                  "source_dds_sha256":"a"*64,
                  "_bbox":[5,10,25,32],
                  "_candidate_rel":"localization/automation_inputs/candidate_outputs/A/old.png"}
        self.groups={"original.dds":[self.row]}
        p=self.root/BASE
        p.mkdir(parents=True)
        (p/(self.rid+".png")).write_bytes(self.new)
        self.rec={"schema":SCHEMA,"status":"MIP1_INDEX_ONLY_SOURCE_AND_PROTECTED_PASS_TEST_ONLY",
                  "roi_id":self.rid,"role":"A",
                  "release_approved":False,"runtime_validation":"UNTESTED",
                  "visual_qa":"C1_C3_UNTESTED",
                  "source_dds_path":"original.dds","source_dds_sha256":"a"*64,
                  "source_native_bbox_xyxy":[5,10,25,32],
                  "old_candidate_sha256":h(self.old),"candidate_sha256":h(self.new),
                  "native_test_dds_sha256":"b"*64}
        self.recpath=p/(self.rid+".json")
        self.write()
    def tearDown(self):self.tmp.cleanup()
    def write(self):self.recpath.write_text(json.dumps(self.rec))
    def test_exact_candidate_replaces_only_runtime_import_path(self):
        old=self.row["_candidate_rel"]
        self.assertEqual(apply_test_only_source_owner_overrides(self.root,self.groups),1)
        self.assertNotEqual(self.row["_candidate_rel"],old)
        self.assertEqual((self.root/old).read_bytes(),self.old)
        self.assertIn("C1_C3_PENDING",self.row["_candidate_import_mode"])
        self.assertNotIn("PASS",self.row["_candidate_import_mode"])
    def test_fake_approval_rejected(self):
        self.rec["release_approved"]=True;self.write()
        with self.assertRaisesRegex(ValueError,"UNVERIFIED"):
            apply_test_only_source_owner_overrides(self.root,self.groups)
    def test_old_source_png_sha_conflict_rejected(self):
        (self.root/self.row["_candidate_rel"]).write_bytes(b"BAD")
        with self.assertRaisesRegex(ValueError,"SHA_CHANGED"):
            apply_test_only_source_owner_overrides(self.root,self.groups)
    def test_bbox_conflict_rejected(self):
        self.rec["source_native_bbox_xyxy"]=[0,0,50,50];self.write()
        with self.assertRaisesRegex(ValueError,"BBOX_CHANGED"):
            apply_test_only_source_owner_overrides(self.root,self.groups)

if __name__=="__main__":
    unittest.main()
