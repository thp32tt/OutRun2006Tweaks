#!/usr/bin/env python3
"""Regression checks for DXVK continuation evidence boundaries."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "validate_dxvk_continuation_window.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="dxvk-window-") as temp:
        binary = Path(temp) / "sample.bin"
        report = Path(temp) / "report.json"
        binary.write_bytes(bytes.fromhex("00 66 0f 54 1d 20 91 61 ff"))
        subprocess.run([sys.executable, str(TOOL), str(binary), "--offset", "0x1", "--end", "0x8", "--report", str(report)], check=True)
        if '"matches": true' not in report.read_text(encoding="utf-8"):
            raise AssertionError("validated overlap was not detected")
    print("DXVK continuation window validator regression tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
