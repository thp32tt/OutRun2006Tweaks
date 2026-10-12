#!/usr/bin/env python3
"""DX9Ex R27 verified-world effect-state fastpath and destructive regressions."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8")


def verify(src: str) -> None:
    start = src.index("HRESULT R27GuardWorldEffect(")
    end = src.index("HRESULT __stdcall DrawPrimitiveDestR27Effect(", start)
    fn = src[start:end]
    guard = (
        "const bool traceShaderFingerprint =\\n"
        "                OutRunVR::GplShaderFingerprint::TraceEnabled();\\n"
        "            if (!traceShaderFingerprint &&\\n"
        "                (!IsGameDevice(device) || InternalStereoPass ||\\n"
        "                 !TargetIsBackBuffer() || !StereoWanted() || !R9StereoSeeded))\\n"
        "                return legacyR13Draw();"
    ).replace("\\n", "\n")
    capture = "const R13EffectSnapshot effect = R13CaptureDrawTimeEffect(device);"
    fast = "if (!traceShaderFingerprint)\\n            {".replace("\\n", "\n")
    traced = "if (traceShaderFingerprint)\\n            {".replace("\\n", "\n")
    assert guard in fn
    fast_idx = fn.index(fast)
    capture_idx = fn.index(capture)
    traced_idx = fn.index(traced)
    assert fn.index(guard) < fast_idx < capture_idx < traced_idx
    assert fn.count("R28RunWithVerifiedWorldEpoch(") == 2
    assert fn.count("if (rebound != E_NOTIMPL)") == 2
    assert "R28RunWithVerifiedWorldEpoch(" in fn[fast_idx:capture_idx]
    assert "if (rebound != E_NOTIMPL)" in fn[fast_idx:capture_idx]
    assert "R28RunWithVerifiedWorldEpoch(" in fn[traced_idx:]
    assert "if (rebound != E_NOTIMPL)" in fn[traced_idx:]
    assert fn.index("R46TraceShaderFingerprint(device, effect);") > capture_idx
    assert fn.index("R46TraceShaderFingerprint(device, effect);") < traced_idx
    assert "R13EffectOverrideScope reuse(effect);" in fn
    assert fn.index("R37DepthDisabledFragileOverlay(effect)") > traced_idx
    assert fn.index("R27ShouldBypassLegacyZeroDisparity(device, effect)") > traced_idx
    assert "return r9Draw();" in fn


verify(source)
assert workflow.count("tools/verify_vr_r27_effect_fastpath.py") >= 2
mutations = (
    ("if (!traceShaderFingerprint &&", "if (traceShaderFingerprint &&"),
    ("!IsGameDevice(device)", "IsGameDevice(device)"),
    ("InternalStereoPass ||", "false ||"),
    ("!TargetIsBackBuffer()", "TargetIsBackBuffer()"),
    ("!StereoWanted()", "StereoWanted()"),
    ("!R9StereoSeeded))", "R9StereoSeeded))"),
    ("if (!traceShaderFingerprint)\\n            {".replace("\\n", "\n"),
        "if (traceShaderFingerprint)\\n            {".replace("\\n", "\n")),
    ("if (traceShaderFingerprint)\\n            {".replace("\\n", "\n"),
        "if (!traceShaderFingerprint)\\n            {".replace("\\n", "\n")),
    ("if (rebound != E_NOTIMPL)", "if (rebound == E_NOTIMPL)"),
    ("const R13EffectSnapshot effect = R13CaptureDrawTimeEffect(device);",
        "const R13EffectSnapshot effect{};"),
    ("R46TraceShaderFingerprint(device, effect);", "(void)effect;"),
    ("R13EffectOverrideScope reuse(effect);", "(void)effect;"),
    ("R37DepthDisabledFragileOverlay(effect)", "false"),
    ("R27ShouldBypassLegacyZeroDisparity(device, effect)", "true"),
    ("return legacyR13Draw();", "return r9Draw();"),
)
for old, new in mutations:
    begin = source.index("HRESULT R27GuardWorldEffect(")
    assert old in source[begin:], old
    broken = source[:begin] + source[begin:].replace(old, new, 1)
    try:
        verify(broken)
    except (AssertionError, ValueError):
        continue
    raise AssertionError("negative mutation survived: " + old)
print("PASS R27 verified-world fastpath, trace/fallback order and 15 negative mutations")
