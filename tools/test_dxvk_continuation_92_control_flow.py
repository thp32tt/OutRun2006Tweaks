#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00360/F117."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation92ControlFlowTests(unittest.TestCase):
    def test_exact_boundary_and_instruction_table_are_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_92_PREFIX_END_RVA = 0x0018394E",
            SOURCE,
        )
        self.assertIn(
            '(0x0018390E, "8b 4d fc", "mov ecx, [ebp-4]")',
            SOURCE,
        )
        self.assertIn(
            '(0x0018394C, "6a 3f", "push 0x3f")',
            SOURCE,
        )

    def test_exact_branches_are_pinned(self):
        self.assertIn("(0x0018392F, 0x00183934)", SOURCE)
        self.assertIn("(0x0018393D, 0x001839D2)", SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_92_CALLS = ()",
            SOURCE,
        )

    def test_inherited_183926_is_resolved_and_new_debt_is_fail_closed(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_92_RESOLVED_PREDECESSOR_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn("0x00183926,", SOURCE)
        self.assertIn(
            "remaining_predecessor_targets == [0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            "unresolved_forward_targets == [0x001839D2, 0x00183B6F]",
            SOURCE,
        )

    def test_proof_consumes_exact_f116_provenance_and_boundaries(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_92_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_18390E_TO_18394E_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            'external_targets == [0x001839D2]',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_18390E_TO_18394E_CONTROL_FLOW_CAPTURE_BOUNDARY_PROVEN"',
            SOURCE,
        )

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_92_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_92_proof=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_92_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
