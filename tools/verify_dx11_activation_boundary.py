#!/usr/bin/env python3
"""Fail closed if dormant native DX11 readiness work begins routing game draws."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DX11 = ROOT / "src" / "vr" / "d3d11"
ACTIVATION_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inl", ".ipp"}

DRAW_DISPATCH = re.compile(
    r"(?:->|\.)\s*Draw(?:Auto|IndexedInstancedIndirect|InstancedIndirect|IndexedInstanced|Indexed|Instanced)?\s*\("
)


def require_text(path: Path, needles: list[str], label: str) -> str:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{label}: missing dormant-boundary evidence: {missing}")
    return text


def iter_activation_sources() -> list[Path]:
    """Return every C/C++ activation surface under the native DX11 tree."""
    return [
        path
        for path in sorted(DX11.rglob("*"))
        if path.is_file() and path.suffix.lower() in ACTIVATION_SOURCE_SUFFIXES
    ]


def main() -> None:
    # Keep every ID3D11DeviceContext Draw* entry point inside the dormant
    # activation boundary. DrawAuto is easy to omit because it has no explicit
    # vertex-count arguments, so fail closed if the matcher ever regresses.
    draw_dispatch_samples = [
        "context->Draw(1, 0)",
        "context->DrawAuto()",
        "context->DrawIndexed(1, 0, 0)",
        "context->DrawInstanced(1, 1, 0, 0)",
        "context->DrawIndexedInstanced(1, 1, 0, 0, 0)",
        "context->DrawInstancedIndirect(args, 0)",
        "context->DrawIndexedInstancedIndirect(args, 0)",
    ]
    unmatched = [
        sample for sample in draw_dispatch_samples
        if not DRAW_DISPATCH.search(sample)
    ]
    if unmatched:
        raise SystemExit(
            "DX11 draw activation matcher drift: " + ", ".join(unmatched)
        )

    if not DX11.is_dir():
        raise SystemExit("native DX11 source directory is missing")

    # R71-R118 may allocate/translate/compile/bind probe resources, but the
    # native backend is still evidence-only. A real D3D11 Draw* dispatch is an
    # explicit activation event and must not arrive accidentally under a
    # readiness/census task.
    activation_sources = iter_activation_sources()
    if not activation_sources:
        raise SystemExit("native DX11 activation source set is empty")

    required_scan_members = [
        DX11 / "native_backend.cpp",
        DX11 / "native_backend.hpp",
        DX11 / "runtime_census.cpp",
        DX11 / "runtime_census.hpp",
    ]
    missing_scan_members = [
        str(path.relative_to(ROOT))
        for path in required_scan_members
        if path not in activation_sources
    ]
    if missing_scan_members:
        raise SystemExit(
            "DX11 activation source coverage drift: " + ", ".join(missing_scan_members)
        )

    violations: list[str] = []
    approved_diagnostic = DX11 / "live_game_frame_bridge.cpp"
    for path in activation_sources:
        text = path.read_text(encoding="utf-8")
        matches = list(DRAW_DISPATCH.finditer(text))
        if path == approved_diagnostic and matches:
            # This is a deliberate, separately audited activation—not an
            # exemption for arbitrary D3D11 Draw or main gameplay promotion.
            from verify_dx11_first_game_frame_boundary import (
                main as review_first_game_frame_diagnostic,
            )
            review_first_game_frame_diagnostic()
            continue
        for match in matches:
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
            '"ExhaustiveDrawCoverage": exhaustive_draw_coverage',
            '"DiagnosticOnly": True',
            '"EXHAUSTIVE_V1"',
        ],
        "DX11 census analyzer",
    )
    if '"NativeDrawPathActivationAllowed": True' in analyzer:
        raise SystemExit("DX11 census analyzer must not authorize native draws")
    if '"ActivationProof": True' in analyzer:
        raise SystemExit("DX11 census analyzer must not promote diagnostics to activation proof")

    census = require_text(
        DX11 / "runtime_census.cpp",
        [
            "void observe_source_draw(",
            "ExactSamples.fetch_add",
            "signature.fixedFunction &&\n            signature.fixedFunctionStateCoverageExact &&\n            signature.fixedFunctionTranslationReady &&\n            signature.resourceBehaviorExact &&\n            resourcesExact && inputLayoutExact &&\n            signature.outputStateObservationComplete &&\n            signature.shaderReadinessExact &&\n            shaderCompileReadinessExact &&\n            signature.shaderTranslationExact",
            "OUTRUN_VR_DX11_CENSUS_EXHAUSTIVE",
            "census_sample_stride()",
            "census_sampling_scheme()",
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
    # The census is diagnostic-only, but every D3D9 draw family that the active
    # bridge hooks must still feed observe_source_draw. Losing one family would
    # silently weaken readiness evidence while the analyzer continues to report
    # non-exhaustive coverage.
    observed_draw_functions = {
        "DrawPrimitiveDest":
            "make_nonindexed_source_draw_observation(",
        "DrawIndexedPrimitiveDest":
            "make_indexed_source_draw_observation(",
        "DrawPrimitiveUPDest":
            "make_nonindexed_up_source_draw_observation(",
        "DrawIndexedPrimitiveUPDest":
            "make_indexed_up_source_draw_observation(",
    }
    missing_observers: list[str] = []
    for function_name, expected_factory in observed_draw_functions.items():
        marker = f"HRESULT __stdcall {function_name}("
        start = bridge.find(marker)
        if start < 0:
            missing_observers.append(function_name + ":missing-function")
            continue
        next_start = bridge.find("HRESULT __stdcall ", start + len(marker))
        block = bridge[start:] if next_start < 0 else bridge[start:next_start]
        if "outrun::vr::dx11::observe_source_draw(" not in block:
            missing_observers.append(function_name + ":missing-observer")
        if expected_factory not in block:
            missing_observers.append(
                function_name + ":wrong-source-draw-identity"
            )
    if missing_observers:
        raise SystemExit(
            "DX11 census source-draw coverage drift: " + ", ".join(missing_observers)
        )

    draw_hook_wiring = [
        "DrawPrimitiveHook=safetyhook::create_inline(vtable[DrawPrimitiveVtableIndex],DrawPrimitiveDest,disabled);",
        "DrawIndexedPrimitiveHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveVtableIndex],DrawIndexedPrimitiveDest,disabled);",
        "DrawPrimitiveUPHook=safetyhook::create_inline(vtable[DrawPrimitiveUPVtableIndex],DrawPrimitiveUPDest,disabled);",
        "DrawIndexedPrimitiveUPHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveUPVtableIndex],DrawIndexedPrimitiveUPDest,disabled);",
    ]
    missing_hook_wiring = [token for token in draw_hook_wiring if token not in bridge]
    if missing_hook_wiring:
        raise SystemExit(
            "DX11 census D3D9 draw-hook wiring drift: " + ", ".join(missing_hook_wiring)
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
