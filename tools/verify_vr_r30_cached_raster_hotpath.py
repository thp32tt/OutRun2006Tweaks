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
    if '#include "../state/state_block_tracker.hpp"' not in r30.splitlines():
        return False
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
        # R29's shader identity is valid only while the shared R33
        # StateBlock setter/Apply coverage remains reliable. Avoid the
        # per-draw D3D9 getter on that path, never on unreliable coverage.
        shader_gate = xyz.index(
            "if (!OutRunVR::State::StateBlockTracker::Reliable())")
        shader_live = xyz.index("FAILED(device->GetVertexShader(&shader))")
        # The common XYZRHW gate now validates a declaration-only POSITIONT
        # input in a separate helper before any eye replay. Keep the
        # expensive live shader fallback ordered BEFORE that helper call.
        fvf_gate = xyz.index("if (!R30HasXyzrhwInputLayout(device))")
        layout = body(r30, "bool R30HasXyzrhwInputLayout(")
        if not all(token in layout for token in (
            "device->GetFVF(&fvf)", "D3DFVF_POSITION_MASK",
            "device->GetVertexDeclaration(&declaration)",
            "declaration->GetDeclaration(elements, &count)",
            "declaration->Release();",
            "D3DDECLUSAGE_POSITIONT",
            "D3DDECLTYPE_FLOAT4")):
            return False
        if not (xyz.index("R29OwnerCurrentVertexShaderIdentity() != 0")
                < shader_gate < shader_live < fvf_gate):
            return False
        live_fallback = xyz[shader_gate:fvf_gate]
        if not all(term in live_fallback for term in (
            "IDirect3DVertexShader9* shader = nullptr;",
            "if (FAILED(device->GetVertexShader(&shader)))",
            "if (shader)",
            "shader->Release();",
            "return false;")):
            return False
        if live_fallback.count("GetVertexShader(") != 1:
            return False
        # A disabled Release in a comment still contains the bare token.
        # Require the COM reference to be released by an executable line.
        if "shader->Release();" not in [
                line.strip() for line in live_fallback.splitlines()
                if not line.lstrip().startswith("//")]:
            return False
        start = xyz.index("R29OwnerEnsureStereoResources(device)")
        fallback_vp = xyz.index("FAILED(device->GetViewport(&state.viewport))")
        if not start < xyz.index("!R29OwnerTryGetTrackedViewport(state.viewport)") < fallback_vp:
            return False
        if "(!R29OwnerTryGetTrackedViewport(state.viewport) &&" not in xyz:
            return False
        # The XYZRHW world-vs-HUD depth discriminator must reuse the
        # coherent R29 effect state, but never trust an invalidated snapshot.
        depthUse = xyz.index("R29OwnerTryGetEffectTelemetrySnapshot(depthEffect)")
        depthFallback = xyz.index("if (!haveCachedDepth &&")
        if not depthUse < depthFallback < xyz.index(
                "state.depthTestEnabled = zEnable != D3DZB_FALSE"):
            return False
        if not all(term in xyz for term in (
            "haveCachedDepth",
            "? depthEffect.zEnable : D3DZB_FALSE",
            "FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable))")):
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
        (r29, api, r30.replace(
            "R29OwnerTryGetEffectTelemetrySnapshot(depthEffect)",
            "false", 1)),
        (r29, api, r30.replace(
            "? depthEffect.zEnable : D3DZB_FALSE",
            "? D3DZB_FALSE : D3DZB_FALSE", 1)),
        (r29, api, r30.replace(
            "if (!haveCachedDepth &&",
            "if (false &&", 1)),
        (r29, api, r30.replace(
            "FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable)))",
            "false)", 1)),
        (r29, api, r30.replace(
            "if (!OutRunVR::State::StateBlockTracker::Reliable())",
            "if (false)", 1)),
        (r29, api, r30.replace(
            "if (!OutRunVR::State::StateBlockTracker::Reliable())",
            "if (true)", 1)),
        (r29, api, r30.replace(
            "if (FAILED(device->GetVertexShader(&shader)))",
            "if (false)", 1)),
        (r29, api, r30.replace(
            "shader->Release();", "// shader->Release();", 1)),
        (r29, api, r30.replace(
            "R29OwnerCurrentVertexShaderIdentity() != 0",
            "false", 1)),
        (r29, api, r30.replace(
            "if (!R30HasXyzrhwInputLayout(device))",
            "if (false)", 1)),
        (r29, api, r30.replace(
            "declaration->GetDeclaration(elements, &count)",
            "D3D_OK", 1)),
        (r29, api, r30.replace(
            '#include "../state/state_block_tracker.hpp"',
            '// removed explicit StateBlockTracker include', 1)),
    )
    for i, candidate in enumerate(changes, 1):
        assert candidate != (r29, api, r30), f"mutation {i} not applied"
        assert not check(*candidate), f"mutation {i} escaped"
    print("PASS DX9Ex R30 cached raster hotpath + 19 destructive regressions")


if __name__ == "__main__":
    main()
