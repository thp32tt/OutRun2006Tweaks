#!/usr/bin/env python3
"""Static regression contract for CONVERSION-DXVK-00336/F104."""

from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parent / "analyze_outrun_exe.py").read_text(
    encoding="utf-8"
)


class Continuation86RawProvenanceTests(unittest.TestCase):
    def test_mandatory_overlap_window_is_declared(self):
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_86_RVA = 0x00183799",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_86_PROBE_LEN = 64",
            SOURCE,
        )
        self.assertIn(
            "GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_86_PROBE_END_RVA = 0x001837D9",
            SOURCE,
        )
        self.assertIn(
            'GF_TARGET_C_HELPER_1_THIRD_CALLEE_CONTINUATION_86_OVERLAP_BYTES = bytes.fromhex("39")',
            SOURCE,
        )

    def test_raw_provenance_is_bound_to_f103_capture_edge(self):
        self.assertIn(
            "def collect_guarded_gf_target_c_helper_1_third_callee_continuation_86_provenance",
            SOURCE,
        )
        self.assertIn(
            "predecessor = collect_guarded_gf_target_c_helper_1_third_callee_continuation_85_prefix_proof(pe)",
            SOURCE,
        )
        self.assertIn(
            '"EXACT_EXE_183799_TO_1837D9_PROVENANCE_CAPTURED"',
            SOURCE,
        )
        self.assertIn(
            '"guarded_gf_target_c_helper_1_third_callee_continuation_86_provenance"',
            SOURCE,
        )
        self.assertIn(
            "guarded_gf_target_c_helper_1_third_callee_continuation_86_provenance=FAILED",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
