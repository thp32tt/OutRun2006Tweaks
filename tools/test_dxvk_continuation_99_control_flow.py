#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00396/F131."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation99ControlFlowTests(unittest.TestCase):
    def test_f130_exact_raw_window_and_overlap_are_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_99_RVA = 0x00183AC7",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_99_PROBE_END_RVA = 0x00183B07",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_99_OVERLAP_BYTES = bytes.fromhex("83 a4 88")',
            SOURCE,
        )
        self.assertIn(
            '"83 a4 88 c4 00 00 00 00 a1 40 bc 98 00 8b 40 10 "',
            SOURCE,
        )
        self.assertIn(
            '"53 6a 00 ff 70 0c ff d6 a1 40 bc 98 00 ff 70 10"',
            SOURCE,
        )

    def test_cut_edge_is_consumed_as_one_complete_instruction(self):
        self.assertIn(
            '(0x00183AC7, "83 a4 88 c4 00 00 00 00", "and dword [eax+ecx*4+0xc4], 0")',
            SOURCE,
        )
        self.assertIn(
            'rows[0]["expected_bytes"].startswith(provenance["overlap_expected_bytes"])',
            SOURCE,
        )
        self.assertIn(
            '"start_boundary_status": "F129_183AC7_OVERLAP_CONSUMED_AS_FULL_AND_INSTRUCTION_BOUNDARY"',
            SOURCE,
        )

    def test_complete_decode_reaches_exact_capture_boundary_without_new_overlap(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_99_PREFIX_END_RVA = 0x00183B07",
            SOURCE,
        )
        self.assertIn(
            '(0x00183B04, "ff 70 10", "push dword [eax+0x10]")',
            SOURCE,
        )
        self.assertIn(
            '"COMPLETE_INSTRUCTIONS_END_AT_183B07_EXACT_CAPTURE_BOUNDARY_NO_OVERLAP_DEBT"',
            SOURCE,
        )
        self.assertNotIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_99_INCOMPLETE_RVA",
            SOURCE,
        )

    def test_exact_branches_preserve_forward_target_debt(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_99_BRANCHES = (",
            SOURCE,
        )
        self.assertIn("(0x00183AE6, 0x00183AF1)", SOURCE)
        self.assertIn("(0x00183AF5, 0x00183B60)", SOURCE)
        self.assertIn("expected_external_targets = {0x00183B60}", SOURCE)
        self.assertIn(
            "unresolved_forward_targets = [\n        0x00183B60,\n        0x00183B6E,\n        0x00183B6F,\n    ]",
            SOURCE,
        )
        self.assertIn(
            '"internal_branch_status": "EXACT_183AF1_INTERNAL_TARGET_BOUNDARY_PROVEN"',
            SOURCE,
        )

    def test_indirect_call_is_exact_but_target_semantics_stay_unresolved(self):
        self.assertIn('(0x00183AFD, "ff d6", "call esi")', SOURCE)
        self.assertIn("indirect_call_site_rva = 0x00183AFD", SOURCE)
        self.assertIn(
            'indirect_call_site_bytes == bytes.fromhex("ff d6")',
            SOURCE,
        )
        self.assertIn(
            '"call_semantics": "EXACT_INDIRECT_CALL_ESI_AT_183AFD_TARGET_SEMANTICS_UNRESOLVED"',
            SOURCE,
        )

    def test_provenance_and_raw_rel32_census_fail_closed(self):
        self.assertIn(
            'predecessor["status"] == "EXACT_183A8A_TO_183AC7_CONTROL_FLOW_WITH_183AC7_CUT_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_183AC7_TO_183B07_PROVENANCE_CAPTURED"',
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
            '"EXACT_183AC7_TO_183B07_CONTROL_FLOW_BOUNDARY_PROVEN"',
            SOURCE,
        )

    def test_report_binding_and_failure_guards_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_99_provenance"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_99_prefix_proof"',
            SOURCE,
        )
        self.assertIn("gf_target_c_helper_1_third_callee_continuation_99=", SOURCE)
        self.assertIn("gf_target_c_helper_1_third_callee_continuation_99_proof=", SOURCE)
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_99_provenance=FAILED",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_99_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
