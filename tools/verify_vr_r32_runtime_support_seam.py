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
    "R30SupportStereoBaselineSeeded",
    "R30SupportTargetIsBackBuffer",
    "R30SupportEffectTelemetrySnapshot",
    "R30SupportTryGetEffectTelemetrySnapshot",
    "R30SupportDirectTransportIdentity",
    "R30SupportOverlayReadyForTransport",
    "R30SupportNoteSafeAckBackpressure",
    "R30SupportNoteDirectTransportRingBackpressure",
    "R30SupportDirectTransportRingBackpressureCount",
    "R30SupportGpuCompletionSnapshot",
    "R30SupportTryGetGpuCompletionSnapshot",
    "R30SupportDirectTransportResourcesReady",
    "R30SupportEnsureDirectTransportResources",
    "R30SupportDirectTransportSourceSurfaces",
    "R30SupportTryGetDirectTransportSourceSurfaces",
    "R30SupportReleaseDirectAckState",
    "R30SupportReleaseDirectTransportInterop",
    "R30SupportTryGetDirectTransportIdentity",
    "R30SupportInvalidateEffectStateCache",
    "R30SupportInvalidateLiveStateSample",
    "R30SupportCurrentVertexShaderIdentity",
    "R30SupportExchangeVertexShaderIdentity",
    "R30SupportRestoreVertexShaderIdentityIfEmpty",
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
    (r"\bR9StereoBaselineSeeded\(\)", "R9StereoBaselineSeeded"),
    (r"(?<!R30Support)\bTargetIsBackBuffer\(\)", "TargetIsBackBuffer"),
    (r"\bR29EffectTelemetrySnapshot\b", "R29EffectTelemetrySnapshot"),
    (r"(?<!R30Support)\bTryGetEffectTelemetrySnapshot\(", "TryGetEffectTelemetrySnapshot"),
    (r"\bSharedState\b", "SharedState"),
    (r"\bDirectInteropVerified\b", "DirectInteropVerified"),
    (r"\bDirectTransportResourcesReady\b", "DirectTransportResourcesReady"),
    (r"(?<!R30Support)\bEnsureDirectTransportResources\(", "EnsureDirectTransportResources"),
    (r"\bR13OverlayReadyForTransport\(", "R13OverlayReadyForTransport"),
    (r"\bR13NoteSafeAckBackpressure\(", "R13NoteSafeAckBackpressure"),
    (r"(?<!R30Support)\bDirectTransportRingBackpressure\b", "DirectTransportRingBackpressure"),
    (r"\bR13GpuCompletionSnapshot\b", "R13GpuCompletionSnapshot"),
    (r"\bR13TryGetGpuCompletionSnapshot\(", "R13TryGetGpuCompletionSnapshot"),
    (r"\bR13ReleaseAckState\(", "R13ReleaseAckState"),
    (r"\bReleaseDirectTransportSlots\(", "ReleaseDirectTransportSlots"),
    (r"\bReleaseDirectInteropProbe\(", "ReleaseDirectInteropProbe"),
    (r"(?<!R30Support)\bInvalidateEffectStateCache\(\)", "InvalidateEffectStateCache"),
    (r"(?<!R30Support)\bInvalidateLiveStateSample\(\)", "InvalidateLiveStateSample"),
    (r"\bCurrentVertexShaderIdentity\b", "CurrentVertexShaderIdentity"),
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
    "R30SupportStereoBaselineSeeded()": ("return R9StereoBaselineSeeded();",),
    "R30SupportTargetIsBackBuffer()": ("return TargetIsBackBuffer();",),
    "R30SupportTryGetEffectTelemetrySnapshot(": (
        "R29EffectTelemetrySnapshot lower{};",
        "TryGetEffectTelemetrySnapshot(lower)",
        "out.alphaBlend = lower.alphaBlend;",
        "out.alphaTest = lower.alphaTest;",
        "out.zWrite = lower.zWrite;",
    ),
    "R30SupportOverlayReadyForTransport()": (
        "return R13OverlayReadyForTransport();",
    ),
    "R30SupportNoteSafeAckBackpressure()": (
        "R13NoteSafeAckBackpressure();",
    ),
    "R30SupportNoteDirectTransportRingBackpressure()": (
        "++DirectTransportRingBackpressure;",
    ),
    "R30SupportDirectTransportRingBackpressureCount()": (
        "return static_cast<std::uint64_t>(DirectTransportRingBackpressure);",
    ),
    "R30SupportTryGetGpuCompletionSnapshot(": (
        "R13GpuCompletionSnapshot lower{};",
        "R13TryGetGpuCompletionSnapshot(lower)",
        "out = {};",
        "out.completedFrameId[i] = lower.completedFrameId[i];",
        "return true;",
    ),
    "R30SupportDirectTransportResourcesReady()": (
        "return DirectTransportResourcesReady;",
    ),
    "R30SupportEnsureDirectTransportResources(": (
        "return EnsureDirectTransportResources(device);",
    ),
    "R30SupportTryGetDirectTransportSourceSurfaces(": (
        "out.left = BackBuffer;",
        "out.right = RightEyeSurface;",
        "return out.left != nullptr && out.right != nullptr;",
    ),
    "R30SupportReleaseDirectAckState()": (
        "R13ReleaseAckState();",
    ),
    "R30SupportReleaseDirectTransportInterop()": (
        "ReleaseDirectTransportSlots();",
        "ReleaseDirectInteropProbe();",
    ),
    "R30SupportTryGetDirectTransportIdentity(": (
        "if (!SharedState || !DirectInteropVerified)",
        "out.hostPid = SharedState->hostPid;",
        "out.hostAdapterLuidLow = SharedState->hostAdapterLuidLow;",
        "out.hostAdapterLuidHigh = SharedState->hostAdapterLuidHigh;",
    ),
    "R30SupportInvalidateEffectStateCache()": ("InvalidateEffectStateCache();",),
    "R30SupportInvalidateLiveStateSample()": ("InvalidateLiveStateSample();",),
    "R30SupportCurrentVertexShaderIdentity()": (
        "CurrentVertexShaderIdentity.load(std::memory_order_acquire)",
    ),
    "R30SupportExchangeVertexShaderIdentity(": (
        "CurrentVertexShaderIdentity.exchange(",
        "identity, std::memory_order_acq_rel",
    ),
    "R30SupportRestoreVertexShaderIdentityIfEmpty(": (
        "if (!identity)",
        "std::uintptr_t expected = 0;",
        "CurrentVertexShaderIdentity.compare_exchange_strong(",
        "std::memory_order_acq_rel, std::memory_order_acquire",
    ),
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

