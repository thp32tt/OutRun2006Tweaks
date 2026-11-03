#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00390/F129."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation98ControlFlowTests(unittest.TestCase):
    def test_f128_exact_raw_window_is_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_98_RVA = 0x00183A8A",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_98_PROBE_END_RVA = 0x00183ACA",
            SOURCE,
        )
        self.assertIn(
            '"8b 35 bc 60 59 00 68 00 40 00 00 c1 e1 0f 03 48 "',
            SOURCE,
        )
        self.assertIn(
            '"40 bc 98 00 8b 40 10 8b 0d 58 bc 98 00 83 a4 88"',
            SOURCE,
        )

    def test_complete_decode_stops_before_three_byte_cut_edge(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_98_PREFIX_END_RVA = 0x00183AC7",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_98_INCOMPLETE_RVA = 0x00183AC7",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_98_INCOMPLETE_BYTES = bytes.fromhex("83 a4 88")',
            SOURCE,
        )
        self.assertIn(
            '(0x00183A8A, "8b 35 bc 60 59 00", "mov esi, [0x5960bc]")',
            SOURCE,
        )
        self.assertIn(
            '(0x00183AC1, "8b 0d 58 bc 98 00", "mov ecx, [0x98bc58]")',
            SOURCE,
        )
        self.assertIn(
            '"COMPLETE_INSTRUCTIONS_END_AT_183AC7_TRAILING_83A488_REQUIRES_OVERLAP"',
            SOURCE,
        )

    def test_indirect_call_site_is_exact_but_semantics_stay_unresolved(self):
        self.assertIn(
            '(0x00183AA2, "ff d6", "call esi")',
            SOURCE,
        )
        self.assertIn(
            "indirect_call_site_rva = 0x00183AA2",
            SOURCE,
        )
        self.assertIn(
            'indirect_call_site_bytes == bytes.fromhex("ff d6")',
            SOURCE,
        )
        self.assertIn(
            '"call_semantics": "EXACT_INDIRECT_CALL_ESI_AT_183AA2_TARGET_SEMANTICS_UNRESOLVED"',
            SOURCE,
        )

    def test_forward_target_debt_is_carried_without_promotion(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_98_INHERITED_FORWARD_TARGETS = (",
            SOURCE,
        )
        self.assertIn(
            "remaining_predecessor_targets == [0x00183B60, 0x00183B6E, 0x00183B6F]",
            SOURCE,
        )
        self.assertIn(
            "unresolved_forward_targets = [\n        0x00183B60,\n        0x00183B6E,\n        0x00183B6F,\n    ]",
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "BOUNDED_CONTROL_FLOW_AND_MANDATORY_OVERLAP_ONLY"',
            SOURCE,
        )

    def test_provenance_and_raw_rel32_census_remain_fail_closed(self):
        self.assertIn(
            'predecessor["status"] == "EXACT_183A4A_TO_183A8A_CONTROL_FLOW_BOUNDARY_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            'predecessor["prefix_end_rva"] == target_rva',
            SOURCE,
        )
        self.assertIn(
            'predecessor["capture_boundary_matches"]',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_183A8A_TO_183ACA_PROVENANCE_CAPTURED"',
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

    def test_report_binding_and_failure_guards_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_98_provenance"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_98_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_98=",
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_98_proof=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_98_provenance=FAILED",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_98_prefix_proof=FAILED",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_183A8A_TO_183AC7_CONTROL_FLOW_WITH_183AC7_CUT_EDGE_PROVEN"',
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()