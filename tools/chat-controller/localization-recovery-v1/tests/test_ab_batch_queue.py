"""Offline A/B five-image queue tests. No real ChatGPT send or Docker deployment."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

BASE = Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("ab_queue",BASE/"ab_batch_queue.py")
import sys
sys.path.insert(0,str(BASE))
ab=importlib.util.module_from_spec(sp)
sp.loader.exec_module(ab)

CHAT="https://chatgpt.com/g/g-p-test/c/6ace69a0-d1b4-83ee-ae7c-8582d0d6e800"


class StubPage:
    url=CHAT
    def __init__(self, count=5, busy=False, error=None):
        self.count=count;self.busy=busy;self.error=error
    async def evaluate(self, script, params):
        return {"count":self.count,"busy":self.busy,"error":self.error}


class ABTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.rows=[]
        for i in range(1,987):
            name=ab.QUARANTINED if i==130 else f"Q{i:03d}_BASE_READABLE_FLIPY.png"
            self.rows.append({
                "part_filename":name,"queue_indexes":"12","source_dds_path":"test.dds",
                "width":"16","height":"16","x":"0","y":"0",
                "part_png_sha256":"f"*64,
                "orientation":"FLIP_Y_PREVIEW_PER_SPRITE_VERIFY"
            })
        self.originals={"test.dds":{"dds_sha256":"d"*64}}
        self.translation={"12":[("Continue?","계속?","[]")]}
        self.mock_sources=patch.object(ab,"_read_sources",return_value=(self.rows,self.originals,self.translation))
        self.mock_sources.start()
        self.addCleanup(self.mock_sources.stop)
        self.mock_file=patch.object(ab,"_filemap",side_effect=self._filemap)
        self.mock_file.start()
        self.addCleanup(self.mock_file.stop)
        self.mock_recent=patch.object(ab,"_count_recent",return_value=0)
        self.mock_recent.start()
        self.addCleanup(self.mock_recent.stop)
        self.env=patch.dict(os.environ,{"OUTRUN_AB_BATCH_QUEUE":"true"})
        self.env.start()
        self.addCleanup(self.env.stop)

    @staticmethod
    def _filemap(row,ordinal,src,originals):
        name=row["part_filename"]
        return {
            "ordinal":ordinal,"filename":name,"output_filename":name[:-4]+"_k.png",
            "path":"/tmp/fake/"+name, "sha256":"f"*64,
            "source_dds_sha256":"d"*64, "source_dds_path":"test.dds",
            "source_to_upright":"IDENTITY","upright_to_source":"IDENTITY",
            "working_orientation":"READABLE_UPRIGHT",
            "width":16,"height":16,"queue_indexes":"12","x":0,"y":0,
        }

    def test_A_B_exact_index_partition_and_simultaneous_batch(self):
        a,reason=ab.next_binding("A",self.root)
        self.assertIsNone(reason)
        b,reason=ab.next_binding("B",self.root)
        self.assertIsNone(reason)
        self.assertEqual([x["ordinal"] for x in a["items"]],list(range(1,6)))
        self.assertEqual([x["ordinal"] for x in b["items"]],list(range(501,506)))
        self.assertEqual(len(a["paths"]),5)
        self.assertEqual(len(b["paths"]),5)
        self.assertEqual(a["expected_images"],5)
        self.assertIn("입력 이미지 5개 → 서로 분리된 결과 이미지 정확히 5개",a["prompt"])
        self.assertIn("outrun_kor",a["prompt"])
        self.assertIn("_k.png",a["prompt"])
        self.assertIn("상하반전 금지",a["prompt"])
        self.assertIn("콜라주",a["prompt"])
        self.assertNotEqual(a["task_id"],b["task_id"])
        self.assertEqual(ab.SLOTS["A"],(0,10,20,30,40,50))
        self.assertEqual(ab.SLOTS["B"],(5,15,25,35,45,55))

    def test_stage_idempotence_and_submission_is_not_success(self):
        a,_=ab.next_binding("A",self.root)
        redo,reason=ab.next_binding("A",self.root)
        self.assertIsNone(reason)
        self.assertEqual(redo["task_id"],a["task_id"])
        self.assertEqual(ab.stage_submission("A",a["task_id"],self.root),"SUBMITTING")
        self.assertEqual(ab.stage_submission("A",a["task_id"],self.root),"SUBMISSION_ALREADY_ATTEMPTED")
        retry,reason=ab.next_binding("A",self.root)
        self.assertIsNone(retry)
        self.assertIn("BATCH_AWAITING_RESULT_AND_LIBRARY",reason)
        ok,gate=asyncio.run(ab.inspect_slot("A",StubPage(),self.root))
        self.assertFalse(ok)
        self.assertEqual(gate,"SUBMISSION_AMBIGUOUS_NO_RECEIPT")

    def test_quarantine_preserves_original_numbers(self):
        st=ab._state(self.root,"A")
        st["next_ordinal"]=128
        ab._atomic_json(ab.state_path(self.root,"A"),st)
        a,reason=ab.next_binding("A",self.root)
        self.assertIsNone(reason)
        self.assertEqual([x["ordinal"] for x in a["items"]],[128,129,131,132,133])
        current=ab._state(self.root,"A")
        self.assertEqual(current["quarantined"][0]["ordinal"],130)
        self.assertEqual(current["active"]["next_ordinal_after"],134)
        b,_=ab.next_binding("B",self.root)
        self.assertEqual(b["items"][0]["ordinal"],501)

    def test_B_last_partial_batch(self):
        state=ab._state(self.root,"B")
        state["next_ordinal"]=986
        ab._atomic_json(ab.state_path(self.root,"B"),state)
        b,reason=ab.next_binding("B",self.root)
        self.assertIsNone(reason)
        self.assertEqual([v["ordinal"] for v in b["items"]],[986])
        self.assertEqual(b["expected_images"],1)
        self.assertIn("입력 이미지 1개 → 서로 분리된 결과 이미지 정확히 1개",b["prompt"])

    def test_quota_global_hold(self):
        with patch.object(ab,"_count_recent",return_value=75):
            for role in ("A","B"):
                b,reason=ab.next_binding(role,self.root)
                self.assertIsNone(b)
                self.assertEqual(reason,"SHARED_ROLLING_UPLOAD_QUOTA_HOLD")

    def _make_sent(self,task,role):
        d=self.root/"sent"
        d.mkdir(exist_ok=True)
        (d/(role+"_"+task+".json")).write_text(json.dumps({
           "task_id":task,"role":role,
           "tiles":[{"ordinal":i} for i in range(5)],
           "status":"CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS"
        }),encoding="utf-8")

    def test_library_is_mandatory_even_when_five_images_exist(self):
        a,_=ab.next_binding("A",self.root)
        self.assertEqual(ab.stage_submission("A",a["task_id"],self.root),"SUBMITTING")
        self.assertEqual(ab.record_chat_url("A",a["task_id"],CHAT,self.root),"URL_RECORDED")
        self._make_sent(a["task_id"],"A")
        with patch.object(ab,"export_unapproved_k_candidates",new_callable=AsyncMock,return_value="TEST_CANDIDATE_EXPORT"):
            ok,msg=asyncio.run(ab.inspect_slot("A",StubPage(5),self.root))
            self.assertFalse(ok);self.assertEqual(msg,"LIBRARY_OUTRUN_KOR_UNVERIFIED")
            self.assertEqual(ab._state(self.root,"A")["next_ordinal"],1)
            evidence=ab._library_evidence_path(self.root,a["task_id"])
            evidence.parent.mkdir(parents=True,exist_ok=True)
            evidence.write_text(json.dumps({
              "task_id":a["task_id"],"slot":"A","folder":"outrun_kor",
              "verification_method":"manual_ui_verified",
              "folder_visible_label":"outrun_kor",
              "verified_at":"2026-10-14T09:24:00+09:00",
              "library_folder_url":"https://chatgpt.com/library",
              "library_item_ids":["item-"+str(i) for i in range(4)]
            }))
            ok,msg=asyncio.run(ab.inspect_slot("A",StubPage(5),self.root))
            self.assertFalse(ok);self.assertEqual(msg,"LIBRARY_EVIDENCE_INCOMPLETE")
            record=json.loads(evidence.read_text())
            record["library_item_ids"].append("item-4")
            evidence.write_text(json.dumps(record))
            ok,msg=asyncio.run(ab.inspect_slot("A",StubPage(5),self.root))
            self.assertTrue(ok);self.assertEqual(msg,"BATCH_COMPLETE_LIBRARY_VERIFIED")
            st=ab._state(self.root,"A")
            self.assertEqual(st["next_ordinal"],6)
            self.assertEqual(st["completed_files"],5)
            self.assertEqual(st["completed_batches"],1)
            self.assertIsNone(st["active"])
            nb,reason=ab.next_binding("A",self.root)
            self.assertIsNone(reason)
            self.assertEqual([x["ordinal"] for x in nb["items"]],[6,7,8,9,10])

    def test_collage_or_partial_generation_cannot_progress(self):
        a,_=ab.next_binding("A",self.root)
        ab.stage_submission("A",a["task_id"],self.root)
        ab.record_chat_url("A",a["task_id"],CHAT,self.root)
        self._make_sent(a["task_id"],"A")
        for n in (0,1,4,6):
            ok,reason=asyncio.run(ab.inspect_slot("A",StubPage(n),self.root))
            self.assertFalse(ok)
            self.assertIn("IMAGEGEN_OUTPUT_COUNT_MISMATCH",reason)
        self.assertEqual(ab._state(self.root,"A")["next_ordinal"],1)

if __name__ == "__main__":
    unittest.main()