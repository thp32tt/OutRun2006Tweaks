#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00370/F122."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation95RawProvenanceTests(unittest.TestCase):
    def test_canonical_overlap_window_is_declared_and_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_RVA = 0x001839CD",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_PROBE_END_RVA = 0x00183A0D",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_OVERLAP_BYTES = bytes.fromhex("8b")',
            SOURCE,
        )
        self.assertIn(
            "8b 75 0c eb 03 8b 5d 08 83 7d f4 00 75 08 3b da",
            SOURCE,
        )
        self.assertIn(
            "04 3b 4e 08 75 60 8a 4c 02 04 88 4d 0f fe c1 83",
            SOURCE,
        )

    def test_f121_cut_edge_is_consumed_with_three_way_overlap_identity(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_94_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            'predecessor["status"] == "EXACT_18398E_TO_1839CD_CONTROL_FLOW_WITH_1839CD_OVERLAP_PROVEN"',
            SOURCE,
        )
        self.assertIn('predecessor["incomplete_rva"] == target_rva', SOURCE)
        self.assertIn('predecessor["incomplete_matches"]', SOURCE)
        self.assertIn('predecessor["capture_edge_matches"]', SOURCE)
        self.assertIn(
            'predecessor["incomplete_expected_bytes"] == overlap.hex(" ")',
            SOURCE,
        )
        self.assertIn(
            'predecessor["incomplete_actual_bytes"] == overlap.hex(" ")',
            SOURCE,
        )
        self.assertIn("overlap_actual = probe[: len(overlap)]", SOURCE)
        self.assertIn("overlap_matches = overlap_actual == overlap", SOURCE)
        self.assertIn("and predecessor_overlap_matches", SOURCE)

    def test_unresolved_forward_target_debt_is_carried_fail_closed(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_95_INHERITED_FORWARD_TARGETS = (",
            SOURCE,
        )
        self.assertIn(
            'predecessor["unresolved_forward_targets"]\n        == [0x001839CD, 0x001839D2, 0x00183B6F]',
            SOURCE,
        )
        self.assertIn(
            '"inherited_predecessor_forward_targets": predecessor["unresolved_forward_targets"]',
            SOURCE,
        )

    def test_exact_probe_is_raw_only_and_semantics_stay_quarantined(self):
        self.assertIn("exact_bytes_match = probe == expected_probe", SOURCE)
        self.assertIn(
            '"EXACT_EXE_1839CD_TO_183A0D_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY"',
            SOURCE,
        )
        self.assertIn('"call_semantics": "UNRESOLVED"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)
        self.assertIn(
            '"continuation_scope": "EXACT_RAW_BYTES_OVERLAP_INHERITED_FORWARD_TARGETS_AND_REL32_CENSUS_ONLY"',
            SOURCE,
        )

    def test_report_binding_and_failure_guard_exist(self):
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_95_provenance"',
            SOURCE,
        )
        self.assertIn(
            "gf_target_c_helper_1_third_callee_continuation_95=",
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_95_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
