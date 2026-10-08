#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00348/F110."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation89RawProvenanceTests(unittest.TestCase):
    def test_mandatory_overlap_window_is_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_RVA = 0x0018384F",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_PROBE_END_RVA = 0x0018388F",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_INHERITED_FORWARD_TARGETS = (",
            SOURCE,
        )

    def test_predecessor_forward_target_debt_is_inherited_fail_closed(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_88_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            "predecessor[\"status\"] == \"EXACT_183810_TO_18384F_CONTROL_FLOW_CAPTURE_EDGE_PROVEN\"",
            SOURCE,
        )
        self.assertIn(
            "predecessor[\"unresolved_forward_targets\"] == [0x00183854]",
            SOURCE,
        )

    def test_full_canonical_probe_is_required(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_89_EXPECTED_BYTES = bytes.fromhex(",
            SOURCE,
        )
        self.assertIn("exact_bytes_match = probe == expected_probe", SOURCE)
        self.assertIn("and exact_bytes_match", SOURCE)
        self.assertIn("\"exact_bytes_match\": exact_bytes_match", SOURCE)

    def test_raw_provenance_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_89_provenance",
            SOURCE,
        )
        self.assertIn(
            "\"EXACT_EXE_18384F_TO_18388F_PROVENANCE_CAPTURED\"",
            SOURCE,
        )
        self.assertIn(
            "\"guarded_gf_target_c_helper_1_third_callee_continuation_89_provenance\"",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_89_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
