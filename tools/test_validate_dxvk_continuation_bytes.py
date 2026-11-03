#!/usr/bin/env python3
"""Regression checks for the DXVK continuation byte evidence validator."""

import unittest

from validate_dxvk_continuation_bytes import EXPECTED, validate_window


class TestDXVKContinuationBytes(unittest.TestCase):
    def test_expected_overlap_is_accepted(self):
        validate_window(
            EXPECTED["start_rva"],
            EXPECTED["end_rva"],
            EXPECTED["overlap"] + b"\x90\x90",
        )

    def test_changed_boundary_byte_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(
                EXPECTED["start_rva"],
                EXPECTED["end_rva"],
                b"\x00" + EXPECTED["overlap"][1:],
            )


if __name__ == "__main__":
    unittest.main()
