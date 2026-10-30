"""UW2 C slot must NEVER end on an incremental source commit.

Run: python3 -m unittest tools/chat-controller/v0.4/tests/test_uw2_full_fidelity_loop.py
No browser, game asset, external network, or Playwright dependency required.
"""
import ast
import asyncio
import base64
import datetime
import json
import pathlib
import re
import types
import unittest
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = "".join((ROOT / "src-vr-v2" / f"controller.py.part{i:02d}").read_text()
              for i in range(4))
MODULE = ast.parse(SRC)
NODES = {x.name: x for x in MODULE.body
         if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))}
SHA_A, SHA_B, SHA_C = ("a" * 40, "b" * 40, "c" * 40)
REPO = "thp32tt/ai-dev-lab"
BRANCH = "uw2-web-port"


class Uw2LongRunningTest(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.commit_sha = SHA_B
        self.now = datetime.datetime(2026, 10, 31, 2, 30)
        self.manifest = None
        self.active = {
            "repo": REPO, "branch": BRANCH, "task_id": "CONVERSION-UW2-01608",
            "base_sha": SHA_A, "slot": "C", "phase": "WAIT_CHAT", "attempt": 1,
            "sent_at": self.now.isoformat(),
        }
        self.q = {"completed": [], "active_by_lane": {"C": self.active}}
        self.reg = types.SimpleNamespace(
            slots=[types.SimpleNamespace(name="C", completed_tasks_in_chat=0)])
        self.env = {
            "json": json, "base64": base64, "datetime": datetime.datetime,
            "urllib": types.SimpleNamespace(parse=urllib.parse), "re": re,
            "log": types.SimpleNamespace(warning=lambda *a: None),
            "UW2_ALLOW_FINAL_TERMINAL": False,
            "UW2_PROGRESS_POLL_SECONDS": 60,
            "UW2_GITHUB_REPO": REPO, "UW2_TARGET_BRANCH": BRANCH,
            "UW2_REQUIRED_STAGES": tuple(f"P{i}" for i in range(10)),
            "UW2_FULL_GAME_ACCEPTANCE_PATH": "uw2-web/docs/ORIGINAL_FULL_GAME_ACCEPTANCE.json",
            "_parse_iso": lambda x: datetime.datetime.fromisoformat(x) if x else None,
            "github_branch_head": lambda b, repo=None: SHA_C,
            "github_find_task_commit": lambda b, task, repo=None: {
                "sha": self.commit_sha, "message": "[AUTO:CONVERSION-UW2-01608] implement"},
            "github_api_json": self.api,
            "save_queue_state": lambda q: self.events.append("saved"),
            "write_runtime": lambda **kw: self.events.append(kw.get("status")),
            "load_registry": lambda now: self.reg,
            "save_registry": lambda reg: self.events.append("reg_saved"),
        }
        for name in ("uw2_full_game_acceptance_verdict",
                     "uw2_finalize_full_game", "uw2_process_lane"):
            fn = NODES[name]
            program = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
            exec(compile(program, "<uw2-tested>", "exec"), self.env)

    def api(self, url):
        self.assertIn("/repos/" + REPO + "/", url)
        if "/contents/" in url:
            if not self.manifest:
                raise RuntimeError("missing final acceptance")
            return {"content": base64.b64encode(
                json.dumps(self.manifest).encode("utf-8")).decode("ascii")}
        if "/compare/" in url:
            return {"status": "ahead", "behind_by": 0}
        if "/commits/" in url:
            return {"files": [{"filename": "uw2-web/web/app.js"},
                              {"filename": "uw2-web/tests/boot-sequence.test.mjs"}]}
        raise AssertionError(url)

    def poll(self, seconds=0):
        asyncio.run(self.env["uw2_process_lane"](
            self.q, self.active, self.now + datetime.timedelta(seconds=seconds)))

    def test_partial_source_commit_never_releases_c(self):
        self.poll()
        self.assertEqual(self.active["phase"], "WAIT_CHAT")
        self.assertIsNone(self.active["terminal"])
        self.assertEqual(self.active["uw2_material_commits_seen"], 1)
        self.assertEqual(self.q["completed"], [])
        self.assertEqual(self.reg.slots[0].completed_tasks_in_chat, 0)

        self.poll(70)
        self.assertEqual(self.active["uw2_material_commits_seen"], 1)
        self.commit_sha = "d" * 40
        self.poll(140)
        self.assertEqual(self.active["uw2_material_commits_seen"], 2)
        self.assertEqual(self.active["task_id"], "CONVERSION-UW2-01608")
        self.assertEqual(self.active["phase"], "WAIT_CHAT")

    def test_complete_flag_without_original_evidence_does_not_stop(self):
        self.poll()
        self.env["UW2_ALLOW_FINAL_TERMINAL"] = True
        self.poll(70)
        self.assertEqual(self.active["phase"], "WAIT_CHAT")
        self.assertEqual(self.q["completed"], [])

    def test_full_game_requires_all_p0_p9_and_explicit_acceptance(self):
        self.poll()
        self.env["UW2_ALLOW_FINAL_TERMINAL"] = True
        manifest = {
            "schema_version": 1, "status": "FULL_GAME_ACCEPTED",
            "target_repo": REPO, "target_branch": BRANCH,
            "validated_source_sha": SHA_B, "reviewer_acceptance": "APPROVED",
            "original_dos_differential": "PASS", "six_playable_campaigns": "PASS",
            "all_scenarios_endings": "PASS", "save_load_bit_exact": "PASS",
            "graphics_audio_input_parity": "PASS", "browser_e2e": "PASS",
            "stages": {f"P{i}": {"status": "PASS",
                                "evidence_path": f"uw2-web/docs/p{i}.json"}
                       for i in range(10)},
        }
        self.manifest = manifest
        del manifest["stages"]["P9"]
        self.poll(70)
        self.assertEqual(self.active["phase"], "WAIT_CHAT")
        manifest["stages"]["P9"] = {
            "status": "PASS", "evidence_path": "uw2-web/docs/p9.json"}
        self.poll(140)
        self.assertEqual(self.active["phase"], "DONE")
        self.assertEqual(self.active["terminal"], "PASS")
        self.assertEqual(self.reg.slots[0].completed_tasks_in_chat, 1)
        self.assertEqual(len(self.q["completed"]), 1)


if __name__ == "__main__":
    unittest.main()
