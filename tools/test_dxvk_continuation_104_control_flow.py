#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00408/F141."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(encoding="utf-8")


class Continuation104ControlFlowTests(unittest.TestCase):
    def test_f140_window_and_f141_boundaries_are_pinned(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_RVA = 0x00183BFE", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_PROBE_END_RVA = 0x00183C3E", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_PREFIX_END_RVA = 0x00183C3D", SOURCE)
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_INCOMPLETE_BYTES = bytes.fromhex("eb")', SOURCE)

    def test_mandatory_overlap_is_consumed_as_complete_push(self):
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_OVERLAP_BYTES = bytes.fromhex("ff 76")', SOURCE)
        self.assertIn('"ff 76 10"', SOURCE)
        self.assertIn('(0x00183BFE, "ff 76 10", "push dword [esi+0x10]")', SOURCE)
        self.assertIn('"F140_EXACT_183BFE_RAW_FRONTIER_CONSUMED_WITH_FULL_OVERLAP"', SOURCE)

    def test_complete_decode_stops_before_partial_short_jump(self):
        self.assertIn('(0x00183C3B, "33 db", "xor ebx, ebx")', SOURCE)
        continuation_104_instructions = SOURCE.split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_INSTRUCTIONS = (", 1
        )[1].split(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_BRANCHES = (", 1
        )[0]
        self.assertNotIn('(0x00183C3D, "eb', continuation_104_instructions)
        self.assertIn('"COMPLETE_INSTRUCTIONS_END_AT_183C3D_TRAILING_EB_REQUIRES_OVERLAP"', SOURCE)

    def test_inherited_forward_targets_are_resolved_on_exact_boundaries(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_INHERITED_FORWARD_TARGETS = (", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_RESOLVED_PREDECESSOR_TARGET_RVAS = (", SOURCE)
        self.assertIn('(0x00183C10, "83 4e 08 ff", "or dword [esi+8], -1")', SOURCE)
        self.assertIn('(0x00183C27, "5e", "pop esi")', SOURCE)
        self.assertIn('"INHERITED_FORWARD_TARGETS_183C10_183C27_RESOLVED_ON_EXACT_BOUNDARIES"', SOURCE)
        self.assertIn('"NO_INHERITED_FORWARD_TARGET_DEBT_REMAINS"', SOURCE)

    def test_backward_jump_is_proven_only_on_predecessor_boundary(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_104_BRANCHES = (", SOURCE)
        self.assertIn("(0x00183C0E, 0x00183BE0)", SOURCE)
        self.assertIn("predecessor_instruction_starts", SOURCE)
        self.assertIn("predecessor_branch_targets_on_boundaries", SOURCE)
        self.assertIn('"JMP_183C0E_TO_183BE0_PREDECESSOR_TARGET_PROVEN_ON_BOUNDARY"', SOURCE)

    def test_rel32_census_is_empty_and_indirect_call_remains_unresolved(self):
        self.assertIn("and not inbound", SOURCE)
        self.assertIn("and not outbound", SOURCE)
        self.assertIn('(0x00183C08, "ff 15 4c 61 59 00", "call dword [0x59614c]")', SOURCE)
        self.assertIn('"INDIRECT_CALL_183C08_TARGET_AND_EFFECT_UNRESOLVED_NO_REL32_CALLS_IN_F141_PREFIX"', SOURCE)

    def test_exact_status_and_report_failure_guards_exist(self):
        self.assertIn('"EXACT_EXE_183BFE_TO_183C3E_PROVENANCE_CAPTURED"', SOURCE)
        self.assertIn('"EXACT_183BFE_TO_183C3D_CONTROL_FLOW_WITH_183C3D_CUT_EDGE_PROVEN"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_104_provenance"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_104_prefix_proof"', SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_104_provenance=FAILED", SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_104_prefix_proof=FAILED", SOURCE)

    def test_no_function_render_hud_or_runtime_semantic_promotion(self):
        self.assertIn('"BACKWARD_BRANCH_183C0E_TO_183BE0_AND_SECOND_PROLOGUE_183C2A_OBSERVED_NO_FUNCTION_SEMANTIC_PROMOTION"', SOURCE)
        self.assertIn('"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)


if __name__ == "__main__":
    unittest.main()
