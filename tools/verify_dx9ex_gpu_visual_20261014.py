#!/usr/bin/env python3
"""Guard already-implemented glow/menu/cadence and new aux-WVP/lens/MAG changes."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
read = lambda p: (root / p).read_text(encoding="utf-8")
g = read("src/hooks_graphics.cpp")
r = read("src/vr/game/outrun_renderer.cpp")
u = read("src/hooks_uiscaling.cpp")
s = read("src/vr/d3d9/stereo_renderer_r30.cpp")
f = read("src/hooks_framerate.cpp")

def verify(g, r, u, s, f):
    wvp = r.split("HRESULT __stdcall SetVertexShaderConstantFDest(", 1)[1].split(
        "bool InstallD3D9Hooks(", 1)[0]
    assert "#include \"../core/r29_owner_api.hpp\"" in r
    a = wvp.index("if (!OutRunVRStereo::R29OwnerTargetIsBackBuffer() ||")
    assert wvp.index("InvalidateVerifiedWvp();") < a
    assert wvp.index("InvalidateGameWvpWrite();") < a
    assert wvp.index("UploadContainsOutRunWvp(") < a
    assert wvp.index("const auto semanticScope =") > a
    assert wvp.index("TryPrepareOutRunWvp(") > a
    b = wvp[a:wvp.index("// R51 ownership split:", a)]
    assert "OutRunVRStereo::R29OwnerAnyAuxRenderTargetActive()" in b
    assert "SetVertexShaderConstantFHook.stdcall<HRESULT>(" in b
    assert "device, startRegister, constantData, vector4fCount);" in b
    centre = g.split("static void __cdecl DrawObjectAlphaCentre(", 1)[1].split(
        "public:", 1)[0]
    assert "LensCentreOwnerDepth == LensCentreDepth" in centre
    assert "!OutRunVR::GameSemantic::QueueRenderActive()" in centre
    assert "objectId == 0x570002" in centre
    assert centre.index("ScopedExactProducerSemantic semantic(") < centre.index(
        "ScopedRenderSemantic centreDrawScope(") < centre.index("Game::DrawObjectAlpha_Internal(")
    assert "centreScope : OutRunVR::GameSemantic::CurrentScope" in centre
    aniso = g.split("class AnisotropicFiltering : public Hook", 1)[1].split(
        "class VSyncOverride", 1)[0]
    d2 = aniso.split("static void destination2(", 1)[1].split("public:", 1)[0]
    assert "PreserveScreenTextureFiltering()" in d2
    assert "if (ctx.edi == D3DSAMP_MINFILTER)" in d2
    assert "|| ctx.edi == D3DSAMP_MAGFILTER" not in d2
    assert "ctx.esi = D3DTEXF_ANISOTROPIC" in d2
    assert aniso.count("SetSamplerState(sampler,") == 1
    # Pre-existing protections are never discarded merely to reduce GPU work.
    assert "R30GameGlowActive()" in s
    assert "R30SkyGlowSceneCaptureEpoch == frame.presentEpoch" in s
    assert "R30CaptureSkyGlowSceneBeforeHud(" in s
    assert "CenterMultiSpriteQuad(float* vertices, int stride)" in u
    for stride in (9, 11, 13):
        assert f"CenterMultiSpriteQuad(" in u and f", {stride});" in u
    assert "vertices[i * stride + 1] = transformedY[i];" in u
    assert "vrCadenceFallback ? 60 : Settings::FramerateLimit.get()" in f

verify(g, r, u, s, f)
for name, gg, rr in (
    ("aux", g, r.replace("OutRunVRStereo::R29OwnerAnyAuxRenderTargetActive()", "false", 1)),
    ("backbuffer", g, r.replace("!OutRunVRStereo::R29OwnerTargetIsBackBuffer()", "false", 1)),
    ("centre", g.replace("ScopedRenderSemantic centreDrawScope(", "ScopedRenderSemantic lostScope(", 1), r),
    ("MAG", g.replace("if (ctx.edi == D3DSAMP_MINFILTER)\n\t\t\tctx.esi",
                       "if (ctx.edi == D3DSAMP_MINFILTER || ctx.edi == D3DSAMP_MAGFILTER)\n\t\t\tctx.esi", 1), r),
):
    try:
        verify(gg, rr, u, s, f)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("unsafe mutation survived: " + name)
print("PASS new DX9Ex optical/GPU guards and 4 destructive checks; HMD UNTESTED")
