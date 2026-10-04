#!/usr/bin/env python3
"""Regression tests for exact DXVK disassembly evidence window verification."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_dxvk_disasm_window.py"


def run_case(name: str, evidence: dict, start: str, end: str, expected_ok: bool) -> None:
    with tempfile.TemporaryDirectory(prefix=f"dxvk-window-{name}-") as temp:
        path = Path(temp) / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(TOOL), "--evidence", str(path), "--start-rva", start, "--end-rva", end],
            capture_output=True,
            text=True,
        )
        if (result.returncode == 0) is not expected_ok:
            raise AssertionError(f"{name}: unexpected return {result.returncode}: {result.stderr}")


def main() -> int:
    run_case(
        "validated-window",
        {"proof_start_rva": "0x00182f7e", "proof_end_rva": "0x00182fbe", "overlap_matches": True},
        "0x00182F7E",
        "0x00182FBE",
        True,
    )
    run_case(
        "wrong-window",
        {"proof_start_rva": "0x00182f7e", "proof_end_rva": "0x00182fbe", "overlap_matches": True},
        "0x00182F7F",
        "0x00182FBE",
        False,
    )
    run_case(
        "failed-overlap",
        {"proof_start_rva": "0x00182f7e", "proof_end_rva": "0x00182fbe", "overlap_matches": False},
        "0x00182F7E",
        "0x00182FBE",
        False,
    )
    print("DXVK disassembly window verifier tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
