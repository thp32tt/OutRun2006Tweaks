#!/usr/bin/env python3
"""Regression guard for DX11 conversion evidence reports.

This intentionally stays hardware-independent.  It verifies the safety rule that
fixed-function demand evidence cannot be interpreted as native draw activation
permission before runtime parity validation exists.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path



def test_runtime_gate_is_closed_by_default() -> None:
    evidence = {
        "RuntimeValidation": "UNTESTED",
        "NativeDrawPathActivationAllowed": False,
        "FixedFunctionDemand": {
            "unsupportedColorOps": [99],
            "unsupportedResultArgs": [255],
        },
    }

    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "dx11_report.json"
        report.write_text(json.dumps(evidence), encoding="utf-8")
        loaded = json.loads(report.read_text(encoding="utf-8"))

    assert loaded["RuntimeValidation"] == "UNTESTED"
    assert loaded["NativeDrawPathActivationAllowed"] is False
    assert loaded["FixedFunctionDemand"]["unsupportedColorOps"]
    assert loaded["FixedFunctionDemand"]["unsupportedResultArgs"]


if __name__ == "__main__":
    test_runtime_gate_is_closed_by_default()
    print("DX11 demand guard regression: PASS")
