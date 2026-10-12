#!/usr/bin/env python3
"""R33 DX9Ex: short-circuit disabled stencil readback without stale cache replay."""
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r33.cpp"


def function_body(src: str, name: str) -> str:
    at = src.index(name)
    start = src.index("{", at)
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise AssertionError("Unterminated function: " + name)


def verify(src: str) -> None:
    read = function_body(src, "bool R33ReadDepthStencilWriteState(")
    setter = function_body(src, "HRESULT __stdcall SetRenderStateDestR33(")
    flags = function_body(src, "void R33RefreshWriteFlags(")
    current = function_body(src, "bool R33DepthStencilCacheCurrent(")

    # Z readback is always needed on a tracked depth target. Stencil only
    # needs its enable bit on the common disabled path, the mask on the
    # enabled-but-zero-mask path and all ops on the potentially writing path.
    required = (
        "D3DRS_ZENABLE", "D3DRS_ZWRITEENABLE",
        "if (R32ReviewMainDepthHasStencil())",
        "D3DRS_STENCILENABLE", "if (next.stencilEnable != FALSE)",
        "D3DRS_STENCILWRITEMASK", "if (next.stencilWriteMask != 0)",
        "D3DRS_STENCILFAIL", "D3DRS_STENCILZFAIL", "D3DRS_STENCILPASS",
        "D3DRS_TWOSIDEDSTENCILMODE", "D3DRS_CCW_STENCILFAIL",
        "D3DRS_CCW_STENCILZFAIL", "D3DRS_CCW_STENCILPASS",
        "next.valid = true;",
    )
    at = -1
    for token in required:
        nxt = read.find(token, at + 1)
        assert nxt > at, "stencil read gate missing or out of order: " + token
        at = nxt
    assert read.count("device->GetRenderState(") == 11, "unexpected D3D9 readback coverage"
    assert read.count("R33InvalidateDepthStencilCache();") == 4, "read-failure fail-closed path lost"
    # An untracked depth target legitimately publishes an early empty-state cache.
    # Check the *tracked* read path independently, after every failed getter
    # and fail-closed return, rather than comparing its returns with that early
    # fast-path publication.
    assert read.count("next.valid = true;") == 2, "empty/tracked publication count changed"
    tracked = read.split("if (FAILED(device->GetRenderState(D3DRS_ZENABLE", 1)[1]
    assert tracked.count("next.valid = true;") == 1, "tracked publication missing or duplicated"
    assert tracked.rfind("next.valid = true;") > tracked.rfind("return false;"), (
        "tracked cache published before read validation"
    )
    assert "s.stencilEnable != FALSE &&" in flags
    assert "s.stencilWriteMask != 0 &&" in flags
    assert "s.stencilWritesIfPresent &&" in src, "format-gated stencil write result lost"

    for field, previous, enabled in (
        ("D3DRS_STENCILENABLE", "stencilEnable", "FALSE"),
        ("D3DRS_STENCILWRITEMASK", "stencilWriteMask", "0"),
    ):
        pattern = (
            r"case " + field + r":\s*"
            r"(?:(?!case ).)*?"
            r"if \(R33DepthStencilState\." + previous +
            r" == " + enabled + r" && value != " + enabled + r"\)\s*"
            r"R33InvalidateDepthStencilCache\(\);\s*"
            r"R33DepthStencilState\." + previous + r" = value;"
        )
        assert re.search(pattern, setter, re.S), "stale snapshot re-enable accepted: " + field
    assert "R33RefreshWriteFlags(R33DepthStencilState);" in setter
    assert "R33DepthStencilState.stateBlockApplies ==" in current
    assert "StateBlockTracker::ApplyGeneration()" in current
    assert "R33DepthStencilState.depthGeneration ==" in current


def main() -> None:
    src = SOURCE.read_text(encoding="utf-8")
    verify(src)
    mutations = [
        ("no_disabled_gate", "if (next.stencilEnable != FALSE)", "if (true)"),
        ("inverted_enable", "if (next.stencilEnable != FALSE)", "if (next.stencilEnable == FALSE)"),
        ("no_mask_gate", "if (next.stencilWriteMask != 0)", "if (true)"),
        ("inverted_mask", "if (next.stencilWriteMask != 0)", "if (next.stencilWriteMask == 0)"),
        ("no_enable_invalidation", "if (R33DepthStencilState.stencilEnable == FALSE && value != FALSE)\n                    R33InvalidateDepthStencilCache();", "if (false)\n                    R33InvalidateDepthStencilCache();"),
        ("no_mask_invalidation", "if (R33DepthStencilState.stencilWriteMask == 0 && value != 0)\n                    R33InvalidateDepthStencilCache();", "if (false)\n                    R33InvalidateDepthStencilCache();"),
        ("missing_depth_read", "D3DRS_ZWRITEENABLE, &next.zWrite", "D3DRS_ZENABLE, &next.zWrite"),
        ("no_fail_closed", "R33InvalidateDepthStencilCache();\n                    return false;", "return false;"),
        ("lost_format_gate", "s.stencilWritesIfPresent &&", "true &&"),
        ("missing_tracked_publish", "            next.valid = true;\n            R33RefreshWriteFlags(next);",
         "            R33RefreshWriteFlags(next);"),
    ]
    for name, old, new in mutations:
        assert old in src, "mutation anchor missing: " + name
        mutant = src.replace(old, new, 1)
        try:
            verify(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("undetected negative mutation: " + name)
    # Move (rather than delete) the tracked publish ahead of the stencil reads.
    # There are still two publications; only their ordering is broken. The
    # verifier must distinguish this from the legitimate untracked early return.
    early = src.replace(
        "            next.valid = true;\n            R33RefreshWriteFlags(next);",
        "            R33RefreshWriteFlags(next);", 1
    ).replace(
        "            if (R32ReviewMainDepthHasStencil())",
        "            next.valid = true;\n            if (R32ReviewMainDepthHasStencil())", 1
    )
    assert early != src, "premature tracked publication mutation anchor missing"
    try:
        verify(early)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("undetected premature tracked-cache publication")
    print(f"PASS R33 disabled/zero-mask stencil readback and {len(mutations) + 1} negative mutations")


if __name__ == "__main__":
    main()
