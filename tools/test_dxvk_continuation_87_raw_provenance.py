#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00340/F106."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation87RawProvenanceTests(unittest.TestCase):
    def test_mandatory_overlap_window_is_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_RVA = 0x001837D5",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_PROBE_END_RVA = 0x00183815",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_87_OVERLAP_BYTES = bytes.fromhex("ff 35 5c bc")',
            SOURCE,
        )

    def test_predecessor_debt_is_inherited_fail_closed(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_86_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            'predecessor["status"] == "EXACT_183799_TO_1837D5_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn("0x001837E1", SOURCE)
        self.assertIn("0x001837E4", SOURCE)
        self.assertIn(
            '"expected_inherited_forward_targets": inherited_targets',
            SOURCE,
        )

    def test_raw_provenance_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_87_provenance",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_1837D5_TO_183815_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_87_provenance"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_87_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
