#!/usr/bin/env python3
"""No-Docker/no-network v2 startup interlock regression tests."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import v2_automation_policy as g

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.ev=self.root/"evidence"
        self.ev.mkdir()
        self.env={"AUTO_SEND":"false","OUTRUN_KR_V2_PHASE":"PAUSED","OUTRUN_KR_V2_NO_SEND":"true",
                  "OUTRUN_A_TILE_BATCH_QUEUE":"false","OUTRUN_AB_BATCH_QUEUE":"false",
                  "OUTRUN_AB_TEXT_ROI_QUEUE":"false","OUTRUN_KR_V2_AUTO_GENERATE":"false",
                  "OUTRUN_KR_V2_AUTO_COMPOSE":"false","OUTRUN_KR_V2_AUTO_DEPLOY":"false"}
        self.policy=HERE/"v2_docker_policy.json"
    def gate(self, **change):
        return g.gate(dict(self.env,**change),self.policy,self.ev)
    def evidence(self, stage, content=b"verified-test-bytes"):
        name=f"{stage}_actual.dds"
        (self.ev/name).write_bytes(content)
        (self.ev/f"{stage}.json").write_text(json.dumps({
            "schema":g.EVIDENCE_SCHEMA,"stage":stage,"decision":"PASS",
            "RUNTIME_VALIDATION":"PASS","reviewer":"human reviewed (test fixture only)",
            "artifact_sha256":{name:hashlib.sha256(content).hexdigest()}
        }),encoding="utf-8")
    def test_paused_default(self):
        self.assertEqual(self.gate(),(True,"PAUSED_NO_SEND_NO_QUEUE","PAUSED"))
    def test_autosend_rejected_even_future_evidence(self):
        for stage in ["F0","F1","F2","F3"]:self.evidence(stage)
        for phase in g.STAGES:
            with self.subTest(phase=phase):
                self.assertIn("AUTOSEND_FORBIDDEN",self.gate(OUTRUN_KR_V2_PHASE=phase,AUTO_SEND="true")[1])
    def test_legacy_and_new_ungated_queues_rejected(self):
        for key in g.FLAGS:
            with self.subTest(key=key):
                self.assertFalse(self.gate(**{key:"true"})[0])
        self.assertIn("SMOKE_SEND_BLOCKED",self.gate(OUTRUN_A_SINGLE_SMOKE_TASK_ID="OLD")[1])
    def test_no_send_interlock_mandatory(self):
        self.assertIn("INTERLOCK_REQUIRED",self.gate(OUTRUN_KR_V2_NO_SEND="false")[1])
    def test_invalid_phase_and_policy(self):
        self.assertEqual(self.gate(OUTRUN_KR_V2_PHASE="BATCH")[1],"INVALID_V2_PHASE")
        fake=self.root/"bad.json";fake.write_text(json.dumps({"schema":"fake"}))
        self.assertEqual(g.gate(self.env,fake,self.ev)[1],"POLICY_CONTRACT_MISMATCH")
    def test_phase_transition_requires_real_prior_stage(self):
        self.assertIn("EVIDENCE_MISSING",self.gate(OUTRUN_KR_V2_PHASE="F1")[1])
        self.evidence("F0")
        self.assertEqual(self.gate(OUTRUN_KR_V2_PHASE="F1")[:2],
                         (True,"MANUAL_REVIEW_PHASE_NO_SEND:F1"))
        self.assertIn("EVIDENCE_MISSING",self.gate(OUTRUN_KR_V2_PHASE="F2")[1])
    def test_tampered_sha_and_traversal_denied(self):
        self.evidence("F0")
        (self.ev/"F0_actual.dds").write_bytes(b"changed")
        self.assertIn("HASH_MISMATCH",self.gate(OUTRUN_KR_V2_PHASE="F1")[1])
        self.evidence("F0")
        p=self.ev/"F0.json"; e=json.loads(p.read_text())
        e["artifact_sha256"]={"../escape.dds":"0"*64}
        p.write_text(json.dumps(e))
        self.assertIn("PATH_UNSAFE",self.gate(OUTRUN_KR_V2_PHASE="F1")[1])
    def test_claimed_pass_without_runtime_proof_denied(self):
        self.evidence("F0")
        p=self.ev/"F0.json"; e=json.loads(p.read_text())
        e["RUNTIME_VALIDATION"]="UNTESTED";p.write_text(json.dumps(e))
        self.assertIn("NOT_ACTUALLY_APPROVED",self.gate(OUTRUN_KR_V2_PHASE="F1")[1])
    def test_docker_defaults(self):
        s=(HERE/"docker-compose.yml").read_text()
        self.assertEqual(s.count('restart: "no"'),2)
        self.assertIn('AUTO_SEND: "false"',s)
        self.assertIn('SCHEDULE_MINUTES: ""',s)
        self.assertIn('OUTRUN_AB_BATCH_QUEUE: "false"',s)
        self.assertIn('OUTRUN_AB_TEXT_ROI_QUEUE: "false"',s)
        self.assertNotIn('      - --loop',s)
        self.assertIn('OUTRUN_V2_RETIRED_C_SALVAGE_DISABLED',s)
        self.assertIn('v2_automation_policy.py',(HERE/"entrypoint.sh").read_text())
        self.assertIn('COPY v2_docker_policy.json',(HERE/"Dockerfile").read_text())
    def test_retired_ab_queue_never_produces_legacy_tiles(self):
        import ab_batch_queue
        import unittest.mock
        with unittest.mock.patch.dict("os.environ", {"OUTRUN_AB_TEXT_ROI_QUEUE":"false", "OUTRUN_AB_BATCH_QUEUE":"true"}):
            binding,reason=ab_batch_queue.next_binding("A", self.root)
        self.assertIsNone(binding)
        self.assertEqual(reason,"HOLD_LEGACY_TILES_RETIRED_TEXT_ROI_QUEUE_REQUIRED")
    def test_policy_false_default(self):
        p=json.loads(self.policy.read_text())
        self.assertFalse(p["v2_batch_sheet_dispatch_implemented"])
        self.assertFalse(p["runtime_activation_approved"])
        self.assertTrue(p["legacy_986_tiles_forbidden"])

if __name__=="__main__":
    unittest.main(verbosity=2)