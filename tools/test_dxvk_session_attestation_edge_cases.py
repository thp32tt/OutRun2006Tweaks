#!/usr/bin/env python3
"""Focused regression checks for DXVK creation attestation edge cases."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "analyze_dxvk_session.py"


def run_analyzer(log_line: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="dxvk-attestation-edge-") as temp:
        session = Path(temp)
        (session / "VR_ONE_CLICK_PREFLIGHT.json").write_text(
            json.dumps(
                {
                    "Dxvk": {
                        "Version": "3.1.1",
                        "Provider": {"Sha256": "a" * 64},
                        "ExpectedSha256": "a" * 64,
                    }
                }
            ),
            encoding="utf-8",
        )
        (session / "OutRun_d3d9.log").write_text(
            log_line + "\nDXVK: v3.1.1\n", encoding="utf-8"
        )
        output = session / "summary.json"
        subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--session-dir",
                str(session),
                "--output",
                str(output),
            ],
            check=True,
        )
        return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    common = (
        "VR DXVK R71 census: providerLoaded=1 nonSystem=1 gameLocal=1 "
        "stockInterop=1 D3D9Ex=1 stockHr=0x00000000 exHr=0x00000000 "
    )
    zero = run_analyzer(common + "source=create-device-ex attestation=0")
    assert zero["Status"] == "DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID"

    negative = run_analyzer(common + "source=create-device-ex attestation=-1")
    assert negative["Status"] == "DXVK_DEVICE_CREATION_REATTESTATION_MISSING"

    print("DXVK attestation edge-case regression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
