"""Verify DX11/DX9Ex grouped-compile policy survives controller prompt generation."""
import ast
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def prefix(lane, continuous=False):
    file = ROOT / "src-vr-v2" / "controller.py.part00"
    mod = ast.parse(file.read_text(encoding="utf-8"))
    fn = next(n for n in mod.body if isinstance(n, ast.FunctionDef)
              and n.name == "queue_dynamic_prefix")
    context = {
        "runtime": {
            "queue_task_id": "CONVERSION-" + lane + "-00580",
            "queue_production_id": "CONVERSION-" + lane + "-00580",
            "queue_event_id": "",
            "queue_event_type": "",
            "queue_lane": lane,
            "queue_branch": "vr-d3d9ex-focus" if lane == "DX9EX" else "vr-dx11-native-r71",
            "queue_attempt": 1,
            "queue_failure_context": "",
            "queue_wave_id": "",
            "queue_qa_batch": [],
        },
        "json": json, "re": re,
        "MAX_TASK_ATTEMPTS": 3,
        "DEVELOPMENT_TARGET_PERCENT": 70,
        "VR_CONTINUOUS_30M_ENABLED": continuous,
        "LOCALIZATION_EXECUTION_POLICY": "LOCALIZATION_EXECUTION_POLICY_ONLY",
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(file), "exec"), context)
    return context["queue_dynamic_prefix"]()


class BatchCompilePolicy(unittest.TestCase):
    def test_separate_dx11_implementation_and_dx9ex_review_prompts(self):
        dx11 = (ROOT / "conversion_dx11.md").read_text(encoding="utf-8")
        for marker in ("FEATURE_BASED_DEVELOPMENT", "FEATURE_READY", "exact-SHA",
                       "5분", "30분", "RUNTIME_VALIDATION=UNTESTED"):
            self.assertIn(marker, dx11)
        dx9ex = (ROOT / "conversion_dx9ex.md").read_text(encoding="utf-8")
        for marker in ("MODE=DX9EX_REVIEW_ONLY", "CODE_CHANGE=FORBIDDEN",
                       "docs/reviews/dx9ex/automation/", "RUNTIME_VALIDATION=UNTESTED"):
            self.assertIn(marker, dx9ex)
        self.assertNotIn("FEATURE_BASED_DEVELOPMENT=ON", dx9ex)

    def test_dx11_dispatch_injects_implementation_policy(self):
        content = prefix("DX11")
        self.assertIn("FEATURE_BASED_DEVELOPMENT", content)
        self.assertIn("작은 패치 개수/20분 종료 규칙은 폐기", content)
        self.assertIn("FEATURE_READY", content)
        self.assertIn("exact-SHA", content)

    def test_dx9ex_dispatch_injects_review_only_policy(self):
        content = prefix("DX9EX")
        for marker in ("DX9EX_REVIEW_ONLY=ON", "CODE_CHANGE=NO",
                       "source build Gate를 요구하지 않는다"):
            self.assertIn(marker, content)
        self.assertNotIn("FEATURE_BASED_DEVELOPMENT=ON", content)

    def test_no_injection_into_localization(self):
        self.assertNotIn("FEATURE_BASED_DEVELOPMENT", prefix("LOCALIZATION_A"))

    def test_no_dxvk_reactivation(self):
        content = prefix("DXVK")
        self.assertNotIn("FEATURE_BASED_DEVELOPMENT", content)
        self.assertIn("DXVK 신규 개발·재개·배포·승격은 동결", content)

    def test_dx11_exact_ci_dx9ex_docs_verdict_without_ci_skip(self):
        dx11 = prefix("DX11")
        self.assertIn("exact-SHA Gate", dx11)
        self.assertIn("CI-skip 지시어를 넣지 마", dx11)
        dx9ex = prefix("DX9EX")
        self.assertIn("docs-only commit path", dx9ex)
        self.assertIn("CI-skip 지시어로 우회", dx9ex)
        for content in (dx11, dx9ex):
            self.assertIn("RUNTIME_VALIDATION=UNTESTED", content)

    def test_dx11_development_first_even_in_30m_mode(self):
        for continuous in (False, True):
            content = prefix("DX11", continuous=continuous)
            for marker in ("DEVELOPMENT_FOCUS_20261017=ON",
                           "필수 GitHub Actions 전체 Gate",
                           "RUNTIME_VALIDATION=UNTESTED"):
                self.assertIn(marker, content)
        content = prefix("DX11", continuous=True)
        for marker in ("≥70%", "같은 TASK_ID/FEATURE_ID",
                       "validation-bearing exact SHA", "DXVK 동결"):
            self.assertIn(marker, content)
        prompt = (ROOT / "conversion_continuous_dx11.md").read_text(encoding="utf-8")
        self.assertIn("SOURCE_IMPLEMENTATION_70_PERCENT", prompt)
        self.assertIn("필수 GitHub Actions 전체 Gate", prompt)

    def test_dx9ex_review_only_independent_of_30m_mode(self):
        for continuous in (False, True):
            content = prefix("DX9EX", continuous=continuous)
            self.assertIn("DX9EX_REVIEW_ONLY=ON", content)
            self.assertNotIn("DEVELOPMENT_FOCUS_20261017=ON", content)
            self.assertNotIn("SOURCE_IMPLEMENTATION_70_PERCENT", content)

    def test_development_first_does_not_activate_frozen_lanes(self):
        for lane in ("DXVK", "LOCALIZATION_A"):
            self.assertNotIn("DEVELOPMENT_FOCUS_20261017=ON", prefix(lane, continuous=True))

    def test_source_syntax(self):
        ast.parse((ROOT / "src-vr-v2" / "controller.py.part00").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
