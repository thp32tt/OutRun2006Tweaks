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
    assert "device->SetViewport(&viewport)" in pass_fn, "eye target's viewport must be set per pass"
    assert "R30SkyGlow.factor > 1" in apply, "do not change protected vertical blur policy"
    assert "compositeSource = R30SkyGlow.temp[eye];" in apply, "vertical blur source lost"

check(source)
mutations = (
    ("surfaces not released", "R30ReleaseCom(R30SkyGlow.tempSurface[eye]);"),
    ("missing reduced surface lifetime", "IDirect3DSurface9* reducedSurface[2]{};"),
    ("uncached every-frame setup", "if (!passState.fixedConfigured)"),
    ("missing blend transition", "if (!passState.blendConfigured || passState.additive != additive)"),
    ("missing post state restoration", "stateBlock->Apply()"),
    ("drop right-eye blur source", "compositeSource = R30SkyGlow.temp[eye];"),
    ("skip per-pass viewport", "device->SetViewport(&viewport)"),
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
    except (AssertionError, IndexError):
        continue
    raise AssertionError("mutation survived: " + label)
print("PASS R30 SkyGlow per-Present depth/shader coalescing and 13 destructive regressions")
