#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00342/F107."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation87ControlFlowTests(unittest.TestCase):
    def test_exact_prefix_and_cut_edge_are_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_PREFIX_END_RVA = 0x00183810",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_INCOMPLETE_RVA = 0x00183810",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_INCOMPLETE_BYTES = bytes.fromhex("83 25 44 bc 98")',
            SOURCE,
        )
        self.assertIn(
            '(0x00183809, "83 25 40 bc 98 00 00", "and dword [0x98bc40], 0")',
            SOURCE,
        )

    def test_inherited_targets_and_internal_branch_are_exact(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_RESOLVED_PREDECESSOR_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn("0x001837E1", SOURCE)
        self.assertIn("0x001837E4", SOURCE)
        self.assertIn("(0x00183802, 0x00183805)", SOURCE)
        self.assertIn(
            "resolved_predecessor_targets_on_boundaries",
            SOURCE,
        )

    def test_empty_rel32_call_census_is_fail_closed(self):
        self.assertIn(
            'raw_call_census_empty = not provenance["raw_outbound_rel32_candidates"]',
            SOURCE,
        )
        self.assertIn(
            '"raw_call_census_empty": raw_call_census_empty',
            SOURCE,
        )

    def test_fail_closed_proof_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_87_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_1837D5_TO_183810_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_87_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_87_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
