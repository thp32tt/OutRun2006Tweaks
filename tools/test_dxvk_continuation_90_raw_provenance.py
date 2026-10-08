#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00352/F112."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation90RawProvenanceTests(unittest.TestCase):
    def test_exact_boundary_window_is_declared_and_pinned(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_RVA = 0x0018388F",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_PROBE_END_RVA = 0x001838CF",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_EXPECTED_BYTES = bytes.fromhex(",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_INHERITED_FORWARD_TARGETS = ()",
            SOURCE,
        )

    def test_predecessor_exact_boundary_and_empty_debt_are_fail_closed(self):
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_89_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            'predecessor["status"] == "EXACT_18384F_TO_18388F_CONTROL_FLOW_PROVEN"',
            SOURCE,
        )
        self.assertIn('predecessor["prefix_end_rva"] == target_rva', SOURCE)
        self.assertIn('predecessor["capture_end_is_instruction_boundary"]', SOURCE)
        self.assertIn('predecessor["unresolved_forward_targets"] == []', SOURCE)

    def test_full_canonical_probe_is_required(self):
        self.assertIn(
            "expected_probe = GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_90_EXPECTED_BYTES",
            SOURCE,
        )
        self.assertIn("exact_bytes_match = probe == expected_probe", SOURCE)
        self.assertIn("and exact_bytes_match", SOURCE)
        self.assertIn('"exact_bytes_match": exact_bytes_match', SOURCE)

    def test_raw_census_and_semantic_quarantine_are_preserved(self):
        self.assertIn(
            "collect_raw_inbound_rel32_candidates(pe, target_rva)",
            SOURCE,
        )
        self.assertIn(
            "collect_raw_rel32_call_candidates(",
            SOURCE,
        )
        self.assertIn(
            '"semantic_effect": "UNRESOLVED_CONTINUATION_BYTES_ONLY"',
            SOURCE,
        )
        self.assertIn('"call_semantics": "UNRESOLVED"', SOURCE)
        self.assertIn('"ownership_effect": "NONE"', SOURCE)

    def test_provenance_is_reported_and_guarded(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_90_provenance",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_18388F_TO_1838CF_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_90_provenance"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_90_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
