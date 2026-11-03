#!/usr/bin/env python3
"""Regression tests for the DXVK provenance window static contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE = Path(__file__).with_name("validate_dxvk_provenance_window.py")
spec = importlib.util.spec_from_file_location("validate_dxvk_provenance_window", MODULE)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_valid_window_is_accepted() -> None:
    assert module.validate(
        {
            "start_rva": "0x100",
            "end_rva": "0x120",
            "overlap_bytes": "66 0f 54",
            "branch_targets": ["0x110->0x115"],
        }
    ) == []


def test_semantic_promotion_is_rejected() -> None:
    assert "semantic promotion is forbidden for provenance-only evidence" in module.validate(
        {
            "start_rva": "0x100",
            "end_rva": "0x120",
            "semantic_promotion": True,
        }
    )


def test_reversed_window_is_rejected() -> None:
    assert "invalid RVA ordering" in module.validate(
        {
            "start_rva": "0x120",
            "end_rva": "0x100",
        }
    )


def test_branch_target_format_is_checked() -> None:
    assert "invalid branch target format" in module.validate(
        {
            "start_rva": "0x100",
            "end_rva": "0x120",
            "branch_targets": ["bad-target"],
        }
    )


def test_required_overlap_is_checked() -> None:
    assert "required_overlap bytes mismatch" not in module.validate(
        {
            "start_rva": "0x100",
            "end_rva": "0x120",
            "overlap_bytes": "66 0f 54",
            "required_overlap_bytes": "66 0f 54",
        }
    )


def test_invalid_hex_overlap_is_rejected() -> None:
    assert "invalid overlap byte encoding" in module.validate(
        {
            "start_rva": "0x100",
            "end_rva": "0x120",
            "overlap_bytes": "gg",
        }
    )
