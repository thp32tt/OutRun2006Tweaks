#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00384/F127."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation97ControlFlowTests(unittest.TestCase):
    def test_f126_exact_raw_window_is_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_97_RVA = 0x00183A4A",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_97_PROBE_END_RVA = 0x00183A8A",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_97_OVERLAP_BYTES = bytes.fromhex("8b 4d")',
            SOURCE,
        )
        self.assertIn(
            '"8b 4d 08 09 59 04 8d 4a e0 ba 00 00 00 80 d3 ea "',
            SOURCE,
        )
        self.assertIn(
            '"98 00 85 c0 0f 84 dc 00 00 00 8b 0d 58 bc 98 00"',
            SOURCE,
        )

    def test_capture_ends_on_exact_instruction_boundary_without_cut_edge(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_97_PREFIX_END_RVA = 0x00183A8A",
            SOURCE,
        )
        self.assertNotIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_97_INCOMPLETE_RVA",
            SOURCE,
        )
        self.assertIn(
            '(0x00183A4A, "8b 4d 08", "mov ecx, [ebp+8]")',
            SOURCE,
        )
        self.assertIn(
            '(0x00183A84, "8b 0d 58 bc 98 00", "mov ecx, [0x98bc58]")',
            SOURCE,
        )
        self.assertIn(
            '"COMPLETE_INSTRUCTIONS_END_AT_183A8A_EXACT_CAPTURE_BOUNDARY_NO_OVERLAP_DEBT"',
            SOURCE,
        )

    def test_inherited_targets_resolve_only_on_exact_boundaries(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_97_RESOLVED_PREDECESSOR_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn(
            "resolved_predecessor_target_rvas == {0x00183A50, 0x00183A63}",
            SOURCE,
        )
        self.assertIn(
            "remaining_predecessor_targets == [0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            '"resolved_predecessor_target_status": "EXACT_183A50_AND_183A63_PREDECESSOR_FORWARD_TARGET_BOUNDARIES_PROVEN"',
            SOURCE,
        )

    def test_new_forward_branches_are_exact_and_carried_fail_closed(self):
        self.assertIn("(0x00183A71, 0x00183B6E)", SOURCE)
        self.assertIn("(0x00183A7E, 0x00183B60)", SOURCE)
        self.assertIn(
            "expected_external_targets = {0x00183B60, 0x00183B6E}",
            SOURCE,
        )
        self.assertIn(
            "unresolved_forward_targets = [\n        0x00183B60,\n        0x00183B6E,\n        0x00183B6F,\n    ]",
            SOURCE,
        )

    def test_provenance_and_raw_census_remain_fail_closed(self):
        self.assertIn(
            'predecessor["status"] == "EXACT_183A0C_TO_183A4A_CONTROL_FLOW_WITH_183A4A_CUT_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_183A4A_TO_183A8A_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            'raw_inbound_census_empty = not provenance["raw_inbound_rel32_candidates"]',
            SOURCE,
        )
        self.assertIn(
            'raw_call_census_empty = not provenance["raw_outbound_rel32_candidates"]',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "BOUNDED_CONTROL_FLOW_ONLY"',
            SOURCE,
        )

    def test_report_binding_and_failure_guards_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_97_provenance"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_97_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_97=",
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_97_proof=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_97_provenance=FAILED",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_97_prefix_proof=FAILED",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_183A4A_TO_183A8A_CONTROL_FLOW_BOUNDARY_PROVEN"',
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
