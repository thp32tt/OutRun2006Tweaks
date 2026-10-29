#!/usr/bin/env python3
from __future__ import annotations
import ast, importlib.util, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def load(name):
    p=ROOT/name
    spec=importlib.util.spec_from_file_location(name.replace('.py',''),p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

class BIdleOCRPatchTests(unittest.TestCase):
    def test_build_chain_adds_b_idle_c2_without_stealing_producer_priority(self):
        src=''.join(p.read_text(encoding='utf-8') for p in sorted((ROOT/'src').glob('controller.py.part*')))
        for name in (
            'patch_controller_png_upload.py',
            'patch_controller_c1_slot.py',
            'patch_controller_gpt_chat_ocr.py',
            'patch_controller_b_idle_gpt_ocr.py',
        ):
            src=load(name).patch(src)
        ast.parse(src)
        self.assertIn('# OUTRUN_B_IDLE_GPT_OCR_V1',src)
        self.assertIn('gpt_ocr_next_binding("C1")',src)
        self.assertIn('gpt_ocr_next_binding("C2")',src)
        self.assertIn('slot.name == "B" and send_result == "SOURCE_REFERENCE_NOT_BOUND:ROI_ROLE_QUEUE_EMPTY_OR_FINISHED"',src)
        self.assertIn('B producer empty; sent C2 OCR task',src)
        producer=src.index('png_binding, png_reason = load_binding(slot.name)')
        fallback=src.index('slot.name == "B" and send_result == "SOURCE_REFERENCE_NOT_BOUND:ROI_ROLE_QUEUE_EMPTY_OR_FINISHED"')
        self.assertLess(producer,fallback)

if __name__=='__main__':
    unittest.main(verbosity=2)