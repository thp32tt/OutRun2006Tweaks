#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00356/F115."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation91ControlFlowTests(unittest.TestCase):
    def test_exact_boundary_and_instruction_table_are_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_PREFIX_END_RVA = 0x0018390E",
            SOURCE,
        )
        self.assertIn(
            '(0x001838CE, "73 19", "jae 0x1838e9")',
            SOURCE,
        )
        self.assertIn(
            '(0x0018390B, "8b 5b 04", "mov ebx, [ebx+4]")',
            SOURCE,
        )

    def test_exact_branches_are_bounded_to_instruction_boundaries(self):
        for marker in (
            "(0x001838CE, 0x001838E9)",
            "(0x001838E0, 0x00183905)",
            "(0x001838E7, 0x00183905)",
            "(0x001838FD, 0x00183905)",
        ):
            self.assertIn(marker, SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_CALLS = ()",
            SOURCE,
        )

    def test_inherited_183908_is_resolved_and_far_debt_remains(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_RESOLVED_PREDECESSOR_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn("0x00183908,", SOURCE)
        self.assertIn(
            "remaining_predecessor_targets == [0x00183926, 0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            'predecessor["unresolved_forward_targets"] == [0x00183908, 0x00183926, 0x00183B6F]',
            SOURCE,
        )

    def test_proof_consumes_exact_raw_provenance_and_empty_call_census(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_91_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_1838CE_TO_18390E_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            'raw_call_census_empty = not provenance["raw_outbound_rel32_candidates"]',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_1838CE_TO_18390E_CONTROL_FLOW_CAPTURE_BOUNDARY_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_91_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_91_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()