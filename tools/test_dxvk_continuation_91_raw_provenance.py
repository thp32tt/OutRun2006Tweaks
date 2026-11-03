#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00356/F114."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation91RawProvenanceTests(unittest.TestCase):
    def test_mandatory_overlap_window_is_declared_and_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_RVA = 0x001838CE",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_PROBE_END_RVA = 0x0018390E",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_OVERLAP_BYTES = bytes.fromhex("73")',
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_91_EXPECTED_BYTES = bytes.fromhex(",
            SOURCE,
        )

    def test_predecessor_forward_debt_is_inherited_fail_closed(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_90_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            'predecessor["status"] == "EXACT_18388F_TO_1838CE_CONTROL_FLOW_CAPTURE_EDGE_PROVEN"',
            SOURCE,
        )
        self.assertIn(
            'predecessor["unresolved_forward_targets"] == [0x00183908, 0x00183926, 0x00183B6F]',
            SOURCE,
        )
        for target in ("0x00183908", "0x00183926", "0x00183B6F"):
            self.assertIn(target, SOURCE)

    def test_overlap_and_full_canonical_probe_are_required(self):
        self.assertIn("overlap_actual = probe[: len(overlap)]", SOURCE)
        self.assertIn("overlap_matches = overlap_actual == overlap", SOURCE)
        self.assertIn(
            'predecessor["incomplete_expected_bytes"] == overlap.hex(" ")',
            SOURCE,
        )
        self.assertIn(
            'predecessor["incomplete_actual_bytes"] == overlap.hex(" ")',
            SOURCE,
        )
        self.assertIn("exact_bytes_match = probe == expected_probe", SOURCE)
        self.assertIn("and exact_bytes_match", SOURCE)

    def test_raw_census_semantics_and_guard_are_preserved(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_91_provenance",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_1838CE_TO_18390E_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY"',
            SOURCE,
        )
        self.assertIn('"call_semantics": "UNRESOLVED"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_91_provenance"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_91_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
