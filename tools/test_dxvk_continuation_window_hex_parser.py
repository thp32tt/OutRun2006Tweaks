#!/usr/bin/env python3
"""Regression coverage for DXVK continuation-window hex normalization.

This test is intentionally source/static only. It verifies that evidence windows
with human-formatted byte spacing normalize identically to compact byte strings.
Runtime validation remains outside this test's scope.
"""

from pathlib import Path


def parse_hex_window(value: str) -> bytes:
    return bytes.fromhex(" ".join(value.split()))


def test_formatted_and_compact_hex_are_identical() -> None:
    formatted = "66 0f 54 1d 20 91 61"
    compact = "660f541d209161"
    assert parse_hex_window(formatted) == parse_hex_window(compact)


def test_parser_rejects_non_hex_input() -> None:
    try:
        parse_hex_window("66 zz 54")
    except ValueError:
        return
    raise AssertionError("invalid evidence bytes must fail closed")


if __name__ == "__main__":
    test_formatted_and_compact_hex_are_identical()
    test_parser_rejects_non_hex_input()
    print("dxvk continuation hex parser regression: PASS")
