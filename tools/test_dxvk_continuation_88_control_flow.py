#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00346/F109."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation88ControlFlowTests(unittest.TestCase):
    def test_exact_prefix_and_cut_edge_are_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_PREFIX_END_RVA = 0x0018384F",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_INCOMPLETE_RVA = 0x0018384F",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_INCOMPLETE_BYTES = bytes.fromhex("72")',
            SOURCE,
        )
        self.assertIn(
            '(0x00183849, "81 fa 00 00 10 00", "cmp edx, 0x100000")',
            SOURCE,
        )

    def test_forward_jump_is_carried_as_unresolved_debt(self):
        self.assertIn("(0x00183840, 0x00183854)", SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_EXPECTED_FORWARD_TARGET_RVAS = (",
            SOURCE,
        )
        self.assertIn("0x00183854", SOURCE)
        self.assertIn(
            '"unresolved_forward_targets": unresolved_forward_targets',
            SOURCE,
        )

    def test_full_pinned_predecessor_and_empty_call_census_are_required(self):
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_183810_TO_183850_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn('provenance["exact_bytes_match"]', SOURCE)
        self.assertIn(
            'raw_call_census_empty = not provenance["raw_outbound_rel32_candidates"]',
            SOURCE,
        )

    def test_fail_closed_proof_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_88_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_183810_TO_18384F_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_88_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_88_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
