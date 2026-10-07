#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        raise ValueError(f"missing body: {marker}")
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:i + 1]
    raise ValueError(f"unterminated body: {marker}")

header = read("src/vr/core/r30_support_api.hpp")
r30 = read("src/vr/d3d9/stereo_renderer_r30.cpp")
r32 = read("src/vr/d3d9/stereo_renderer_r32.cpp")
workflow = read(".github/workflows/vr-dx9ex-active.yml")
errors = []

required = (
    "R30SupportTelemetryEnabled",
    "R30SupportIsGameDevice",
    "R30SupportInternalStereoPassActive",
    "R30SupportExchangeInternalStereoPass",
    "R30SupportPresentEpoch",
    "R30SupportStereoWanted",
    "R30SupportTargetIsBackBuffer",
    "R30SupportEffectTelemetrySnapshot",
    "R30SupportTryGetEffectTelemetrySnapshot",
    "R30SupportInvalidateEffectStateCache",
    "R30SupportInvalidateLiveStateSample",
    "R30SupportInvalidateRendererStateAfterExternalRestore",
)
for name in required:
    if name not in header:
        errors.append(f"support header missing {name}")
    if name not in r30:
        errors.append(f"R30 implementation missing {name}")
    if name not in r32:
        errors.append(f"R32 missing owner-facade use {name}")

if '#include "../core/r30_support_api.hpp"' not in r32:
    errors.append("R32 missing explicit R30 support API include")

# These exact lower private symbols must no longer be consumed by R32.
for regex, label in (
    (r"\bSettings::VRTelemetry\b", "Settings::VRTelemetry"),
    (r"(?<!R30Support)\bIsGameDevice\(", "IsGameDevice"),
    (r"\bInternalStereoPass\b", "InternalStereoPass"),
    (r"\bPresentEpoch\b", "PresentEpoch"),
    (r"(?<!R30Support)\bStereoWanted\(\)", "StereoWanted"),
    (r"(?<!R30Support)\bTargetIsBackBuffer\(\)", "TargetIsBackBuffer"),
    (r"\bR29EffectTelemetrySnapshot\b", "R29EffectTelemetrySnapshot"),
    (r"(?<!R30Support)\bTryGetEffectTelemetrySnapshot\(", "TryGetEffectTelemetrySnapshot"),
    (r"(?<!R30Support)\bInvalidateEffectStateCache\(\)", "InvalidateEffectStateCache"),
    (r"(?<!R30Support)\bInvalidateLiveStateSample\(\)", "InvalidateLiveStateSample"),
    (r"OutRunVRRenderer::R29InvalidateRendererStateAfterExternalRestore\(",
     "R29 renderer invalidation"),
):
    if re.search(regex, r32):
        errors.append(f"R32 retained lower private runtime dependency: {label}")

delegations = {
    "R30SupportTelemetryEnabled()": ("Settings::VRTelemetry",),
    "R30SupportIsGameDevice(": ("IsGameDevice(device)",),
    "R30SupportInternalStereoPassActive()": ("return InternalStereoPass;",),
    "R30SupportExchangeInternalStereoPass(": (
        "const bool previous = InternalStereoPass;",
        "InternalStereoPass = active;",
        "return previous;",
    ),
    "R30SupportPresentEpoch()": ("return PresentEpoch;",),
    "R30SupportStereoWanted()": ("return StereoWanted();",),
    "R30SupportTargetIsBackBuffer()": ("return TargetIsBackBuffer();",),
    "R30SupportTryGetEffectTelemetrySnapshot(": (
        "R29EffectTelemetrySnapshot lower{};",
        "TryGetEffectTelemetrySnapshot(lower)",
        "out.alphaBlend = lower.alphaBlend;",
        "out.alphaTest = lower.alphaTest;",
        "out.zWrite = lower.zWrite;",
    ),
    "R30SupportInvalidateEffectStateCache()": ("InvalidateEffectStateCache();",),
    "R30SupportInvalidateLiveStateSample()": ("InvalidateLiveStateSample();",),
    "R30SupportInvalidateRendererStateAfterExternalRestore()": (
        "OutRunVRRenderer::R29InvalidateRendererStateAfterExternalRestore();",
    ),
}
for marker, tokens in delegations.items():
    try:
        fn = body(r30, marker)
    except ValueError as exc:
        errors.append(str(exc))
        continue
    for token in tokens:
        if token not in fn:
            errors.append(f"{marker} lost lower delegation: {token}")

if ": previous_(R30SupportExchangeInternalStereoPass(true))" not in r32:
    errors.append("R32 internal-pass scope no longer acquires through owner exchange")
destructor = body(r32, "R32ReviewInternalStereoPassScope::~R32ReviewInternalStereoPassScope()")
if "R30SupportExchangeInternalStereoPass(previous_)" not in destructor:
    errors.append("R32 internal-pass scope no longer restores through owner exchange")

if "'tools/verify_vr_r32_runtime_support_seam.py'" not in workflow:
    errors.append("DX9Ex workflow does not run R32 runtime support verifier")

if errors:
    for error in errors:
        print(f"R32 runtime support seam FAIL: {error}")
    sys.exit(1)

print("R32 runtime support seam PASS")
