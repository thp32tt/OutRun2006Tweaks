"""Verify DX11/DX9Ex grouped-compile policy survives controller prompt generation."""
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def prefix(lane):
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
        "json": json,
        "MAX_TASK_ATTEMPTS": 3,
        "LOCALIZATION_EXECUTION_POLICY": "LOCALIZATION_EXECUTION_POLICY_ONLY",
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(file), "exec"), context)
    return context["queue_dynamic_prefix"]()


class BatchCompilePolicy(unittest.TestCase):
    def test_both_conversion_prompt_files(self):
        for file in ("conversion_dx11.md", "conversion_dx9ex.md"):
            with self.subTest(file=file):
                content = (ROOT / file).read_text(encoding="utf-8")
                self.assertIn("BATCH_COMPILE_POLICY=GROUPED", content)
                self.assertIn("최종 material commit", content)
                self.assertIn("exact-SHA", content)
                self.assertIn("5분", content)
                self.assertIn("30분", content)
                self.assertIn("RUNTIME_VALIDATION=UNTESTED", content)

    def test_dx11_dispatch_injects_batch_rule(self):
        content = prefix("DX11")
        self.assertIn("BATCH_COMPILE_POLICY=GROUPED", content)
        self.assertIn("작은 소스 수정마다", content)
        self.assertIn("최종 material commit", content)
        self.assertIn("exact-SHA", content)

    def test_dx9ex_dispatch_injects_batch_rule(self):
        content = prefix("DX9EX")
        self.assertIn("BATCH_COMPILE_POLICY=GROUPED", content)
        self.assertIn("5분 컨트롤러 GitHub 체크포인트", content)

    def test_no_injection_into_localization(self):
        self.assertNotIn("BATCH_COMPILE_POLICY=GROUPED", prefix("LOCALIZATION_A"))

    def test_no_dxvk_reactivation(self):
        content = prefix("DXVK")
        self.assertNotIn("BATCH_COMPILE_POLICY=GROUPED", content)
        self.assertIn("DXVK 신규 개발·재개·배포·승격은 동결", content)

    def test_every_final_batch_keeps_ci_without_skip(self):
        for lane in ("DX11", "DX9EX"):
            content = prefix(lane)
            self.assertIn("필수 exact-SHA GitHub Actions 전체 검증", content)
            self.assertIn("CI-skip 지시어를 넣지 마", content)
            self.assertIn("RUNTIME_VALIDATION=UNTESTED", content)

    def test_source_syntax(self):
        source = (ROOT / "src-vr-v2" / "controller.py.part00").read_text(encoding="utf-8")
        ast.parse(source)


if __name__ == "__main__":
    unittest.main()