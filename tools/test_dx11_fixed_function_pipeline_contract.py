#!/usr/bin/env python3
"""Static contract checks for DX11 fixed-function pipeline ownership.

The test keeps the conversion boundary fail-closed: alpha-test migration is
only allowed after complete fixed-function observation and shader generation.
It intentionally does not enable runtime rendering.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "src" / "vr" / "d3d11" / "fixed_function_pipeline.cpp"

    if not source.exists():
        raise SystemExit("missing DX11 fixed function pipeline source")

    text = source.read_text(encoding="utf-8")

    required = [
        "translate_fixed_function_pipeline_with_shader_semantics",
        "if (!fixedFunctionObserved)",
        "fixedFunctionStateObservationComplete",
        "if (!out.pixelShader.generated())",
        "source.complete &&",
        "out.alphaTestOwnedByPixelShader = true",
    ]

    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit("fixed function ownership contract missing: " + ", ".join(missing))

    print("DX11 fixed function ownership contract: OK")


if __name__ == "__main__":
    main()
