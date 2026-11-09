"""Ferrari V12: safe parked-car rollover and one-shot original PMT import."""
import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/"src-vr-v2"/"controller.py.part03").read_text()
NODES = {node.name:node for node in ast.parse(SOURCE).body
         if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}

class TestNextCarImport(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,9,14,30,tzinfo=timezone.utc)
        self.seq=["center_console","driver_controls","inner_door","visible_seat","instrument_cluster","dashboard","steering_wheel","cross_cockpit_qa"]
        self.queue={"repository":"thp32tt/imsi1","branch":"main","active_by_slot":{"A":"360spider","C":"f355spider"},
                    "cars":[{"id":"360spider","slot":"A","started_at_utc":"2026-11-09T14:20:00Z","workpack_path":"docs/automation/FERRARI_COCKPIT_WORKPACK_A_360SPIDER.json"},
                            {"id":"f355spider","slot":"C","started_at_utc":"2026-11-09T14:20:00Z","workpack_path":"docs/automation/FERRARI_COCKPIT_WORKPACK_C_F355SPIDER.json"}],
                    "strategy_v3":{"component_sequence":self.seq}}
        self.packs={}
        for slot,car,sha in (("A","360spider","a"*64),("C","f355spider","b"*64)):
            self.packs[slot]={"car_id":car,"slot":slot,"component_order":self.seq,
                        "current_component":"source_bootstrap","dispatches_on_component":0,
                        "input_stage":"SOURCE_IMPORT_PENDING",
                        "original_game_resource_file":f"/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_{'360sp' if slot=='A' else 'f355sp'}_pmt.sz",
                        "original_game_resource_sha256":sha,"original_import_blend_sha256":None,
                        "migration_input_blend_sha256":None,
                        "components":{**{x:{"status":"NOT_STARTED","source_edits_this_phase":0} for x in self.seq},
                                      "source_bootstrap":{"status":"NOT_STARTED","source_edits_this_phase":0}}}
        def api(url):
            if url.endswith("FERRARI16_GEOMETRY_QUEUE.json?ref=main"): payload=self.queue
            elif url.endswith("FERRARI_COCKPIT_WORKPACK_A_360SPIDER.json?ref=main"):payload=self.packs["A"]
            elif url.endswith("FERRARI_COCKPIT_WORKPACK_C_F355SPIDER.json?ref=main"):payload=self.packs["C"]
            else:raise ValueError(url)
            return {"encoding":"base64","content":base64.b64encode(json.dumps(payload).encode()).decode()}
        self.env={
            "CAR_MODEL_GITHUB_REPO":"thp32tt/imsi1","CAR_MODEL_TARGET_BRANCH":"main",
            "github_api_json":api, "base64":base64,"json":json,"urllib":urllib,
            "re":__import__("re"),
            "datetime":datetime,
            "_ferrari_workpack_ssot_cache":{},
            "stable_hash":lambda x:hashlib.sha256(x.encode()).hexdigest()}
        exec(compile(ast.Module(body=[NODES["ferrari_workpack_dispatch_decision"]],type_ignores=[]),"<v12>", "exec"),self.env)
    def dec(self,slot="A",state=None):
        self.env["_ferrari_workpack_ssot_cache"].clear()
        return self.env["ferrari_workpack_dispatch_decision"](slot,state or {},self.now)
    def test_verified_native_source_bootstrap_only_once(self):
        r=self.dec()
        self.assertTrue(r["allow"])
        self.assertTrue(r["bootstrap_only"])
        self.assertEqual(r["component"],"source_bootstrap")
        self.assertFalse(self.dec(state={"last_workpack_fingerprint_sent":r["fingerprint"]})["allow"])
    def test_c_slot_independent(self):
        self.assertEqual(self.dec("C")["vehicle"],"f355spider")
    def test_import_sha_makes_new_geometry_checkpoint(self):
        r=self.dec()
        p=self.packs["A"]
        p["input_stage"]="SOURCE_VERIFIED"
        p["original_import_blend_sha256"]="c"*64
        p["migration_input_blend_sha256"]="c"*64
        p["current_component"]="center_console"
        p["components"]["source_bootstrap"]["status"]="SOURCE_VERIFIED"
        s=self.dec(state={"last_workpack_fingerprint_sent":r["fingerprint"]})
        self.assertTrue(s["allow"])
        self.assertFalse(s.get("bootstrap_only",False))
        self.assertNotEqual(r["fingerprint"],s["fingerprint"])
    def test_import_error_fails_closed(self):
        self.packs["A"]["input_stage"]="SOURCE_IMPORT_BLOCKED"
        with self.assertRaises(ValueError): self.dec()
    def test_wrong_original_path_fails_closed(self):
        self.packs["A"]["original_game_resource_file"]="/tmp/random_fake_car_pmt.sz"
        self.assertFalse(self.dec()["allow"])
    def test_expired_car_does_not_bootstrap(self):
        self.queue["cars"][0]["started_at_utc"]="2026-11-08T04:20:00Z"
        self.assertFalse(self.dec()["allow"])
    def test_initial_p0_pass_allowed_after_breadth(self):
        p=self.packs["A"]
        p["input_stage"]="SOURCE_VERIFIED"
        p["original_import_blend_sha256"]="c"*64
        p["migration_input_blend_sha256"]="c"*64
        p["current_component"]="dashboard"
        for c in self.seq[:self.seq.index("dashboard")]:
            p["components"][c]={"status":"COVERED_PARTIAL_QA","source_edits_this_phase":1}
        self.assertTrue(self.dec()["allow"])
        p["components"]["dashboard"]["status"]="IN_PROGRESS"
        self.assertFalse(self.dec()["allow"])
    def test_cycle_bootstrap_prompt_no_fabricated_blend(self):
        code=ast.get_source_segment(SOURCE,NODES["car_model_simple_cycle"])
        self.assertIn('if admission.get("bootstrap_only")',code)
        self.assertIn("SOURCE_IMPORT_PENDING",code)
        self.assertLess(code.index("ferrari_workpack_dispatch_decision("),code.index("reg = load_registry(now)"))
if __name__=="__main__":unittest.main()