#!/usr/bin/env python3
"""Small DX11 conversion-lane static contract checker.

This intentionally does not enable the native draw path.  It provides a cheap
CI/local static guard for conversion work when runtime hardware is unavailable.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


REQUIRED = {
    "pipeline_translation": (
        ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp",
        [
            "PipelineUnsupported",
            "translate",
        ],
    ),
    "runtime_census": (
        ROOT / "src" / "vr" / "d3d11" / "runtime_census.cpp",
        [
            "signature",
            "hash",
        ],
    ),
    "fixed_function_probe": (
        ROOT / "tools" / "dx11_fixed_function_pipeline_probe.cpp",
        [
            "PASS",
        ],
    ),
}


def main() -> None:
    missing = []
    for name, (path, markers) in REQUIRED.items():
        if not path.exists():
            missing.append(f"{name}:missing:{path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                missing.append(f"{name}:missing-marker:{marker}")

    if missing:
        raise SystemExit("DX11 conversion contract drift: " + ", ".join(missing))

    print("DX11 conversion static contract: PASS")


if __name__ == "__main__":
    main()
