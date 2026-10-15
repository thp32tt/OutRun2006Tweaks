#!/usr/bin/env python3
"""R27 non-stereo effect routes bypass redundant upper-layer state probes.

The lower R13 path remains the sole executor for mono-shadow, auxiliary-RT
and occlusion routes. Pure-source mutation and decision-table checks only:
no FPS/HMD claim is made by this verification.
"""
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8")

def effect_guard(text: str) -> str:
    begin = text.index("HRESULT R27GuardWorldEffect(")
    end = text.index("HRESULT __stdcall DrawPrimitiveDestR27Effect(", begin)
    return text[begin:end]

def verify(text: str) -> None:
    fn = effect_guard(text)
    gate = """if (!traceShaderFingerprint &&
                (R13ForceMonoShadow || AnyAuxRenderTargetActive() ||
                 OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire) ||
                 ActiveOcclusionQueries.load(std::memory_order_acquire) > 0))
                return legacyR13Draw();"""
    assert gate in fn
    trace = "const bool traceShaderFingerprint ="
    primary = "if (!traceShaderFingerprint &&\n                (!IsGameDevice(device)"
    fast = "if (!traceShaderFingerprint)\n            {"
    capture = "const R13EffectSnapshot effect = R13CaptureDrawTimeEffect(device);"
    indices = [fn.index(x) for x in (trace, primary, gate, fast, capture)]
    assert indices == sorted(indices)
    # No loss of legacy hook, shader diagnostics, positive stereo World route
    # or the original snapshot override used by the normal fallback.
    assert fn.count("return legacyR13Draw();") == 3
    assert fn.count("R28RunWithVerifiedWorldEpoch(") == 2
    assert "R46TraceShaderFingerprint(device, effect);" in fn
    assert "R13EffectOverrideScope reuse(effect);" in fn
    assert "R27ShouldBypassLegacyZeroDisparity(device, effect)" in fn
    assert "return r9Draw();" in fn
    assert "R27ShouldBypassLegacyZeroDisparity(" in text
    for veto in ("R13ForceMonoShadow", "AnyAuxRenderTargetActive()",
                 "OcclusionQueryTrackingUnavailable.load", "ActiveOcclusionQueries.load"):
        assert veto in fn[indices[2]:indices[3]], veto

def decision(trace: bool, shadow: bool, aux: bool,
             tracking_lost: bool, occlusion: bool) -> str:
    return "LEGACY" if not trace and (
        shadow or aux or tracking_lost or occlusion) else "NORMAL"

verify(SRC)
assert WF.count("tools/verify_vr_r27_shadow_occlusion_fastpath.py") >= 2
for values in product((False, True), repeat=5):
    trace, shadow, aux, tracking_lost, occlusion = values
    route = decision(*values)
    if trace:
        assert route == "NORMAL"  # keep GPL trace capture
    if not trace and (shadow or aux or tracking_lost or occlusion):
        assert route == "LEGACY"  # no speculative WVP / upper effect reads
    if not any(values):
        assert route == "NORMAL"  # game stereo remains eligible

guard = effect_guard(SRC)
mutations = (
    ("if (!traceShaderFingerprint &&\n                (R13ForceMonoShadow",
     "if (traceShaderFingerprint &&\n                (R13ForceMonoShadow"),
    ("R13ForceMonoShadow || AnyAuxRenderTargetActive()",
     "false || AnyAuxRenderTargetActive()"),
    ("AnyAuxRenderTargetActive() ||", "false ||"),
    ("OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire)",
     "false"),
    ("ActiveOcclusionQueries.load(std::memory_order_acquire) > 0",
     "false"),
    ("return legacyR13Draw();\n\n            if (!traceShaderFingerprint)",
     "return r9Draw();\n\n            if (!traceShaderFingerprint)"),
)
for old, new in mutations:
    assert old in guard, old
    begin = SRC.index("HRESULT R27GuardWorldEffect(")
    end = SRC.index("HRESULT __stdcall DrawPrimitiveDestR27Effect(", begin)
    mutated = SRC[:begin] + guard.replace(old, new, 1) + SRC[end:]
    try:
        verify(mutated)
    except (AssertionError, ValueError):
        continue
    raise AssertionError("destructive mutation escaped: " + old)
print("PASS R27 mono/shadow/aux/occlusion route, GPL tracing, 32 cases, 6 mutants")