release_transport = body(r30, "R30SupportReleaseDirectTransportInterop()")
if release_transport.find("ReleaseDirectTransportSlots();") >= release_transport.find("ReleaseDirectInteropProbe();"):
    errors.append("R30 DirectGPU release facade changed slots -> probe ordering")

invalidate_direct = body(r32, "R32InvalidateDirectInteropOnly()")
ordered = (
    "R30SupportReleaseDirectAckState();",
    "R32DirectCopyPathRejected = false;",
    "R32DirectCopyRejectHr = D3D_OK;",
    "R30SupportReleaseDirectTransportInterop();",
    "R32ForgetDirectIdentity();",
)
positions = [invalidate_direct.find(token) for token in ordered]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    errors.append("R32 direct interop invalidation order changed")

source_surfaces = body(r30, "R30SupportTryGetDirectTransportSourceSurfaces(")
if "AddRef(" in source_surfaces:
    errors.append("R30 DirectGPU source-surface facade must preserve borrowed-pointer lifetime semantics")

resolve_direct = body(r32, "bool R32ResolveDirectTransport(")
if "R30SupportOverlayReadyForTransport()" not in resolve_direct:
    errors.append("R32 DirectGPU resolve bypasses R30 overlay-readiness facade")
if "R30SupportNoteSafeAckBackpressure()" not in resolve_direct:
    errors.append("R32 DirectGPU resolve bypasses R30 ACK-backpressure telemetry facade")
if "R30SupportNoteDirectTransportRingBackpressure()" not in resolve_direct:
    errors.append("R32 DirectGPU resolve bypasses R30 ring-backpressure owner facade")
if "DirectTransportRingBackpressure" in resolve_direct.replace(
        "R30SupportNoteDirectTransportRingBackpressure()", ""):
    errors.append("R32 DirectGPU resolve retained raw lower ring-backpressure state")
if "R30SupportGpuCompletionSnapshot ackSnapshot{};" not in resolve_direct:
    errors.append("R32 DirectGPU resolve missing R30 ACK snapshot value type")
if "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)" not in resolve_direct:
    errors.append("R32 DirectGPU resolve bypasses R30 ACK snapshot/rebind facade")
if "R13OverlayReadyForTransport()" in resolve_direct:
    errors.append("R32 DirectGPU resolve regained direct R13 overlay-readiness dependency")
if "R13NoteSafeAckBackpressure()" in resolve_direct:
    errors.append("R32 DirectGPU resolve regained direct R13 ACK-backpressure telemetry dependency")
if "R13TryGetGpuCompletionSnapshot(" in resolve_direct or "R13GpuCompletionSnapshot" in resolve_direct:
    errors.append("R32 DirectGPU resolve regained direct R13 ACK snapshot dependency")
for raw in ("BackBuffer", "RightEyeSurface"):
    if re.search(rf"\b{raw}\b", resolve_direct):
        errors.append(f"R32 DirectGPU resolve retained raw lower source surface: {raw}")
source_order = (
    "R30SupportDirectTransportSourceSurfaces sourceSurfaces{};",
    "R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces)",
    "const std::uint32_t preferred =",
    "device->StretchRect(\n                    sourceSurfaces.left",
    "device->StretchRect(sourceSurfaces.right",
)
ack_snapshot_order = (
    "R30SupportGpuCompletionSnapshot ackSnapshot{};",
    "if (!ackSnapshotRead)",
    "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)",
    "ackSnapshotRead = true;",
    "ackSnapshot.completedFrameId[index]",
)
ack_positions = [resolve_direct.find(token) for token in ack_snapshot_order]
if any(pos < 0 for pos in ack_positions) or ack_positions != sorted(ack_positions):
    errors.append("R32 ACK snapshot facade changed one-snapshot-per-resolve ordering")
source_positions = [resolve_direct.find(token) for token in source_order]
if any(pos < 0 for pos in source_positions) or source_positions != sorted(source_positions):
    errors.append("R32 DirectGPU source-surface facade/check/copy ordering changed")

fail_closed = body(r32, "HRESULT R32LowerFailClosed(")
if "!R30SupportStereoBaselineSeeded()" not in fail_closed:
    errors.append("R32 fail-closed baseline gate bypasses R30 owner facade")
shader_order = (
    "R30SupportExchangeVertexShaderIdentity(0);",
    "const HRESULT hr = lowerDraw();",
    "R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity);",
)
shader_positions = [fail_closed.find(token) for token in shader_order]
if any(pos < 0 for pos in shader_positions) or shader_positions != sorted(shader_positions):
    errors.append("R32 fail-closed shader identity exchange/draw/restore order changed")
if "return R30SupportCurrentVertexShaderIdentity();" not in r32:
    errors.append("R32 review shader identity read bypasses R30 owner facade")

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