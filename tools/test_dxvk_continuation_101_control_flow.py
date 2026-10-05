#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00402/F135."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(encoding="utf-8")


class Continuation101ControlFlowTests(unittest.TestCase):
    def test_f134_window_and_f135_boundaries_are_pinned(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_RVA = 0x00183B44", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_PROBE_END_RVA = 0x00183B84", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_PREFIX_END_RVA = 0x00183B83", SOURCE)
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_INCOMPLETE_BYTES = bytes.fromhex("75")', SOURCE)

    def test_mandatory_overlap_is_consumed_as_complete_first_instruction(self):
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_OVERLAP_BYTES = bytes.fromhex("ff 0d 44")', SOURCE)
        self.assertIn('"ff 0d 44 bc 98 00"', SOURCE)
        self.assertIn('(0x00183B44, "ff 0d 44 bc 98 00", "dec dword [0x98bc44]")', SOURCE)
        self.assertIn('"F134_EXACT_183B44_RAW_FRONTIER_CONSUMED_WITH_FULL_OVERLAP"', SOURCE)

    def test_complete_decode_stops_before_partial_jcc(self):
        self.assertIn('(0x00183B81, "3b c1", "cmp eax, ecx")', SOURCE)
        continuation_101_instructions = SOURCE.split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_INSTRUCTIONS = (", 1
        )[1].split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_BRANCHES = (", 1
        )[0]
        self.assertNotIn('(0x00183B83, "75 ', continuation_101_instructions)
        self.assertIn('"COMPLETE_INSTRUCTIONS_END_AT_183B83_TRAILING_75_REQUIRES_OVERLAP"', SOURCE)

    def test_internal_jbe_target_is_exact_boundary(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_BRANCHES = (", SOURCE)
        self.assertIn("(0x00183B50, 0x00183B56)", SOURCE)
        self.assertIn('"JBE_183B50_TO_183B56_TARGET_PROVEN_ON_BOUNDARY"', SOURCE)
        self.assertIn("internal_branch_targets_on_boundaries", SOURCE)

    def test_inherited_targets_are_resolved_only_as_instruction_boundaries(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_101_RESOLVED_PREDECESSOR_TARGET_RVAS = (", SOURCE)
        self.assertIn("== {0x00183B60, 0x00183B6E, 0x00183B6F}", SOURCE)
        self.assertIn('"INHERITED_183B60_183B6E_183B6F_PROVEN_AS_INSTRUCTION_BOUNDARIES"', SOURCE)
        self.assertIn('"NO_INHERITED_FORWARD_TARGET_DEBT_REMAINS"', SOURCE)
        self.assertIn('"unresolved_forward_targets": unresolved_forward_targets', SOURCE)

    def test_raw_rel32_census_remains_empty_and_no_call_is_promoted(self):
        self.assertIn("and not inbound", SOURCE)
        self.assertIn("and not outbound", SOURCE)
        self.assertIn('raw_call_census_empty = not provenance["raw_outbound_rel32_candidates"]', SOURCE)
        self.assertIn('"NO_REL32_CALLS_IN_F135_PREFIX"', SOURCE)

    def test_exact_status_and_report_failure_guards_exist(self):
        self.assertIn('"EXACT_EXE_183B44_TO_183B84_PROVENANCE_CAPTURED"', SOURCE)
        self.assertIn('"EXACT_183B44_TO_183B83_CONTROL_FLOW_WITH_183B83_CUT_EDGE_PROVEN"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_101_provenance"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_101_prefix_proof"', SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_101_provenance=FAILED", SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_101_prefix_proof=FAILED", SOURCE)

    def test_no_function_render_hud_or_runtime_semantic_promotion(self):
        self.assertIn('"INHERITED_BOUNDARIES_183B60_183B6E_183B6F_PROVEN_NO_FUNCTION_SEMANTIC_PROMOTION"', SOURCE)
        self.assertIn('"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)


if __name__ == "__main__":
    unittest.main()
