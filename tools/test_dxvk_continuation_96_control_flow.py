#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00378/F125."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation96ControlFlowTests(unittest.TestCase):
    def test_complete_instruction_prefix_and_cut_edge_are_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_96_PREFIX_END_RVA = 0x00183A4A",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_96_INCOMPLETE_RVA = 0x00183A4A",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_96_INCOMPLETE_BYTES = bytes.fromhex("8b 4d")',
            SOURCE,
        )
        self.assertIn('(0x00183A0C, "83 fa 20", "cmp edx, 0x20")', SOURCE)
        self.assertIn('(0x00183A48, "d3 eb", "shr ebx, cl")', SOURCE)

    def test_exact_branches_and_internal_boundaries_are_pinned(self):
        for row in (
            "(0x00183A13, 0x00183A3A)",
            "(0x00183A19, 0x00183A29)",
            "(0x00183A38, 0x00183A63)",
            "(0x00183A3E, 0x00183A50)",
        ):
            self.assertIn(row, SOURCE)
        self.assertIn("expected_external_targets = {0x00183A50, 0x00183A63}", SOURCE)
        self.assertIn(
            '"internal_branch_status": "EXACT_183A29_AND_183A3A_INTERNAL_TARGET_BOUNDARIES_PROVEN"',
            SOURCE,
        )

    def test_inherited_target_debt_is_preserved_fail_closed(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_96_RESOLVED_PREDECESSOR_TARGET_RVAS = ()",
            SOURCE,
        )
        self.assertIn(
            "remaining_predecessor_targets == [0x00183A63, 0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            "unresolved_forward_targets = [\n        0x00183A50,\n        0x00183A63,\n        0x00183B6F,\n    ]",
            SOURCE,
        )

    def test_f124_raw_provenance_and_rel32_census_are_required(self):
        self.assertIn(
            '"EXACT_EXE_183A0C_TO_183A4C_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            'not provenance["raw_inbound_rel32_candidates"]',
            SOURCE,
        )
        self.assertIn(
            'not provenance["raw_outbound_rel32_candidates"]',
            SOURCE,
        )
        self.assertIn(
            '"raw_call_census_empty": raw_call_census_empty',
            SOURCE,
        )

    def test_mandatory_183a4a_cut_edge_is_fail_closed(self):
        self.assertIn("capture_edge_matches = (", SOURCE)
        self.assertIn(
            '"COMPLETE_INSTRUCTIONS_END_AT_183A4A_TRAILING_8B4D_REQUIRES_OVERLAP"',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"',
            SOURCE,
        )

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_96_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_96_proof=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_96_prefix_proof=FAILED",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_183A0C_TO_183A4A_CONTROL_FLOW_WITH_183A4A_CUT_EDGE_PROVEN"',
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
