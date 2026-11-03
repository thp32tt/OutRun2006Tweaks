#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00338/F105."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation86ControlFlowTests(unittest.TestCase):
    def test_exact_prefix_and_cut_edge_are_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_86_PREFIX_END_RVA = 0x001837D5",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_86_INCOMPLETE_RVA = 0x001837D5",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_86_INCOMPLETE_BYTES = bytes.fromhex("ff 35 5c bc")',
            SOURCE,
        )
        self.assertIn(
            '(0x001837D3, "75 0f", "jne 0x1837e4")',
            SOURCE,
        )

    def test_direct_control_flow_metadata_is_exact(self):
        self.assertIn("(0x001837B5, 0x001837E1)", SOURCE)
        self.assertIn("(0x001837C4, 0x001837E4)", SOURCE)
        self.assertIn("(0x001837D3, 0x001837E4)", SOURCE)
        self.assertIn("(0x001837B7, 0x0018377D)", SOURCE)
        self.assertIn("(0x001837CB, 0x001837E8)", SOURCE)

    def test_fail_closed_proof_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_86_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_183799_TO_1837D5_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_86_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_86_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
