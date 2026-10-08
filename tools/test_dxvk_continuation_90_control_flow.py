#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00354/F113."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation90ControlFlowTests(unittest.TestCase):
    def test_exact_prefix_and_cut_edge_are_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_PREFIX_END_RVA = 0x001838CE",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_INCOMPLETE_RVA = 0x001838CE",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_INCOMPLETE_BYTES = bytes.fromhex("73")',
            SOURCE,
        )
        self.assertIn(
            '(0x001838C9, "bb 00 00 00 80", "mov ebx, 0x80000000")',
            SOURCE,
        )

    def test_four_direct_branches_and_forward_debt_are_fail_closed(self):
        for marker in (
            "(0x00183892, 0x00183B6F)",
            "(0x001838B0, 0x00183926)",
            "(0x001838B9, 0x001838BE)",
            "(0x001838C4, 0x00183908)",
        ):
            self.assertIn(marker, SOURCE)
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_EXPECTED_FORWARD_TARGET_RVAS = (",
            SOURCE,
        )
        for target in ("0x00183908", "0x00183926", "0x00183B6F"):
            self.assertIn(target, SOURCE)
        self.assertIn(
            "unresolved_forward_targets = [0x00183908, 0x00183926, 0x00183B6F]",
            SOURCE,
        )

    def test_full_raw_provenance_and_empty_call_census_are_required(self):
        self.assertIn(
            'provenance["status"] == "EXACT_EXE_18388F_TO_1838CF_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn('provenance["exact_bytes_match"]', SOURCE)
        self.assertIn(
            'raw_call_census_empty = not provenance["raw_outbound_rel32_candidates"]',
            SOURCE,
        )
        self.assertIn(
            'expected_external_targets = {0x00183908, 0x00183926, 0x00183B6F}',
            SOURCE,
        )

    def test_proof_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_90_prefix_proof",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_18388F_TO_1838CE_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_90_prefix_proof"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_90_prefix_proof=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
