"""Prevent REVIEW_ONLY DX9Ex rollovers from restarting source/CI work."""
import ast
import asyncio
import json
import re
from pathlib import Path
from typing import Optional
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "".join(p.read_text() for p in sorted((ROOT / "src-vr-v2").glob("controller.py.part*")))


def isolated_function(name, *, async_function=False, review_only=True):
    tree = ast.parse(SOURCE)
    kind = ast.AsyncFunctionDef if async_function else ast.FunctionDef
    nodes = [node for node in tree.body if isinstance(node, kind) and node.name == name]
    if len(nodes) != 1:
        raise AssertionError(f"expected one {name}, found {len(nodes)}")
    ns = {
        "json": json,
        "re": re,
        "Optional": Optional,
        "BrowserContext": object,
        "Page": object,
        "DX9EX_REVIEW_ONLY": review_only,
        "MAX_TASK_ATTEMPTS": 3,
        "CONTROLLER_MODE": "conversion",
        "GAME_MOD_CONTEXT": "Authorized offline VR mod",
        "DEVELOPMENT_TARGET_PERCENT": 70,
        "VR_CHECKPOINT_BRANCH": "chat-controller-downloads",
        "LOCALIZATION_EXECUTION_POLICY": "LOCALIZATION",
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<review-only-guard>", "exec"), ns)
    return ns[name]


class DX9ExReviewRolloverGuardTest(unittest.TestCase):
    def test_review_only_rollover_preserves_task_and_excludes_development_commands(self):
        prompt = isolated_function("queue_rollover_prompt")({
            "task_id": "CONVERSION-DX9EX-01076",
            "production_id": "CONVERSION-DX9EX-01076",
            "event_id": "CONVERSION-DX9EX-01076-E005",
            "event_type": "rollover",
            "lane": "DX9EX",
            "branch": "vr-d3d9ex-focus",
            "attempt": 2,
            "chat_rollovers": 2,
            "base_sha": "3961a3760521ff7b57a4648651e6940cc9da2c52",
            "vr_checkpoint_last_path": "tools/chat-controller/checkpoints/vr/CONVERSION-DX9EX-01076/latest.json",
        })
        for required in (
            "ATTEMPT=2/3", "CHAT_ROLLOVER=3", "EVENT_ID=CONVERSION-DX9EX-01076-E005",
            "MODE=DX9EX_REVIEW_ONLY", "CODE_CHANGE=FORBIDDEN",
            "docs/reviews/dx9ex/automation/<TASK_ID>.md",
            "R26+HUD", "RUNTIME_VALIDATION=UNTESTED",
            "source-only CI 재시도 금지",
        ):
            self.assertIn(required, prompt)
        for forbidden in (
            "FEATURE_READY", "DEVELOPMENT_FOCUS_20261017",
            "유효 작업시간 ≥", "docs/automation/runs/ 아래",
            "미완료 구현/실패 수리를 실제 소스",
            "final exact-SHA CI",
        ):
            # A sentence forbidding FEATURE_READY is fine; forbid only affirmative directives.
            if forbidden == "FEATURE_READY":
                self.assertNotIn("FEATURE_READY를 제출해", prompt)
            else:
                self.assertNotIn(forbidden, prompt)

    def test_dx11_retains_implementation_rollover_instructions(self):
        prompt = isolated_function("queue_rollover_prompt")({
            "task_id": "CONVERSION-DX11-00952",
            "lane": "DX11",
            "branch": "vr-dx11-native-r71",
            "attempt": 3,
            "chat_rollovers": 57,
        })
        self.assertIn("FEATURE_READY를 제출해", prompt)
        self.assertIn("DEVELOPMENT_FOCUS_20261017", prompt)
        self.assertNotIn("MODE=DX9EX_REVIEW_ONLY", prompt)

    def test_legacy_ci_wait_reconciles_without_spending_attempt(self):
        fn = isolated_function("recover_missing_gate_run", async_function=True)
        active = {
            "task_id": "CONVERSION-DX9EX-01076",
            "lane": "DX9EX",
            "phase": "WAIT_ACTIONS",
            "attempt": 2,
            "result_sha": "a7e996412ceb6c3ab80bcd3ac75ea956c7a02b82",
            "gate_run": {"id": 123},
            "missing_gate_run_reason": "stale CI timeout",
        }
        action, message = asyncio.run(fn(None, {}, active, None))
        self.assertEqual(action, "review_record_reconcile")
        self.assertIn("docs commit", message)
        self.assertEqual(active["attempt"], 2)
        self.assertEqual(active["phase"], "WAIT_CHAT")
        self.assertEqual(active["validation_mode"], "DX9EX_REVIEW_RECORD_ONLY")
        self.assertNotIn("gate_run", active)
        self.assertNotIn("missing_gate_run_reason", active)
        self.assertEqual(active["result_sha"], "a7e996412ceb6c3ab80bcd3ac75ea956c7a02b82")

    def test_wait_actions_always_invokes_review_verifier_before_source_gate(self):
        node = next(n for n in ast.parse(SOURCE).body
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "conversion_process_lane")
        code = ast.get_source_segment(SOURCE, node)
        segment = code[code.index('if active["phase"] == "WAIT_ACTIONS":'):]
        self.assertLess(segment.index("finalize_dx9ex_review_only_result("),
                        segment.index("github_gate_run("))
        self.assertIn("if review_commit:", segment)


if __name__ == "__main__":
    unittest.main()
