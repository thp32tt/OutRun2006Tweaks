#!/usr/bin/env python3
"""Fail closed if dormant native DX11 readiness work begins routing game draws."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DX11 = ROOT / "src" / "vr" / "d3d11"

DRAW_DISPATCH = re.compile(
    r"(?:->|\.)\s*Draw(?:IndexedInstancedIndirect|InstancedIndirect|IndexedInstanced|Indexed|Instanced)?\s*\("
)


def require_text(path: Path, needles: list[str], label: str) -> str:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{label}: missing dormant-boundary evidence: {missing}")
    return text


def main() -> None:
    if not DX11.is_dir():
        raise SystemExit("native DX11 source directory is missing")

    # R71-R118 may allocate/translate/compile/bind probe resources, but the
    # native backend is still evidence-only. A real D3D11 Draw* dispatch is an
    # explicit activation event and must not arrive accidentally under a
    # readiness/census task.
    violations: list[str] = []
    for path in sorted(DX11.glob("*.cpp")):
        text = path.read_text(encoding="utf-8")
        for match in DRAW_DISPATCH.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path.relative_to(ROOT)}:{line}:{match.group(0).strip()}")

    if violations:
        raise SystemExit(
            "DX11 native draw activation boundary crossed; explicit activation "
            "review/runtime gate is required before Draw* dispatch is allowed: "
            + "; ".join(violations)
        )

    analyzer = require_text(
        ROOT / "tools" / "analyze_dx11_census.py",
        [
            '"NativeDrawPathActivationAllowed": False',
            '"ActivationProof": False',
            '"ExhaustiveDrawCoverage": False',
            '"DiagnosticOnly": True',
        ],
        "DX11 census analyzer",
    )
    if '"NativeDrawPathActivationAllowed": True' in analyzer:
        raise SystemExit("DX11 census analyzer must not authorize native draws")

    census = require_text(
        DX11 / "runtime_census.cpp",
        [
            "void observe_source_draw(",
            "ExactSamples.fetch_add",
            "resourcesExact && inputLayoutExact && shaderTranslationExact",
        ],
        "DX11 runtime census",
    )
    if DRAW_DISPATCH.search(census):
        raise SystemExit("DX11 census must remain observation-only")

    bridge = require_text(
        ROOT / "src" / "vr" / "d3d9" / "stereo_renderer_r7.inc",
        [
            "vr/d3d11/runtime_census.hpp",
            "observe_source_draw",
        ],
        "validated D3D9 draw bridge",
    )
    forbidden_bridge_tokens = [
        "vr/d3d11/native_backend.hpp",
        "vr/d3d11/native_shared_eye_ring.hpp",
    ]
    leaked = [token for token in forbidden_bridge_tokens if token in bridge]
    if leaked:
        raise SystemExit(
            "validated D3D9 draw bridge gained native DX11 routing dependencies: "
            + ", ".join(leaked)
        )

    print(
        "DX11 dormant activation boundary: OK "
        "(census diagnostic-only; no native D3D11 Draw* dispatch)"
    )


if __name__ == "__main__":
    main()
