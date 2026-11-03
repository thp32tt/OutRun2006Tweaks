#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00410/F143."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(encoding="utf-8")


class Continuation105ControlFlowTests(unittest.TestCase):
    def test_f142_window_and_f143_boundaries_are_pinned(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_RVA = 0x00183C3D", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_PROBE_END_RVA = 0x00183C7D", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_PREFIX_END_RVA = 0x00183C7C", SOURCE)
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_INCOMPLETE_BYTES = bytes.fromhex("ff")', SOURCE)

    def test_mandatory_overlap_is_consumed_as_complete_short_jump(self):
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_OVERLAP_BYTES = bytes.fromhex("eb")', SOURCE)
        self.assertIn('(0x00183C3D, "eb 03", "jmp 0x183c42")', SOURCE)
        self.assertIn('"F142_EXACT_183C3D_RAW_FRONTIER_CONSUMED_WITH_FULL_OVERLAP"', SOURCE)

    def test_complete_decode_stops_before_partial_ff(self):
        self.assertIn('(0x00183C7B, "57", "push edi")', SOURCE)
        instructions = SOURCE.split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_INSTRUCTIONS = (", 1
        )[1].split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_BRANCHES = (", 1
        )[0]
        self.assertNotIn('(0x00183C7C, "ff', instructions)
        self.assertIn('"COMPLETE_INSTRUCTIONS_END_AT_183C7C_TRAILING_FF_REQUIRES_OVERLAP"', SOURCE)

    def test_three_short_branches_are_pinned_to_current_boundaries(self):
        self.assertIn("(0x00183C3D, 0x00183C42)", SOURCE)
        self.assertIn("(0x00183C44, 0x00183C3F)", SOURCE)
        self.assertIn("(0x00183C65, 0x00183C5B)", SOURCE)
        self.assertIn('"SHORT_BRANCH_TARGETS_183C42_183C3F_183C5B_PROVEN_ON_EXACT_BOUNDARIES"', SOURCE)
        self.assertIn("and internal_branch_targets_on_boundaries", SOURCE)

    def test_f141_debt_is_not_resurrected(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_INHERITED_FORWARD_TARGETS = ()", SOURCE)
        section = SOURCE.split(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_105_provenance", 1
        )[1].split(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_105_prefix_proof", 1
        )[0]
        self.assertIn('predecessor["unresolved_forward_targets"] == []', section)
        self.assertNotIn('predecessor["unresolved_forward_targets"] == [0x00183C10, 0x00183C27]', section)
        self.assertIn('"NO_INHERITED_FORWARD_TARGETS_TO_RESOLVE"', SOURCE)
        self.assertIn('"NO_INHERITED_FORWARD_TARGET_DEBT_REMAINS"', SOURCE)

    def test_no_predecessor_boundary_gate_leaks_into_internal_only_proof(self):
        section = SOURCE.split(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_105_prefix_proof", 1
        )[1].split(
            "def _memoize_pe_only_collector", 1
        )[0]
        self.assertNotIn("target_is_predecessor_boundary", section)
        self.assertIn("set(external_targets) == expected_external_targets", section)
        self.assertIn('"NO_EXTERNAL_DIRECT_BRANCH_TARGETS"', section)

    def test_rel32_census_and_call_semantics_remain_quarantined(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_105_CALLS = ()", SOURCE)
        self.assertIn("and raw_inbound_census_empty", SOURCE)
        self.assertIn("and raw_call_census_empty", SOURCE)
        self.assertIn('"TRAILING_FF_OPCODE_SEMANTICS_UNRESOLVED_NO_REL32_CALLS_IN_F143_PREFIX"', SOURCE)

    def test_exact_status_and_failure_guards_exist(self):
        self.assertIn('"EXACT_EXE_183C3D_TO_183C7D_PROVENANCE_CAPTURED"', SOURCE)
        self.assertIn('"EXACT_183C3D_TO_183C7C_CONTROL_FLOW_WITH_183C7C_CUT_EDGE_PROVEN"', SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_105_provenance=FAILED", SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_105_prefix_proof=FAILED", SOURCE)

    def test_no_function_render_hud_or_runtime_semantic_promotion(self):
        self.assertIn('"INTERNAL_SHORT_BRANCHES_OBSERVED_NO_FUNCTION_SEMANTIC_PROMOTION"', SOURCE)
        self.assertIn('"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)


if __name__ == "__main__":
    unittest.main()
