#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00350/F111."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation89ControlFlowTests(unittest.TestCase):
    def test_full_capture_is_exactly_25_complete_instructions(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_PREFIX_END_RVA = 0x0018388F",
            SOURCE,
        )
        self.assertIn(
            '(0x0018384F, "72 09", "jb 0x18385a")',
            SOURCE,
        )
        self.assertIn(
            '(0x0018388C, "f6 c1 01", "test cl, 1")',
            SOURCE,
        )
        self.assertIn(
            '"instruction_count": len(rows)',
            SOURCE,
        )

    def test_inherited_forward_target_is_resolved_on_current_boundary(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_RESOLVED_PREDECESSOR_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn("0x00183854", SOURCE)
        self.assertIn(
            'resolved_predecessor_target_rvas == {0x00183854}',
            SOURCE,
        )
        self.assertIn(
            '"resolved_predecessor_targets_on_boundaries": resolved_predecessor_targets_on_boundaries',
            SOURCE,
        )

    def test_both_exact_branches_are_fail_closed(self):
        self.assertIn("(0x0018384F, 0x0018385A)", SOURCE)
        self.assertIn("(0x00183856, 0x00183842)", SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_EXPECTED_PREDECESSOR_BOUNDARY_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn(
            '"predecessor_branch_targets_on_boundaries": predecessor_branch_targets_on_boundaries',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_183856_TO_183842_PREDECESSOR_INSTRUCTION_BOUNDARY_PROVEN"',
            SOURCE,
        )

    def test_proof_requires_exact_provenance_and_is_guarded(self):
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_18384F_TO_18388F_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn('provenance["exact_bytes_match"]', SOURCE)
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_89_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_18384F_TO_18388F_CONTROL_FLOW_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_89_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_89_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
