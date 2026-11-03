#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00372/F123."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation95ControlFlowTests(unittest.TestCase):
    def test_complete_instruction_prefix_and_cut_edge_are_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_PREFIX_END_RVA = 0x00183A0C",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_INCOMPLETE_RVA = 0x00183A0C",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_INCOMPLETE_BYTES = bytes.fromhex("83")',
            SOURCE,
        )
        self.assertIn(
            '(0x001839CD, "8b 75 0c", "mov esi, [ebp+0x0c]")',
            SOURCE,
        )
        self.assertIn(
            '(0x00183A0A, "fe c1", "inc cl")',
            SOURCE,
        )

    def test_exact_branches_and_call_census_are_pinned(self):
        for row in (
            "(0x001839D0, 0x001839D5)",
            "(0x001839D9, 0x001839E3)",
            "(0x001839DD, 0x00183A63)",
            "(0x00183A01, 0x00183A63)",
        ):
            self.assertIn(row, SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_CALLS = ()",
            SOURCE,
        )
        self.assertIn("expected_external_targets = {0x00183A63}", SOURCE)

    def test_inherited_target_debt_transitions_only_on_exact_boundaries(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_RESOLVED_PREDECESSOR_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn(
            "resolved_predecessor_target_rvas == {0x001839CD, 0x001839D2}",
            SOURCE,
        )
        self.assertIn(
            "remaining_predecessor_targets == [0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            "unresolved_forward_targets = [\n        0x00183A63,\n        0x00183B6F,\n    ]",
            SOURCE,
        )

    def test_mandatory_183a0c_cut_edge_is_fail_closed(self):
        self.assertIn("incomplete_matches = (", SOURCE)
        self.assertIn("capture_edge_matches = (", SOURCE)
        self.assertIn(
            '"COMPLETE_INSTRUCTIONS_END_AT_183A0C_TRAILING_83_REQUIRES_OVERLAP"',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"',
            SOURCE,
        )

    def test_proof_consumes_exact_f122_provenance(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_95_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_1839CD_TO_183A0D_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_1839CD_TO_183A0C_CONTROL_FLOW_WITH_183A0C_CUT_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            'provenance["overlap_matches"]',
            SOURCE,
        )
        self.assertIn(
            'provenance["predecessor_overlap_matches"]',
            SOURCE,
        )

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_95_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_95_proof=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_95_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
