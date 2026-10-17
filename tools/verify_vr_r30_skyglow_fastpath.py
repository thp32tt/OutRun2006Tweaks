#!/usr/bin/env python3
"""Check SkyGlow single-Present hot path and destroy safety contracts."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r30.cpp"
source = SRC.read_text(encoding="utf-8")

def check(text):
    def need(fragment, context):
        if fragment not in text:
            raise AssertionError(context)
    for fragment in (
        "IDirect3DSurface9* reducedSurface[2]{};",
        "IDirect3DSurface9* tempSurface[2]{};",
        "R30ReleaseCom(R30SkyGlow.reducedSurface[eye]);",
        "R30ReleaseCom(R30SkyGlow.tempSurface[eye]);",
        "R30SkyGlow.reduced[eye]->GetSurfaceLevel(",
        "R30SkyGlow.temp[eye]->GetSurfaceLevel(",
        "R30SkyGlow.reducedSurface[0] && R30SkyGlow.reducedSurface[1]",
        "R30SkyGlow.tempSurface[0] && R30SkyGlow.tempSurface[1]",
        "R30SkyGlowPassState passState{};",
        "device, passState,",
        "if (!passState.fixedConfigured)",
        "bool depthDetached = false;",
        "IDirect3DPixelShader9* activePixelShader = nullptr;",
        "if (!passState.depthDetached)",
        "passState.depthDetached = true;",
        "if (passState.activePixelShader != shader)",
        "passState.activePixelShader = shader;",
        "if (!passState.blendConfigured || passState.additive != additive)",
        "passState.additive = additive;",
        "passState.blendConfigured = true;",
        "device->SetTexture(0, nullptr);",
        "stateBlock->Apply()",
        "R30ReleaseSkyGlowResources();",
    ):
        need(fragment, "SkyGlow cache required: " + fragment)
    allocation = text.split("bool R30EnsureSkyGlowResources(", 1)[1].split("struct R30GlowVertex", 1)[0]
    capture = text.split("bool R30CaptureSkyGlowSceneBeforeHud(", 1)[1].split("bool R30ApplyStereoSkyGlow(", 1)[0]
    apply = text.split("bool R30ApplyStereoSkyGlow(", 1)[1].split("ULONGLONG R30LastTelemetryMs", 1)[0]
    pass_fn = text.split("bool R30DrawSkyGlowPass(", 1)[1].split("bool R30CaptureSkyGlowSceneBeforeHud(", 1)[0]
    # A mid-frame OFF->ON setting transition MUST NOT allow a post-HUD
    # backbuffer copy. This screen-boundary stamp precedes BOTH live
    # enable checks, while the actual clean-eye capture remains conditional.
    boundary = "R30SkyGlowScreenDrawEpoch = frame.presentEpoch;"
    assert capture.count(boundary) == 1, "screen boundary not recorded exactly once"
    assert (capture.index("if (!device)") <
            capture.index("const auto frame = R29OwnerCaptureFrameSnapshot();") <
            capture.index(boundary) <
            capture.index("Settings::SkyGlowFactor <= 0") <
            capture.index("R30GameGlowActive()") <
            capture.index("R29OwnerSkyGlowCaptureStillValid(")), (
                "SkyGlow mid-frame enable could reuse post-HUD pixels")
    assert "R30SkyGlowSceneCaptureEpoch = frame.presentEpoch;" in capture
    assert "R30SkyGlowScreenDrawEpoch == frame.presentEpoch" in apply
    assert "R30SkyGlowSceneCaptureEpoch != frame.presentEpoch" in apply
    need("for (int eye = 0; eye < 2; ++eye)", allocation)
    assert "GetSurfaceLevel(" not in capture and "GetSurfaceLevel(" not in apply, "per-frame surface getters"
    assert apply.count("device, passState,") == 4, "all four eye/pass calls must share one Present cache"
    assert "R30SkyGlow.reducedSurface[eye]" in capture
    assert "R30SkyGlow.reducedSurface[eye]" in apply
    assert "R30SkyGlow.tempSurface[eye]" in apply
    assert "passState.fixedConfigured = true;" in pass_fn.split("if (passState.activePixelShader != shader)", 1)[0]
    assert pass_fn.index("device->SetRenderTarget(0, target)") < pass_fn.index("if (!passState.depthDetached)")
    assert "FAILED(device->SetDepthStencilSurface(nullptr))" in pass_fn
    assert "FAILED(device->SetPixelShader(shader))" in pass_fn
    assert "R30SkyGlowPassState passState{};" in apply
    assert "device->SetTexture(0, nullptr);" in pass_fn, "avoid RT/SRV feedback hazard"
    assert "D3DRS_SRCBLEND, D3DBLEND_ONE" in pass_fn
    assert "D3DCOLORWRITEENABLE_ALPHA" in pass_fn
    # D3D9 resets the viewport on RT0 change. Skip the redundant driver
    # setter only for allocated reduced/temp surfaces with matching extent.
    # Unknown/full-eye compositor surfaces retain their explicit viewport.
    for fragment in (
        "target == R30SkyGlow.reducedSurface[0]",
        "target == R30SkyGlow.reducedSurface[1]",
        "target == R30SkyGlow.tempSurface[0]",
        "target == R30SkyGlow.tempSurface[1]",
        "width == R30SkyGlow.glowWidth &&",
        "height == R30SkyGlow.glowHeight;",
        "if (!knownReducedTarget)",
    ):
        need(fragment, "SkyGlow viewport fastpath guard required: " + fragment)
    assert (pass_fn.index("const bool knownReducedTarget =") <
            pass_fn.index("if (!knownReducedTarget)") <
            pass_fn.index("D3DVIEWPORT9 viewport{};") <
            pass_fn.index("device->SetViewport(&viewport)")), "guard viewport fallback after RT bind"
    assert pass_fn.count("device->SetViewport(&viewport)") == 1, "unexpected duplicate viewport setters"
    # Reuse D3DSBT_ALL across Presents, but Capture the current game state
    # on EVERY later frame. Ensure device loss/resize releases the object and
    # a failed Capture or Apply cannot replay a stale preceding frame.
    assert "IDirect3DStateBlock9* savedGameState = nullptr;" in text
    present = text.split("HRESULT __stdcall PresentDestR30(", 1)[1].split("HRESULT __stdcall ResetDestR30(", 1)[0]
    assert "else\n            {\n                // If stereo eligibility or SkyGlow is switched off" in present
    assert "R30ReleaseCom(R30SkyGlow.savedGameState);" in present, "mono eligibility must shed captured refs"
    lifetime = text.split("void R30ReleaseSkyGlowResources()", 1)[1].split("bool R30CompilePixelShader", 1)[0]
    assert "R30ReleaseCom(R30SkyGlow.savedGameState);" in lifetime
    # Recreating reduced eye textures discards the pre-HUD GPU snapshot.
    # If this happens within the same Present, the post-HUD framebuffer is
    # contaminated: do not use it as an implicit SkyGlow fallback.
    assert "R30SkyGlowSceneCaptureEpoch = 0;" in lifetime, "resize retained stale pre-HUD capture"
    after_ensure = apply.split("if (!R30EnsureSkyGlowResources(device))", 1)[1].split(
        "// Create once per SkyGlow resource epoch", 1)[0]
    assert "R30SkyGlowScreenDrawEpoch == frame.presentEpoch &&" in after_ensure
    assert "R30SkyGlowSceneCaptureEpoch != frame.presentEpoch" in after_ensure
    assert "++R30SkyGlowUiCaptureSkips;" in after_ensure
    assert "return true;" in after_ensure, "SkyGlow must fail closed after lost pre-HUD source"
    for fragment in (
        "if (!R30SkyGlow.savedGameState)",
        "D3DSBT_ALL, &R30SkyGlow.savedGameState",
        "else if (FAILED(R30SkyGlow.savedGameState->Capture()))",
        "IDirect3DStateBlock9* const stateBlock = R30SkyGlow.savedGameState;",
        # A successful SkyGlow Apply resynchronizes the shader epoch.
        # On failure the else arm discards the cached StateBlock and
        # invalidates renderer ownership; an old '!restoreOk' token is
        # not required, but the negative failure path is.
        "if (restoreOk)",
        "R29OwnerResynchronizeShaderEpoch(device);",
        "else\n            {\n                R30ReleaseCom(R30SkyGlow.savedGameState);\n"
        "                R29OwnerInvalidateRendererStateAfterExternalRestore();\n            }",
        "R29OwnerInvalidateEffectStateCache();",
        "R30ReleaseCom(R30SkyGlow.savedGameState);",
    ):
        assert fragment in apply, "missing SkyGlow captured-state lifetime: " + fragment
    assert apply.count("device->CreateStateBlock(") == 1
    assert "stateBlock->Release();" not in apply, "cached state block released each Present"
    assert apply.index("savedGameState->Capture()") < apply.index("device->GetRenderTarget("), "game state captured after other work"
    assert apply.index("stateBlock->Apply()") < apply.index("if (restoreOk)") < apply.index(
        "R29OwnerInvalidateRendererStateAfterExternalRestore()"), "restoration failure did not invalidate block"
    assert apply.index("R29OwnerResynchronizeShaderEpoch(device);") < apply.index(
        "R29OwnerInvalidateEffectStateCache();"), "success shader epoch/caches not resynchronized"
    assert "R30SkyGlow.factor > 1" in apply, "do not change protected vertical blur policy"
    assert "compositeSource = R30SkyGlow.temp[eye];" in apply, "vertical blur source lost"

check(source)
mutations = (
    ("remove saved state allocation", "IDirect3DStateBlock9* savedGameState = nullptr;"),
    ("remove mono/stereo-off cleanup", "// If stereo eligibility or SkyGlow is switched off"),
    ("remove saved state release", "R30ReleaseCom(R30SkyGlow.savedGameState);"),
    ("retain lost pre-HUD resource epoch",
     "// that a capture from the discarded resource is still valid.\n            R30SkyGlowSceneCaptureEpoch = 0;"),
    ("drop screen boundary for off-to-on SkyGlow in one Present",
     "R30SkyGlowScreenDrawEpoch = frame.presentEpoch;"),
    ("ignore pre-HUD resource recreation", "R30SkyGlowScreenDrawEpoch == frame.presentEpoch &&\n                R30SkyGlowSceneCaptureEpoch != frame.presentEpoch"),
    ("remove once-per-resource creation gate", "if (!R30SkyGlow.savedGameState)"),
    ("disable per-frame Capture", "else if (FAILED(R30SkyGlow.savedGameState->Capture()))"),
    ("disable D3DSBT_ALL full-state snapshot", "D3DSBT_ALL, &R30SkyGlow.savedGameState"),
    ("remove Apply-failure invalidation",
     "else\n            {\n                R30ReleaseCom(R30SkyGlow.savedGameState);\n"
     "                R29OwnerInvalidateRendererStateAfterExternalRestore();\n            }"),
    ("surfaces not released", "R30ReleaseCom(R30SkyGlow.tempSurface[eye]);"),
    ("missing reduced surface lifetime", "IDirect3DSurface9* reducedSurface[2]{};"),
    ("uncached every-frame setup", "if (!passState.fixedConfigured)"),
    ("missing blend transition", "if (!passState.blendConfigured || passState.additive != additive)"),
    ("missing post state restoration", "stateBlock->Apply()"),
    ("drop right-eye blur source", "compositeSource = R30SkyGlow.temp[eye];"),
    ("remove compositor viewport fallback", "device->SetViewport(&viewport)"),
    ("unguard compositor viewport", "if (!knownReducedTarget)"),
    ("wrong reduced eye0 identity", "target == R30SkyGlow.reducedSurface[0]"),
    ("wrong reduced eye1 identity", "target == R30SkyGlow.reducedSurface[1]"),
    ("wrong temp eye0 identity", "target == R30SkyGlow.tempSurface[0]"),
    ("wrong temp eye1 identity", "target == R30SkyGlow.tempSurface[1]"),
    ("ignore reduced width mismatch", "width == R30SkyGlow.glowWidth &&"),
    ("ignore reduced height mismatch", "height == R30SkyGlow.glowHeight;"),
    ("depth state no longer cached", "if (!passState.depthDetached)"),
    ("depth detach never committed", "passState.depthDetached = true;"),
    ("shader cache bypass", "if (passState.activePixelShader != shader)"),
    ("shader cache never committed", "passState.activePixelShader = shader;"),
    ("depth HRESULT ignored", "FAILED(device->SetDepthStencilSurface(nullptr))"),
    ("shader HRESULT ignored", "FAILED(device->SetPixelShader(shader))"),
)
for label, token in mutations:
    if token not in source:
        raise AssertionError("missing mutation input: " + label)
    damaged = source.replace(token, "/*negative mutation*/", 1)
    try:
        check(damaged)
    except (AssertionError, IndexError, ValueError):
        continue
    raise AssertionError("mutation survived: " + label)
print("PASS R30 SkyGlow state/viewport and 29 mutations including pre-HUD resource-recreation guard; HMD UNTESTED")
