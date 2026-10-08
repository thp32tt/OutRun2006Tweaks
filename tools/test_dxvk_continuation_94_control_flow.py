#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00368/F121."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation94ControlFlowTests(unittest.TestCase):
    def test_complete_instruction_prefix_and_overlap_are_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_PREFIX_END_RVA = 0x001839CD",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_INCOMPLETE_RVA = 0x001839CD",
            SOURCE,
        )
        self.assertIn(
            '(0x0018398E, "fe 4c 03 04", "dec byte [ebx+eax+4]")',
            SOURCE,
        )
        self.assertIn(
            '(0x001839CA, "89 4e 08", "mov [esi+8], ecx")',
            SOURCE,
        )

    def test_exact_branches_are_pinned_to_internal_boundary(self):
        for row in (
            "(0x00183992, 0x001839B5)",
            "(0x00183999, 0x001839B5)",
            "(0x001839AD, 0x001839B5)",
        ):
            self.assertIn(row, SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_CALLS = ()",
            SOURCE,
        )

    def test_predecessor_targets_resolve_only_on_exact_boundaries(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_RESOLVED_PREDECESSOR_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn(
            "resolved_predecessor_target_rvas == {0x0018399B, 0x001839B5}",
            SOURCE,
        )
        self.assertIn(
            "remaining_predecessor_targets == [0x001839CD, 0x001839D2, 0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            "unresolved_forward_targets = [\n        0x001839CD,\n        0x001839D2,\n        0x00183B6F,\n    ]",
            SOURCE,
        )

    def test_mandatory_cut_edge_is_fail_closed(self):
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_INCOMPLETE_BYTES = bytes.fromhex("8b")',
            SOURCE,
        )
        self.assertIn("incomplete_matches = (", SOURCE)
        self.assertIn("capture_edge_matches = (", SOURCE)
        self.assertIn(
            '"COMPLETE_INSTRUCTIONS_END_AT_1839CD_TRAILING_8B_REQUIRES_OVERLAP"',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"',
            SOURCE,
        )

    def test_proof_consumes_exact_f120_provenance(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_94_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_18398E_TO_1839CE_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_18398E_TO_1839CD_CONTROL_FLOW_WITH_1839CD_OVERLAP_PROVEN"',
            SOURCE,
        )

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_94_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_94_proof=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_94_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
