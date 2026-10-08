#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00400/F133."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(encoding="utf-8")


class Continuation100ControlFlowTests(unittest.TestCase):
    def test_f132_raw_window_and_boundaries_are_pinned(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_RVA = 0x00183B07", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_PROBE_END_RVA = 0x00183B47", SOURCE)
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_PREFIX_END_RVA = 0x00183B44", SOURCE)
        self.assertIn('GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_INCOMPLETE_BYTES = bytes.fromhex("ff 0d 44")', SOURCE)

    def test_complete_decode_stops_before_partial_dec_instruction(self):
        self.assertIn('(0x00183B07, "6a 00", "push 0")', SOURCE)
        self.assertIn('(0x00183B41, "83 c4 0c", "add esp, 0x0c")', SOURCE)
        continuation_100_rows = SOURCE[
            SOURCE.index("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_INSTRUCTIONS = ("):
            SOURCE.index("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_BRANCHES = ()")
        ]
        self.assertNotIn('(0x00183B44, "ff 0d 44 bc 98 00"', continuation_100_rows)
        self.assertIn('"COMPLETE_INSTRUCTIONS_END_AT_183B44_TRAILING_FF0D44_REQUIRES_OVERLAP"', SOURCE)

    def test_exact_rel32_call_is_address_only(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_CALLS = (", SOURCE)
        self.assertIn("(0x00183B39, 0x00180340)", SOURCE)
        self.assertIn('"call_semantics": "UNRESOLVED"', SOURCE)
        self.assertIn('"EXACT_REL32_CALL_183B39_TO_180340_ADDRESS_ONLY_AND_INDIRECT_CALL_183B0F_TARGET_SEMANTICS_UNRESOLVED"', SOURCE)

    def test_indirect_call_bytes_are_pinned_without_semantic_promotion(self):
        self.assertIn('(0x00183B0F, "ff 15 4c 61 59 00", "call dword [0x59614c]")', SOURCE)
        self.assertIn("indirect_call_site_rva = 0x00183B0F", SOURCE)
        self.assertIn('indirect_call_site_bytes == bytes.fromhex("ff 15 4c 61 59 00")', SOURCE)

    def test_inherited_forward_target_debt_remains_fail_closed(self):
        self.assertIn("GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_INHERITED_FORWARD_TARGETS = (", SOURCE)
        self.assertIn("remaining_predecessor_targets == [0x00183B60, 0x00183B6E, 0x00183B6F]", SOURCE)
        self.assertIn('"INHERITED_183B60_183B6E_183B6F_REMAIN_UNRESOLVED"', SOURCE)

    def test_raw_rel32_census_requires_exact_single_call(self):
        self.assertIn('outbound_identity == expected_outbound', SOURCE)
        self.assertIn('"raw_outbound_rel32_matches": outbound_identity == expected_outbound', SOURCE)
        self.assertIn('raw_inbound_census_empty = not provenance["raw_inbound_rel32_candidates"]', SOURCE)
        self.assertIn('expected_raw_calls = set(GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_100_CALLS)', SOURCE)
        self.assertIn('raw_call_census_matches = observed_raw_calls == expected_raw_calls', SOURCE)

    def test_report_binding_and_failure_guards_exist(self):
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_100_provenance"', SOURCE)
        self.assertIn('"guarded_gf_target_c_helper_1_third_callee_continuation_100_prefix_proof"', SOURCE)
        self.assertIn("gf_target_c_helper_1_third_callee_continuation_100=", SOURCE)
        self.assertIn("gf_target_c_helper_1_third_callee_continuation_100_proof=", SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_100_provenance=FAILED", SOURCE)
        self.assertIn("guarded_gf_target_c_helper_1_third_callee_continuation_100_prefix_proof=FAILED", SOURCE)


if __name__ == "__main__":
    unittest.main()
