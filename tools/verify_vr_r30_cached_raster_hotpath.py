#!/usr/bin/env python3
"""DX9Ex R30 perspective UI cached-state and XYZRHW viewport hotpath guard."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R29 = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"
API = ROOT / "src/vr/core/r29_owner_api.hpp"
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def body(text, signature):
    at = text.index(signature)
    first = text.index("{", at)
    depth = 0
    for at in range(first, len(text)):
        if text[at] == "{":
            depth += 1
        elif text[at] == "}":
            depth -= 1
            if depth == 0:
                return text[first:at + 1]
    raise ValueError(signature)


def check(r29, api, r30):
    try:
        local = body(r29, "inline bool TryGetEffectTelemetrySnapshot(")
        bridge = body(r29, "bool R29OwnerTryGetEffectTelemetrySnapshot(")
        classify = body(r30, "R30ScreenSpaceKind R30ClassifyScreenSpacePass(")
        xyz = body(r30, "bool R30PrepareXyzrhwState(")
        header = api[api.index("struct R29OwnerEffectTelemetrySnapshot"):
                     api.index("bool R29OwnerTryGetEffectTelemetrySnapshot(")]
        if "DWORD zEnable = D3DZB_TRUE;" not in header:
            return False
        if not all(term in local for term in (
            "if (!R29EffectCacheCurrent())",
            "out.alphaBlend = R29Effect.alphaBlend;",
            "out.alphaTest = R29Effect.alphaTest;",
            "out.zEnable = R29Effect.zEnable;")):
            return False
        if "out.zEnable = lower.zEnable;" not in bridge:
            return False
        use = classify.index("R29OwnerTryGetEffectTelemetrySnapshot(effect)")
        gate = classify.index("if (!haveCachedEffect &&")
        if not use < gate:
            return False
        if not all(term in classify for term in (
            "haveCachedEffect ? effect.zEnable : D3DZB_TRUE",
            "haveCachedEffect ? effect.alphaBlend : FALSE",
            "haveCachedEffect ? effect.alphaTest : FALSE")):
            return False
        fallback = classify[gate:classify.index("return R30ScreenSpaceKind::None;", gate)]
        if not all(term in fallback for term in (
            "D3DRS_ZENABLE", "D3DRS_ALPHABLENDENABLE",
            "D3DRS_ALPHATESTENABLE", "FAILED(device->GetRenderState(")):
            return False
        start = xyz.index("R29OwnerEnsureStereoResources(device)")
        fallback_vp = xyz.index("FAILED(device->GetViewport(&state.viewport))")
        if not start < xyz.index("!R29OwnerTryGetTrackedViewport(state.viewport)") < fallback_vp:
            return False
        if "(!R29OwnerTryGetTrackedViewport(state.viewport) &&" not in xyz:
            return False
        return True
    except ValueError:
        return False


def main():
    r29, api, r30 = (
        p.read_text(encoding="utf-8") for p in (R29, API, R30)
    )
    assert WORKFLOW.read_text(encoding="utf-8").count(
        "tools/verify_vr_r30_cached_raster_hotpath.py") == 2
    assert check(r29, api, r30), "R30 cached-state/viewport contract broken"
    changes = (
        (r29.replace("out.zEnable = lower.zEnable;",
                     "out.zEnable = D3DZB_TRUE;", 1), api, r30),
        (r29.replace("out.zEnable = R29Effect.zEnable;",
                     "out.zEnable = R29Effect.zWrite;", 1), api, r30),
        (r29, api, r30.replace(
            "R29OwnerTryGetEffectTelemetrySnapshot(effect)",
            "false", 1)),
        (r29, api, r30.replace(
            "if (!haveCachedEffect &&",
            "if (false &&", 1)),
        (r29, api, r30.replace(
            "haveCachedEffect ? effect.alphaTest : FALSE",
            "haveCachedEffect ? effect.alphaBlend : FALSE", 1)),
        (r29, api, r30.replace(
            "D3DRS_ALPHATESTENABLE, &alphaTest",
            "D3DRS_ALPHABLENDENABLE, &alphaTest", 1)),
        (r29, api, r30.replace(
            "!R29OwnerTryGetTrackedViewport(state.viewport)",
            "false", 1)),
    )
    for i, candidate in enumerate(changes, 1):
        assert candidate != (r29, api, r30), f"mutation {i} not applied"
        assert not check(*candidate), f"mutation {i} escaped"
    print("PASS DX9Ex R30 cached raster hotpath + 7 destructive regressions")


if __name__ == "__main__":
    main()
