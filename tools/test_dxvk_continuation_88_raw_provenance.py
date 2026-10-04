#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00344/F108."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation88RawProvenanceTests(unittest.TestCase):
    def test_mandatory_overlap_window_is_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_RVA = 0x00183810",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_PROBE_END_RVA = 0x00183850",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_OVERLAP_BYTES = bytes.fromhex("83 25 44 bc 98")',
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_88_EXPECTED_BYTES = bytes.fromhex(",
            SOURCE,
        )
        self.assertIn(
            '"eb 12 8b 54 24 04 2b 50 0c 81 fa 00 00 10 00 72"',
            SOURCE,
        )

    def test_predecessor_empty_debt_is_inherited_fail_closed(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_87_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            'predecessor["status"] == "EXACT_1837D5_TO_183810_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            'predecessor["unresolved_forward_targets"] == []',
            SOURCE,
        )
        self.assertIn(
            '"expected_inherited_forward_targets": inherited_targets',
            SOURCE,
        )

    def test_raw_provenance_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_88_provenance",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_183810_TO_183850_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_88_provenance"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_88_provenance=FAILED",
            SOURCE,
        )
        self.assertIn("exact_bytes_match = probe == expected_probe", SOURCE)
        self.assertIn("and exact_bytes_match", SOURCE)
        self.assertIn('"exact_bytes_match": exact_bytes_match', SOURCE)


if __name__ == "__main__":
    unittest.main()
