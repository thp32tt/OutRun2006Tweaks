#!/usr/bin/env python3
"""Static regression checks for DXVK continuation evidence validation."""

from __future__ import annotations

import unittest

from verify_dxvk_continuation_window import validate


class VerifyDxvkContinuationWindowTests(unittest.TestCase):
    def test_accepts_matching_hex_window_prefix(self) -> None:
        record = {
            "rva_start": "0x100",
            "rva_end": "0x104",
            "overlap_bytes": "8B FF 55",
            "window_bytes": "8B FF 55 90",
        }
        self.assertEqual(validate(record), [])

    def test_rejects_window_without_overlap_prefix(self) -> None:
        record = {
            "rva_start": "0x100",
            "rva_end": "0x104",
            "overlap_bytes": "8B FF 55",
            "window_bytes": "90 90 90",
        }
        self.assertIn("invalid:overlap-mismatch", validate(record))

    def test_rejects_non_hex_bytes(self) -> None:
        record = {
            "rva_start": "0x100",
            "rva_end": "0x104",
            "overlap_bytes": "not-bytes",
        }
        self.assertIn("invalid:overlap-bytes", validate(record))


if __name__ == "__main__":
    unittest.main()
