#!/usr/bin/env python3
"""No-Docker/no-network startup interlock tests for controlled Korean automation."""
from __future__ import annotations
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
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.policy = HERE / "v2_docker_policy.json"
        self.env = {
            "AUTO_SEND":"true",
            "OUTRUN_KR_V2_PHASE":"F2",
            "OUTRUN_KR_V2_NO_SEND":"false",
            "OUTRUN_A_TILE_BATCH_QUEUE":"false",
            "OUTRUN_AB_BATCH_QUEUE":"false",
            "OUTRUN_AB_TEXT_ROI_QUEUE":"true",
            "OUTRUN_ROI_BRIDGE_ENABLED":"true",
            "OUTRUN_KR_V2_AUTO_GENERATE":"true",
            "OUTRUN_KR_V2_AUTO_COMPOSE":"false",
            "OUTRUN_KR_V2_AUTO_DEPLOY":"false",
            "OUTRUN_A_SINGLE_SMOKE_TASK_ID":"",
        }

    def gate(self, **change):
        return g.gate(dict(self.env, **change), self.policy, self.root)

    def test_controlled_auto_allowed(self):
        self.assertEqual(self.gate(), (True, "CONTROLLED_NATIVE_ROI_IMAGEGEN_ACTIVE", "F2"))

    def test_manual_no_send_allowed(self):
        env = dict(self.env,
                   AUTO_SEND="false",
                   OUTRUN_AB_TEXT_ROI_QUEUE="false",
                   OUTRUN_ROI_BRIDGE_ENABLED="true",
                   OUTRUN_KR_V2_AUTO_GENERATE="false",
                   OUTRUN_KR_V2_NO_SEND="true",
                   OUTRUN_KR_V2_PHASE="PAUSED")
        self.assertEqual(g.gate(env, self.policy, self.root), (True, "MANUAL_NO_SEND", "PAUSED"))

    def test_legacy_paths_rejected(self):
        self.assertIn("LEGACY_TILE_QUEUE", self.gate(OUTRUN_A_TILE_BATCH_QUEUE="true")[1])
        self.assertIn("LEGACY_AB_BATCH", self.gate(OUTRUN_AB_BATCH_QUEUE="true")[1])
        self.assertIn("LEGACY_SMOKE", self.gate(OUTRUN_A_SINGLE_SMOKE_TASK_ID="OLD")[1])

    def test_auto_dds_and_deploy_stay_forbidden(self):
        self.assertIn("DDS_COMPOSE", self.gate(OUTRUN_KR_V2_AUTO_COMPOSE="true")[1])
        self.assertIn("GAME_DEPLOY", self.gate(OUTRUN_KR_V2_AUTO_DEPLOY="true")[1])

    def test_partial_auto_activation_rejected(self):
        self.assertIn("PIPELINE_NOT_FULLY_ENABLED", self.gate(OUTRUN_ROI_BRIDGE_ENABLED="false")[1])
        self.assertIn("PIPELINE_NOT_FULLY_ENABLED", self.gate(OUTRUN_AB_TEXT_ROI_QUEUE="false")[1])
        self.assertIn("PIPELINE_NOT_FULLY_ENABLED", self.gate(OUTRUN_KR_V2_AUTO_GENERATE="false")[1])
        self.assertIn("NO_SEND_INTERLOCK", self.gate(OUTRUN_KR_V2_NO_SEND="true")[1])

    def test_invalid_phase_and_bad_policy_rejected(self):
        self.assertEqual(self.gate(OUTRUN_KR_V2_PHASE="BATCH")[1], "INVALID_V2_PHASE")
        self.assertIn("PRODUCTION_PHASE", self.gate(OUTRUN_KR_V2_PHASE="F1")[1])
        fake = self.root / "bad.json"
        fake.write_text(json.dumps({"schema":"fake"}), encoding="utf-8")
        self.assertEqual(g.gate(self.env, fake, self.root)[1], "POLICY_CONTRACT_MISMATCH")

    def test_policy_and_compose_contract(self):
        p = json.loads(self.policy.read_text(encoding="utf-8"))
        self.assertEqual(p["deployment_mode"], "ACTIVE_CONTROLLED_ROI_IMAGEGEN")
        self.assertTrue(p["runtime_activation_approved"])
        self.assertTrue(p["controller_auto_send"])
        self.assertTrue(p["native_roi_dispatch_implemented"])
        self.assertTrue(p["legacy_986_tiles_forbidden"])
        self.assertFalse(p["auto_dds_write"])
        self.assertFalse(p["auto_game_pass"])
        self.assertFalse(p["auto_deploy"])
        self.assertEqual(p["browser_slots"], ["A","B","C1"])

        s = (HERE / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('AUTO_SEND: "true"', s)
        self.assertIn('SCHEDULE_MINUTES: "0,10,30,40"', s)
        self.assertIn('OUTRUN_AB_TEXT_ROI_QUEUE: "true"', s)
        self.assertIn('OUTRUN_A_TILE_BATCH_QUEUE: "false"', s)
        self.assertIn('OUTRUN_AB_BATCH_QUEUE: "false"', s)
        self.assertIn('OUTRUN_KR_V2_AUTO_COMPOSE: "false"', s)
        self.assertIn('OUTRUN_KR_V2_AUTO_DEPLOY: "false"', s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
