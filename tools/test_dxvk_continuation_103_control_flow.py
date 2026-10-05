#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00406/F139."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(encoding="utf-8")


class Continuation103ControlFlowTests(unittest.TestCase):
    def test_f138_window_and_f139_boundaries_are_pinned(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_RVA = 0x00183BC0", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_PROBE_END_RVA = 0x00183C00", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_PREFIX_END_RVA = 0x00183BFE", SOURCE)
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_INCOMPLETE_BYTES = bytes.fromhex("ff 76")', SOURCE)

    def test_mandatory_overlap_is_consumed_as_complete_push_imm32(self):
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_OVERLAP_BYTES = bytes.fromhex("68 c4 41")', SOURCE)
        self.assertIn('"68 c4 41 00 00"', SOURCE)
        self.assertIn('(0x00183BC0, "68 c4 41 00 00", "push 0x41c4")', SOURCE)
        self.assertIn('"F138_EXACT_183BC0_RAW_FRONTIER_CONSUMED_WITH_FULL_OVERLAP"', SOURCE)

    def test_complete_decode_stops_before_partial_ff76(self):
        self.assertIn('(0x00183BFC, "75 12", "jne 0x183c10")', SOURCE)
        continuation_103_instructions = SOURCE.split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_INSTRUCTIONS = (", 1
        )[1].split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_BRANCHES = (", 1
        )[0]
        self.assertNotIn('(0x00183BFE, "ff 76', continuation_103_instructions)
        self.assertIn('"COMPLETE_INSTRUCTIONS_END_AT_183BFE_TRAILING_FF76_REQUIRES_OVERLAP"', SOURCE)

    def test_internal_and_external_short_branch_debt_is_exact(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_BRANCHES = (", SOURCE)
        self.assertIn("(0x00183BDE, 0x00183BE4)", SOURCE)
        self.assertIn("(0x00183BE2, 0x00183C27)", SOURCE)
        self.assertIn("(0x00183BFC, 0x00183C10)", SOURCE)
        self.assertIn('expected_external_targets = {0x00183C10, 0x00183C27}', SOURCE)
        self.assertIn('unresolved_forward_targets = [0x00183C10, 0x00183C27]', SOURCE)
        self.assertIn('"JNE_183BDE_TO_183BE4_TARGET_PROVEN_ON_BOUNDARY"', SOURCE)
        self.assertIn('"JMP_183BE2_TO_183C27_AND_JNE_183BFC_TO_183C10_CARRIED_UNRESOLVED"', SOURCE)

    def test_predecessor_has_no_forward_target_debt_to_promote(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_INHERITED_FORWARD_TARGETS = ()", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_103_RESOLVED_PREDECESSOR_TARGET_RVAS = ()", SOURCE)
        self.assertIn('"NO_INHERITED_FORWARD_TARGET_DEBT_TO_RESOLVE"', SOURCE)
        self.assertIn('"NO_INHERITED_FORWARD_TARGET_DEBT_REMAINS"', SOURCE)

    def test_rel32_census_is_empty_and_both_indirect_calls_remain_unresolved(self):
        self.assertIn("and not inbound", SOURCE)
        self.assertIn("and not outbound", SOURCE)
        self.assertIn('(0x00183BD3, "ff 15 48 61 59 00", "call dword [0x596148]")', SOURCE)
        self.assertIn('(0x00183BF1, "ff 15 3c 61 59 00", "call dword [0x59613c]")', SOURCE)
        self.assertIn('"INDIRECT_CALLS_183BD3_183BF1_TARGET_AND_EFFECT_UNRESOLVED_NO_REL32_CALLS_IN_F139_PREFIX"', SOURCE)

    def test_exact_status_and_report_failure_guards_exist(self):
        self.assertIn('"EXACT_EXE_183BC0_TO_183C00_PROVENANCE_CAPTURED"', SOURCE)
        self.assertIn('"EXACT_183BC0_TO_183BFE_CONTROL_FLOW_WITH_183BFE_CUT_EDGE_PROVEN"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_103_provenance"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_103_prefix_proof"', SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_103_provenance=FAILED", SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_103_prefix_proof=FAILED", SOURCE)

    def test_no_function_render_hud_or_runtime_semantic_promotion(self):
        self.assertIn('"BRANCH_BOUNDARY_183BE4_PROVEN_EXTERNAL_183C10_183C27_UNRESOLVED_NO_FUNCTION_SEMANTIC_PROMOTION"', SOURCE)
        self.assertIn('"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)


if __name__ == "__main__":
    unittest.main()
