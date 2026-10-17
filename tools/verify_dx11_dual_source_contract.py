#!/usr/bin/env python3
"""Fail closed when DX11 dual-source blend claims exceed shader output evidence."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "src" / "vr" / "d3d11" / "state_translation.cpp"
PIPELINE = ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp"
PIPELINE_HPP = ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.hpp"
SEMANTIC_SMOKE = ROOT / "tools" / "dx11_fixed_function_shader_semantics.cpp"
RUNTIME_CENSUS = ROOT / "src" / "vr" / "d3d11" / "runtime_census.cpp"
CENSUS_ANALYZER = ROOT / "tools" / "analyze_dx11_census.py"
CENSUS_ANALYZER_TEST = ROOT / "tools" / "test_analyze_dx11_census.py"


def require_fail_closed_case(state: str, d3d9: str, d3d11: str) -> None:
    case_token = f"case {d3d9}:"
    expected = f"case {d3d9}: return {{{d3d11}, false}};"
    if state.count(case_token) != 1:
        raise SystemExit(
            f"dual-source blend contract requires exactly one {d3d9} case"
        )
    if expected not in state:
        raise SystemExit(
            f"dual-source blend case is not fail-closed: expected {expected}"
        )


def main() -> None:
    state = STATE.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")
    pipeline_hpp = PIPELINE_HPP.read_text(encoding="utf-8")
    semantic_smoke = SEMANTIC_SMOKE.read_text(encoding="utf-8")
    runtime_census = RUNTIME_CENSUS.read_text(encoding="utf-8")
    census_analyzer = CENSUS_ANALYZER.read_text(encoding="utf-8")
    census_analyzer_test = CENSUS_ANALYZER_TEST.read_text(encoding="utf-8")

    required_blocker_contract = [
        (
            "PipelineUnsupportedDualSourceBlend = 1u << 12",
            pipeline_hpp,
            "dedicated dual-source unsupported bit",
        ),
        (
            "bool is_dual_source_blend_factor(D3DBLEND value) noexcept",
            pipeline,
            "dual-source D3D9 factor classifier",
        ),
        (
            "value == D3DBLEND_SRCCOLOR2",
            pipeline,
            "SRCCOLOR2 classifier membership",
        ),
        (
            "value == D3DBLEND_INVSRCCOLOR2",
            pipeline,
            "INVSRCCOLOR2 classifier membership",
        ),
        (
            "is_dual_source_blend_factor(sourceBlendValue)",
            pipeline,
            "source-factor dual-source detection",
        ),
        (
            "is_dual_source_blend_factor(destinationBlendValue)",
            pipeline,
            "destination-factor dual-source detection",
        ),
        (
            "if (rt.BlendEnable && dualSourceBlendRequested)",
            pipeline,
            "dual-source blocker is gated by active blending",
        ),
        (
            "out.unsupported |= PipelineUnsupportedDualSourceBlend;",
            pipeline,
            "dedicated dual-source blocker propagation",
        ),
    ]
    missing_blocker_contract = [
        meaning
        for token, source, meaning in required_blocker_contract
        if token not in source
    ]
    if missing_blocker_contract:
        raise SystemExit(
            "dual-source blend blocker provenance missing: "
            + ", ".join(missing_blocker_contract)
        )

    require_fail_closed_case(
        state, "D3DBLEND_SRCCOLOR2", "D3D11_BLEND_SRC1_COLOR"
    )
    require_fail_closed_case(
        state, "D3DBLEND_INVSRCCOLOR2", "D3D11_BLEND_INV_SRC1_COLOR"
    )

    # The current native fixed-function generator emits one color target only.
    # Any second target means the dual-source exactness decision must be reviewed
    # together with actual shader linkage before activation can move forward.
    if "SV_Target1" in pipeline:
        raise SystemExit(
            "second pixel output evidence appeared in native shader generator; "
            "review dual-source blend exactness before activation"
        )

    required_semantic_smokes = [
        "SRCCOLOR2 source blend must remain fail-closed without SV_Target1",
        "INVSRCCOLOR2 source blend must remain fail-closed without SV_Target1",
        "SRCCOLOR2 destination blend must remain fail-closed without SV_Target1",
        "INVSRCCOLOR2 destination blend must remain fail-closed without SV_Target1",
        "SRCCOLOR2 source blend must report dedicated dual-source blocker",
        "INVSRCCOLOR2 source blend must report dedicated dual-source blocker",
        "SRCCOLOR2 destination blend must report dedicated dual-source blocker",
        "INVSRCCOLOR2 destination blend must report dedicated dual-source blocker",
        "disabled alpha blending must ignore dormant dual-source factors",
    ]
    missing_smokes = [
        token for token in required_semantic_smokes if token not in semantic_smoke
    ]
    if missing_smokes:
        raise SystemExit(
            "dual-source blend semantic smoke coverage missing: "
            + ", ".join(missing_smokes)
        )

    census_contract = {
        "DualSourceBlendSamples": (runtime_census, "runtime SRC1 demand counter"),
        "dualSourceBlend[any={}": (runtime_census, "runtime SRC1 summary"),
        '"VR DX11 R120"': (census_analyzer, "current R120 log recognition"),
        "dualSourceBlendAny": (census_analyzer, "SRC1 analyzer fields"),
        '"DualSourceBlend"': (census_analyzer, "SRC1 analyzer evidence block"),
        '"ExhaustiveNoUsageObserved"': (
            census_analyzer, "exhaustive-only zero-demand proof"
        ),
        "src1_demand = run_case(": (
            census_analyzer_test, "positive SRC1 demand analyzer regression"
        ),
        '"ExhaustiveNoUsageObserved"] is True': (
            census_analyzer_test, "exhaustive zero-demand analyzer regression"
        ),
    }
    missing_census_contract = [
        meaning
        for token, (source, meaning) in census_contract.items()
        if token not in source
    ]
    if missing_census_contract:
        raise SystemExit(
            "dual-source blend census evidence drift: "
            + ", ".join(missing_census_contract)
        )

    print(
        "DX11 dual-source blend contract: PASS "
        "(fail-closed, single-target shader generator, exact demand census wired)"
    )


if __name__ == "__main__":
    main()
