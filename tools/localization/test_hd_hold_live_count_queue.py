"""Live HOLD counting and edge lane exclusion from source owner-only proof."""
import csv,json,tempfile,unittest
from pathlib import Path
import hd_hold_retry_pipeline as pipeline

class LiveHoldQueueTests(unittest.TestCase):
    def setup_fixture(self,h=633):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);edited=root/"edits";proof=root/"proof";out=root/"out";state=root/"state"
        for x in (edited,proof,out,state):x.mkdir()
        rid="Q001_0000000000000000"
        shared="a"*64
        (edited/"auto_edit_report.json").write_text(json.dumps({
            "schema":"outrun-hd-existing-pixel-auto-editor-v1",
            "source_report_zip_sha256":shared,"original_hold_count_unchanged":h,
            "release_approved":False,"records":[
                {"roi_id":rid,"lane":"EDGE","status":"EDIT_UNSAFE_HOLD",
                 "hold_reason":"QA_SOURCE_TEXT_BBOX_TOUCHES_ROI_EDGE"}]}))
        (proof/"source_protection_evidence.json").write_text(json.dumps({
            "schema":"outrun-hd-source-protected-component-evidence-v1",
            "source_report_zip_sha256":shared,"source_total_roi":954,
            "source_holds":633,"release_approved":False,
            "tickets":[]}))
        cross=root/"crosswalk.csv"
        with cross.open("w",newline="",encoding="utf-8") as fd:
            writer=csv.DictWriter(fd,fieldnames=["roi_id"])
            writer.writeheader()
            for i in range(954):
                writer.writerow({"roi_id":f"Q001_{i:016x}"})
        return edited,proof,out,cross,state
    def test_633_current_holds_queue_not_frozen_at_640(self):
        ed,pr,out,cross,state=self.setup_fixture()
        result=pipeline.build(ed,pr,out,cross,state,max_tasks=8)
        q=json.loads((out/"queue.json").read_text())
        self.assertEqual(q["hold_count"],633)
        self.assertEqual(q["old_painted_count_invalid_for_release"],321)
        self.assertEqual(q["tasks"],[])
        self.assertEqual(result["failure_reasons"]["EDGE_NEEDS_SEPARATE_SOURCE_REBIND_QA"],1)
        self.assertEqual(result["regeneration_imagegen_tasks_prepared"],0)
        self.assertFalse(q["release_approved"])
    def test_mismatched_source_held_count_never_accepted(self):
        ed,pr,out,cross,state=self.setup_fixture(h=632)
        with self.assertRaisesRegex(ValueError,"NOT_EXACT_SOURCE_TEST_ONLY_EVIDENCE"):
            pipeline.build(ed,pr,out,cross,state,max_tasks=8)

if __name__=="__main__":
    unittest.main()
