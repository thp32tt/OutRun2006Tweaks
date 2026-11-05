#!/usr/bin/env python3
"""Static inventory helper for the DX11 conversion lane.

This intentionally does not enable native draw routing. It provides a small
GitHub-only audit surface for conversion work when runtime hardware is not
available.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DX11 = ROOT / "src" / "vr" / "d3d11"


def scan_translation_symbols():
    targets = [
        DX11 / "pipeline_translation.cpp",
        DX11 / "pipeline_translation.hpp",
        DX11 / "fixed_function_pipeline.cpp",
    ]
    patterns = {
        "temp_register": r"TEMP",
        "result_argument": r"RESULTARG|resultarg",
        "activation_boundary": r"NativeDrawPathActive|native.*draw",
        "fail_closed": r"unsupported|fail.?closed",
    }
    result = {}
    for name, pattern in patterns.items():
        result[name] = 0
        for path in targets:
            if path.exists():
                result[name] += len(re.findall(pattern, path.read_text(encoding="utf-8")))
    return result


def main():
    inventory = scan_translation_symbols()
    print("DX11_STATIC_INVENTORY")
    for key in sorted(inventory):
        print(f"{key}={inventory[key]}")
    if inventory["activation_boundary"] == 0:
        raise SystemExit("activation boundary marker missing")


if __name__ == "__main__":
    main()
