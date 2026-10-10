#!/usr/bin/env python3
"""Smoke tests for Check-DX11StateTokenConsistency.py.

Repository-only validation; no DX11 runtime or GPU dependency is required.
"""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile


MODULE_PATH = pathlib.Path(__file__).with_name("Check-DX11StateTokenConsistency.py")


def load_checker():
    spec = importlib.util.spec_from_file_location("dx11_state_checker", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_token_scan_smoke() -> None:
    checker = load_checker()
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "fixture.txt"
        path.write_text("D3D_RASTER_STATE", encoding="utf-8")
        assert checker.scan_text(path.read_text(), str(path)) == []


def test_duplicate_detection_contract() -> None:
    checker = load_checker()
    errors = checker.scan_text("D3D_BLEND_STATE_ALPHA", "first")
    errors.extend(checker.scan_text("D3D_BLEND_STATE_ALPHA", "second"))
    assert any("D3D_BLEND_STATE_ALPHA" in item for item in errors)
