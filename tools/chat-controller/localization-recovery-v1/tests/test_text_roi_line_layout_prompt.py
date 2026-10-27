"""Regression: preserve original icon line layout in both A/B ROI prompt paths.

No image-generation/API call; extracts the prompt function without importing browser deps.
"""
import ast
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "text_roi_queue.py"


def load_prompt():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_prompt")
    code = compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(SOURCE), "exec")
    namespace = {"LIBRARY_FOLDER": "아웃런 한글화 신규"}
    exec(code, namespace)
    return namespace["_prompt"]


class TestIconLineLayoutPrompt(unittest.TestCase):
    def test_direct_full_hd_icon(self):
        item = {
            "input_mode": "FULL_HD_DIRECT_REFERENCE",
            "bbox_xyxy": [100, 200, 350, 400],
            "reference_width": 4096, "reference_height": 4096,
            "width": 250, "height": 200,
            "english": "Time Attack Mode",
            "korean": "타임 어택 모드",
            "output_filename": "test_k.png",
        }
        p = load_prompt()("A", "TEST", [item], None)
        self.assertIn("원본 2줄을 1줄로, 3줄을 2줄로 합치지 말고", p)
        self.assertIn("같은 수의 줄", p)
        self.assertIn("버튼, 아이콘", p)

    def test_cropped_roi_icon(self):
        item = {
            "input_mode": "ROI_CROP_REFERENCE",
            "filename": "source.png",
            "width": 370, "height": 220,
            "english": "OutRun Mode SPECIAL TOURS",
            "korean": "아웃런 모드 스페셜 투어",
            "output_filename": "source_k.png",
        }
        p = load_prompt()("B", "TEST", [item], None)
        self.assertIn("원본 2줄을 1줄로, 3줄을 2줄로 합치지 말고", p)
        self.assertIn("같은 수의 줄", p)
        self.assertIn("버튼/아이콘", p)


if __name__ == "__main__":
    unittest.main()
