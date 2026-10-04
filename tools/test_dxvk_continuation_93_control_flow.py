#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00364/F119."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation93ControlFlowTests(unittest.TestCase):
    def test_exact_boundary_and_instruction_table_are_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_PREFIX_END_RVA = 0x0018398E",
            SOURCE,
        )
        self.assertIn(
            '(0x0018394E, "89 75 0c", "mov [ebp+0x0c], esi")',
            SOURCE,
        )
        self.assertIn(
            '(0x0018398A, "21 74 b8 44", "and [eax+edi*4+0x44], esi")',
            SOURCE,
        )

    def test_exact_branches_are_pinned(self):
        for row in (
            "(0x00183955, 0x00183959)",
            "(0x00183967, 0x0018396B)",
            "(0x0018396D, 0x001839CD)",
            "(0x00183978, 0x001839B5)",
            "(0x00183982, 0x0018399B)",
        ):
            self.assertIn(row, SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_CALLS = ()",
            SOURCE,
        )

    def test_inherited_debt_remains_and_new_forward_targets_fail_closed(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_RESOLVED_PREDECESSOR_TARGET_RVAS = ()",
            SOURCE,
        )
        self.assertIn(
            "remaining_predecessor_targets == [0x001839D2, 0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            "0x0018399B,\n        0x001839B5,\n        0x001839CD,\n        0x001839D2,\n        0x00183B6F,",
            SOURCE,
        )

    def test_proof_consumes_exact_f118_provenance_and_boundaries(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_93_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_18394E_TO_18398E_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            "set(external_targets) == expected_external_targets",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_18394E_TO_18398E_CONTROL_FLOW_CAPTURE_BOUNDARY_PROVEN"',
            SOURCE,
        )

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_93_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_93_proof=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_93_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
