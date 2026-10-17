#!/usr/bin/env python3
"""Static contract probe for DX11 fixed-function CONSTANT handling.

This test intentionally checks evidence boundaries only. It must not be used to
activate NativeDrawPathActive or claim Quest 3/VDXR runtime validation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = (ROOT / "src" / "vr" / "d3d11" / "fixed_function_pipeline.cpp").read_text(
    encoding="utf-8"
)
ANALYZER = (ROOT / "tools" / "analyze_dx11_census.py").read_text(
    encoding="utf-8"
)


def main() -> None:
    required_pipeline_tokens = (
        "D3DTA_CONSTANT",
        "stageConstant",
    )
    missing_pipeline = [token for token in required_pipeline_tokens if token not in PIPELINE]
    if missing_pipeline:
        raise SystemExit("DX11 CONSTANT translator contract missing: " + ", ".join(missing_pipeline))

    required_evidence_tokens = (
        "FFP_TEXTURE_FACTOR_RE",
        "ActivationProof",
        "NativeDrawPathActive",
    )
    missing_evidence = [token for token in required_evidence_tokens if token not in ANALYZER]
    if missing_evidence:
        raise SystemExit("DX11 CONSTANT census boundary missing: " + ", ".join(missing_evidence))


if __name__ == "__main__":
    main()
