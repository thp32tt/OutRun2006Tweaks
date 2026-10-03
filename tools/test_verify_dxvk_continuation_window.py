#!/usr/bin/env python3
"""Static regression checks for DXVK continuation evidence validation."""

from __future__ import annotations

import unittest

from verify_dxvk_continuation_window import validate, validate_window


class VerifyDxvkContinuationWindowTests(unittest.TestCase):
    def test_accepts_matching_hex_window_prefix(self) -> None:
        record = {
            "start_rva": "0x100",
            "end_rva": "0x104",
            "overlap_bytes": "8B FF 55",
            "window_bytes": "8B FF 55 90",
            "instruction_count": 1,
        }
        self.assertEqual(validate(record), [])

    def test_rejects_window_without_overlap_prefix(self) -> None:
        record = {
            "start_rva": "0x100",
            "end_rva": "0x104",
            "overlap_bytes": "8B FF 55",
            "window_bytes": "90 90 90 90",
            "instruction_count": 1,
        }
        self.assertIn("invalid:overlap-mismatch", validate(record))

    def test_rejects_non_hex_bytes(self) -> None:
        record = {
            "start_rva": "0x100",
            "end_rva": "0x104",
            "overlap_bytes": "not-bytes",
            "window_bytes": "8B FF 55 90",
            "instruction_count": 1,
        }
        self.assertIn("invalid:overlap-bytes", validate(record))

    def test_rejects_invalid_branch_target_rva(self) -> None:
        record = {
            "start_rva": "0x100",
            "end_rva": "0x104",
            "overlap_bytes": "8B FF 55",
            "window_bytes": "8B FF 55 90",
            "instruction_count": 1,
            "branch_targets": [{"rva": "bad"}],
        }
        self.assertIn("invalid:branch-target-0-rva", validate(record))

    def test_rejects_window_length_that_does_not_match_rva_range(self) -> None:
        record = {
            "start_rva": "0x100",
            "end_rva": "0x105",
            "overlap_bytes": "8B FF 55",
            "window_bytes": "8B FF 55 90",
            "instruction_count": 1,
        }
        self.assertIn("invalid:window-length", validate(record))

    def test_cli_helper_requires_exact_range_coverage(self) -> None:
        result = validate_window(
            "0x100",
            "0x105",
            bytes.fromhex("8B FF 55 90"),
            bytes.fromhex("8B FF 55"),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["range_matches_window"])
        self.assertEqual(result["runtime_validation"], "UNTESTED")


if __name__ == "__main__":
    unittest.main()
