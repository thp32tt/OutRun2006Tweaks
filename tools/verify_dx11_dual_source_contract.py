#!/usr/bin/env python3
"""Fail closed when DX11 dual-source blend claims exceed shader output evidence."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "src" / "vr" / "d3d11" / "state_translation.cpp"
PIPELINE = ROOT / "src" / "vr" / "d3d11" / "pipeline_translation.cpp"
SEMANTIC_SMOKE = ROOT / "tools" / "dx11_fixed_function_shader_semantics.cpp"


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
    semantic_smoke = SEMANTIC_SMOKE.read_text(encoding="utf-8")

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
    ]
    missing_smokes = [
        token for token in required_semantic_smokes if token not in semantic_smoke
    ]
    if missing_smokes:
        raise SystemExit(
            "dual-source blend semantic smoke coverage missing: "
            + ", ".join(missing_smokes)
        )

    print(
        "DX11 dual-source blend contract: PASS "
        "(fail-closed, single-target shader generator)"
    )


if __name__ == "__main__":
    main()
