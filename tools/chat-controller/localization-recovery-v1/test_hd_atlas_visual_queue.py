import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,AsyncMock,MagicMock
import hd_atlas_visual_queue as q
import github_actions_light_controller as light
import github_chat_rework_controller as bridge

def task():
    return {"task_id":"HDAT-"+"a"*24,"source_dds_sha256":"1"*64,"candidate_dds_sha256":"2"*64,
            "target":"textures/load/spr_test/a.dds","native_size":[200,100],"orientation":"NORMAL",
            "roi_count":1,"painted_count":0,"hold_count":1,
            "holds":[{"roi_id":"Q001_"+"a"*16,"english":"GO","korean":"출발","reason":"HOLD","bbox_xyxy":[0,0,100,50]}]}

class AtlasQueueTests(unittest.TestCase):
    def test_pass_cannot_hide_untranslated_hold(self):
        t=task()
        d={"task_id":t["task_id"],"source_dds_sha256":t["source_dds_sha256"],"candidate_dds_sha256":t["candidate_dds_sha256"],"decision":"PASS_PROVISIONAL","reason":"ok"}
        self.assertEqual(q.parse_decision(json.dumps(d),t)["decision"],"REWORK_REQUIRED")
        d["candidate_dds_sha256"]="f"*64
        self.assertIsNone(q.parse_decision(json.dumps(d),t))
    def test_proposals_contained_and_held_only(self):
        t=task()
        d={**{k:t[k] for k in ("task_id","source_dds_sha256","candidate_dds_sha256")},
           "decision":"REWORK_REQUIRED","reason":"wrong bbox","bbox_proposals":[
            {"roi_id":t["holds"][0]["roi_id"],"bbox_xyxy":[-1,0,50,30]},
            {"roi_id":"unrelated","bbox_xyxy":[1,2,50,30]},
            {"roi_id":t["holds"][0]["roi_id"],"bbox_xyxy":[1,2,50,30]}]}
        p=q.parse_decision(json.dumps(d),t)
        self.assertEqual(len(p["bbox_proposals"]),1)
        self.assertEqual(p["bbox_proposals"][0]["bbox_xyxy"],[1,2,50,30])
    def test_no_token_artifact_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"TOKEN_REQUIRED"):q.fetch_evidence({},Path(d),"")
    def test_new_queue_writes_limited_to_visual_receipts(self):
        g=bridge.Github("test")
        for rel,branch in ((q.QROOT+"/latest.json",q.BRANCH),(q.QROOT+"/visual/run-1.json",bridge.ASSETS_BRANCH)):
            with self.assertRaisesRegex(ValueError,"ATLAS_QUEUE_WRITE_SCOPE"):
                g.req(rel,branch,{"content":"test"})
    def test_dispatch_targets_master_and_pinned_sha(self):
        with patch.object(light,"repair_pointer",return_value=None),patch.object(light,"api_call",side_effect=[{"workflow_runs":[]},None]) as call:
            result=light.repair_cycle("a"*40,"token",{})
        self.assertEqual(result["status"],"REPAIR_DISPATCHED")
        self.assertEqual(call.call_args.kwargs["json_body"],{"ref":"master","inputs":{"asset_sha":"a"*40}})
    def test_existing_workflow_or_pointer_dedup(self):
        with patch.object(light,"repair_pointer",return_value={"asset_sha":"a"*40,"run_id":1,"counts":{}}),patch.object(light,"api_call",return_value={"workflow_runs":[]}) as call:
            result=light.repair_cycle("a"*40,"token",{})
        self.assertEqual(result["status"],"REPAIR_QUEUE_PUBLISHED_GPT_FEEDBACK_ON_SCHEDULE")
        self.assertEqual(call.call_count,1)
    def test_active_workflow_not_duplicated(self):
        with patch.object(light,"repair_pointer",return_value=None),patch.object(light,"api_call",return_value={"workflow_runs":[{"status":"in_progress","id":7}]}) as call:
            result=light.repair_cycle("a"*40,"token",{})
        self.assertEqual(result["status"],"REPAIR_RUNNING_OR_QUEUED")
        self.assertEqual(call.call_count,1)

if __name__=="__main__":unittest.main()
