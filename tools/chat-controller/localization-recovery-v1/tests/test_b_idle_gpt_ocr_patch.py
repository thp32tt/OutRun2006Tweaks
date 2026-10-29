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
        self.assertIn('GPT_OCR_RESPONSE_POLL_SECONDS',src)
        self.assertIn('Periodic OCR response poll consumed',src)
        self.assertIn('[data-testid^="conversation-turn-"]',src)
        self.assertIn('[data-message-author-role="assistant"]',src)
        self.assertIn('mono - last_gpt_ocr_poll >= GPT_OCR_RESPONSE_POLL_SECONDS',src)
        # The actual reply must be polled in the lane that sent it.
        self.assertIn('poll_slot = "B" if active.get("ocr_lane") == "C2" else "C1"',src)
        self.assertIn('page = pages.get(poll_slot)',src)
        self.assertIn('protected_slots.add(poll_slot)',src)
        self.assertIn('protected_slots.discard(poll_slot)',src)
        self.assertIn('C1_OCR_C2_LEASE_ACTIVE',src)
        self.assertIn('B_C2_OCR_C1_LEASE_ACTIVE',src)
        producer=src.index('png_binding, png_reason = load_binding(slot.name)')
        fallback=src.index('slot.name == "B" and send_result == "SOURCE_REFERENCE_NOT_BOUND:ROI_ROLE_QUEUE_EMPTY_OR_FINISHED"')
        self.assertLess(producer,fallback)

if __name__=='__main__':
    unittest.main(verbosity=2)