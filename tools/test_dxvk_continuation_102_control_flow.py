#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00404/F137."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(encoding="utf-8")


class Continuation102ControlFlowTests(unittest.TestCase):
    def test_f136_window_and_f137_boundaries_are_pinned(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_RVA = 0x00183B83", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_PROBE_END_RVA = 0x00183BC3", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_PREFIX_END_RVA = 0x00183BC0", SOURCE)
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_INCOMPLETE_BYTES = bytes.fromhex("68 c4 41")', SOURCE)

    def test_mandatory_overlap_is_consumed_as_complete_short_jcc(self):
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_OVERLAP_BYTES = bytes.fromhex("75")', SOURCE)
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_FIRST_INSTRUCTION_BYTES = bytes.fromhex(', SOURCE)
        self.assertIn('(0x00183B83, "75 34", "jne 0x183bb9")', SOURCE)
        self.assertIn('"F136_EXACT_183B83_RAW_FRONTIER_CONSUMED_WITH_FULL_OVERLAP"', SOURCE)

    def test_complete_decode_stops_before_partial_push_imm32(self):
        self.assertIn('(0x00183BBF, "56", "push esi")', SOURCE)
        continuation_102_instructions = SOURCE.split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_INSTRUCTIONS = (", 1
        )[1].split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_BRANCHES = (", 1
        )[0]
        self.assertNotIn('(0x00183BC0, "68 ', continuation_102_instructions)
        self.assertIn('"COMPLETE_INSTRUCTIONS_END_AT_183BC0_TRAILING_68C441_REQUIRES_OVERLAP"', SOURCE)

    def test_both_jne_targets_are_exact_instruction_boundaries(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_BRANCHES = (", SOURCE)
        self.assertIn("(0x00183B83, 0x00183BB9)", SOURCE)
        self.assertIn("(0x00183BA2, 0x00183BA8)", SOURCE)
        self.assertIn('"JNE_183B83_TO_183BB9_AND_183BA2_TO_183BA8_TARGETS_PROVEN_ON_BOUNDARIES"', SOURCE)
        self.assertIn("internal_branch_targets_on_boundaries", SOURCE)

    def test_predecessor_has_no_forward_target_debt_to_promote(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_INHERITED_FORWARD_TARGETS = ()", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_102_RESOLVED_PREDECESSOR_TARGET_RVAS = ()", SOURCE)
        self.assertIn('"NO_INHERITED_FORWARD_TARGET_DEBT_TO_RESOLVE"', SOURCE)
        self.assertIn('"NO_INHERITED_FORWARD_TARGET_DEBT_REMAINS"', SOURCE)

    def test_rel32_census_remains_empty_and_indirect_call_semantics_unresolved(self):
        self.assertIn("and not inbound", SOURCE)
        self.assertIn("and not outbound", SOURCE)
        self.assertIn('(0x00183B9A, "ff 15 68 61 59 00", "call dword [0x596168]")', SOURCE)
        self.assertIn('"INDIRECT_CALL_183B9A_TARGET_AND_EFFECT_UNRESOLVED_NO_REL32_CALLS_IN_F137_PREFIX"', SOURCE)

    def test_exact_status_and_report_failure_guards_exist(self):
        self.assertIn('"EXACT_EXE_183B83_TO_183BC3_PROVENANCE_CAPTURED"', SOURCE)
        self.assertIn('"EXACT_183B83_TO_183BC0_CONTROL_FLOW_WITH_183BC0_CUT_EDGE_PROVEN"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_102_provenance"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_102_prefix_proof"', SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_102_provenance=FAILED", SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_102_prefix_proof=FAILED", SOURCE)

    def test_no_function_render_hud_or_runtime_semantic_promotion(self):
        self.assertIn('"BRANCH_BOUNDARIES_183BA8_183BB9_PROVEN_NO_FUNCTION_SEMANTIC_PROMOTION"', SOURCE)
        self.assertIn('"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)


if __name__ == "__main__":
    unittest.main()
