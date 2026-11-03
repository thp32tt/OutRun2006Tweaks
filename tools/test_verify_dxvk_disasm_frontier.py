#!/usr/bin/env python3
"""Regression checks for DXVK frontier manifest guards."""

import json
import subprocess
import sys
from pathlib import Path


def run_case(tmp_path: Path, manifest: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "frontier.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "tools/verify_dxvk_disasm_frontier.py", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_required_overlap_without_bytes_fails(tmp_path: Path) -> None:
    result = run_case(
        tmp_path,
        {
            "proof_start_rva": "0x182F7E",
            "proof_end_rva": "0x182FBE",
            "runtime_validation": "UNTESTED",
            "capture_edge_matches": True,
            "overlap_required": True,
        },
    )
    assert result.returncode != 0


def test_capture_and_overlap_contract_passes(tmp_path: Path) -> None:
    result = run_case(
        tmp_path,
        {
            "proof_start_rva": "0x182F7E",
            "proof_end_rva": "0x182FBE",
            "runtime_validation": "UNTESTED",
            "capture_edge_matches": True,
            "overlap_required": True,
            "overlap_bytes": "66 0f 54 1d 20 91 61",
        },
    )
    assert result.returncode == 0
