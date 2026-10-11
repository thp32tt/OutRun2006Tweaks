#!/usr/bin/env python3
"""DX9Ex R27 mono/auxiliary effect-state fastpath and negative regressions."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8")


def verify(src: str) -> None:
    start = src.index("HRESULT R27GuardWorldEffect(")
    end = src.index("HRESULT __stdcall DrawPrimitiveDestR27Effect(", start)
    fn = src[start:end]
    guard = (
        "if (!OutRunVR::GplShaderFingerprint::TraceEnabled() &&\n"
        "                (!IsGameDevice(device) || InternalStereoPass ||\n"
        "                 !TargetIsBackBuffer() || !StereoWanted() || !R9StereoSeeded))\n"
        "                return legacyR13Draw();"
    )
    capture = "const R13EffectSnapshot effect = R13CaptureDrawTimeEffect(device);"
    assert guard in fn and fn.index(guard) < fn.index(capture)
    for token in (
        "R46TraceShaderFingerprint(device, effect);",
        "R13EffectOverrideScope reuse(effect);",
        "R28RunWithVerifiedWorldEpoch(",
        "R37DepthDisabledFragileOverlay(effect)",
        "R27ShouldBypassLegacyZeroDisparity(device, effect)",
        "return r9Draw();",
    ):
        assert token in fn, token


verify(source)
assert workflow.count("tools/verify_vr_r27_effect_fastpath.py") >= 2
mutations = (
    ("!OutRunVR::GplShaderFingerprint::TraceEnabled()", "true"),
    ("!IsGameDevice(device)", "IsGameDevice(device)"),
    ("InternalStereoPass ||", "false ||"),
    ("!TargetIsBackBuffer()", "TargetIsBackBuffer()"),
    ("!StereoWanted()", "StereoWanted()"),
    ("!R9StereoSeeded))", "R9StereoSeeded))"),
    ("return legacyR13Draw();", "return r9Draw();"),
)
for old, new in mutations:
    start = source.index("HRESULT R27GuardWorldEffect(")
    assert old in source[start:]
    broken = source[:start] + source[start:].replace(old, new, 1)
    try:
        verify(broken)
    except (AssertionError, ValueError):
        continue
    raise AssertionError("negative mutation survived: " + old)
print("PASS R27 mono/aux effect fastpath, trace path and 7 negative mutations")
