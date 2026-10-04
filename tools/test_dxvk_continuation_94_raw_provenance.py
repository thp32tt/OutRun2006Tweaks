#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00366/F120."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation94RawProvenanceTests(unittest.TestCase):
    def test_canonical_window_is_declared_and_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_RVA = 0x0018398E",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_PROBE_END_RVA = 0x001839CE",
            SOURCE,
        )
        self.assertIn(
            "fe 4c 03 04 75 21 8b 4d 08 21 31 eb 1a 8d 4b e0",
            SOURCE,
        )
        self.assertIn(
            "89 4e 04 8b 4d 0c 8b 71 04 8b 49 08 89 4e 08 8b",
            SOURCE,
        )

    def test_f119_boundary_and_all_forward_debt_are_fail_closed(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_93_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            'predecessor["status"] == "EXACT_18394E_TO_18398E_CONTROL_FLOW_CAPTURE_BOUNDARY_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            "0x0018399B, 0x001839B5, 0x001839CD, 0x001839D2, 0x00183B6F",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_94_INHERITED_FORWARD_TARGETS = (",
            SOURCE,
        )

    def test_exact_probe_is_raw_only_and_preserves_overlap_debt(self):
        self.assertIn("exact_bytes_match = probe == expected_probe", SOURCE)
        self.assertIn(
            '"EXACT_EXE_18398E_TO_1839CE_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY"',
            SOURCE,
        )
        self.assertIn('"call_semantics": "UNRESOLVED"', SOURCE)
        self.assertIn(
            '"continuation_status": "RAW_CAPTURE_REQUIRES_EXACT_DECODE_WITH_TRAILING_8B_OVERLAP"',
            SOURCE,
        )
        self.assertIn('"ownership_effect": "NONE"', SOURCE)

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_94_provenance"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_94=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_94_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
