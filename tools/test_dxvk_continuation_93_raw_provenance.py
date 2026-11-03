#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00362/F118."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation93RawProvenanceTests(unittest.TestCase):
    def test_canonical_window_is_declared_and_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_RVA = 0x0018394E",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_PROBE_END_RVA = 0x0018398E",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_EXPECTED_BYTES = bytes.fromhex(",
            SOURCE,
        )

    def test_predecessor_boundary_and_forward_debt_are_fail_closed(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_92_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            'predecessor["status"] == "EXACT_18390E_TO_18394E_CONTROL_FLOW_CAPTURE_BOUNDARY_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            'predecessor["unresolved_forward_targets"] == [0x001839D2, 0x00183B6F]',
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_93_INHERITED_FORWARD_TARGETS = (",
            SOURCE,
        )

    def test_exact_probe_and_raw_census_only(self):
        self.assertIn("exact_bytes_match = probe == expected_probe", SOURCE)
        self.assertIn(
            '"EXACT_EXE_18394E_TO_18398E_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY"',
            SOURCE,
        )
        self.assertIn('"call_semantics": "UNRESOLVED"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_93_provenance"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_93=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_93_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
