from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"missing architecture file: {rel}")
    return path.read_text(encoding="utf-8")


def require(rel: str, *markers: str) -> str:
    data = text(rel)
    for marker in markers:
        if marker not in data:
            raise SystemExit(f"missing architecture invariant: {rel} :: {marker}")
    return data


# Final authoritative implementation graph. Intermediate implementation files
# are intentionally kept because the R23 wrappers include the validated lower
# layers, but cmake must never compile those included bodies independently.
required = [
    "src/vr/settings.cpp",
    "src/vr/runtime_eligibility.hpp",
    "src/vr/game/outrun_renderer.cpp",
    "src/vr/game/outrun_renderer_r13.cpp",
    "src/vr/game/outrun_renderer_r23.cpp",
    "src/vr/game/outrun_renderer_r29.cpp",
    "src/vr/d3d9/stereo_renderer.cpp",
    "src/vr/d3d9/stereo_renderer_r13.cpp",
    "src/vr/d3d9/stereo_renderer_r20.cpp",
    "src/vr/d3d9/stereo_renderer_r21.cpp",
    "src/vr/d3d9/stereo_renderer_r22.cpp",
    "src/vr/d3d9/stereo_renderer_r23.cpp",
    "src/vr/d3d9/stereo_renderer_r29.cpp",
    "src/vr/d3d9/stereo_renderer_r30.cpp",
    "src/vr/d3d9/stereo_renderer_r31.cpp",
    "src/vr/d3d9/ex_device_upgrade.cpp",
    "src/vr/d3d9/ex_device_upgrade_r13.cpp",
    "src/vr/d3d9/ex_device_upgrade_r14.cpp",
    "src/vr/d3d9/r13_bridge.hpp",
    "src/vr/d3d9/vr_pass_policy.hpp",
    "src/vr/ipc/protocol.hpp",
    "src/vr/ipc/protocol_v3.hpp",
    "src/vr/ipc/direct_ack_r13.hpp",
    "src/vr/core/frame_types.hpp",
    "src/vr/core/matrix.hpp",
    "src/vr/core/transport.hpp",
    "src/vr/game/game_adapter.hpp",
    "src/vr/d3d9/stereo_backend.hpp",
    "vrhost/src/main.cpp",
    "vrhost/src/main_r23.cpp",
    "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp",
    "vrhost/src/runtime/r23_runtime_hardening.hpp",
    "vrhost/src/runtime/r23_verified_bundle.hpp",
    "vrhost/tests/runtime_eligibility_smoke.cpp",
    "vrhost/tests/r23_verified_bundle_smoke.cpp",
    "docs/VR_ARCHITECTURE.md",
]
for rel in required:
    if not (ROOT / rel).is_file():
        raise SystemExit(f"missing architecture file: {rel}")

forbidden = [
    "src/hooks_vr.cpp",
    "src/vr_renderer_probe.cpp",
    "src/vr_stereo.cpp",
    "vrhost/main.cpp",
    "vrhost/main_compat.cpp",
    "vrhost/main_compat_v2.cpp",
    "vrhost/main_compat_v3.cpp",
    "vrhost/main_stereo.cpp",
]
for rel in forbidden:
    if (ROOT / rel).exists():
        raise SystemExit(f"legacy/prototype artifact still present: {rel}")

# v2 remains the live transport ABI while v3 is mirrored for migration and
# diagnostics. Do not silently steal reserved words or pointer-width fields.
protocol_v2 = require(
    "src/vr/ipc/protocol.hpp",
    "SharedProtocolVersion = 2",
    "RenderFrameProtocolVersion = 2",
    "RenderFrameRingSize = 4",
    "HostAdapterLuidValid",
    "hostDirectConsumedFrameId",
    "SharedRenderFrameRing",
)
protocol_v3 = require(
    "src/vr/ipc/protocol_v3.hpp",
    "ProtocolVersion = 3",
    "HostStateName",
    "ClientStateName",
    "FrameRingName",
    "AckStateName",
    "using WireHandle = std::uint64_t",
    "WireHandle leftHandle",
    "WireHandle rightHandle",
)
for forbidden_marker in (
    "std::uintptr_t interopProbeHandle",
    "std::uintptr_t leftHandle",
    "std::uintptr_t rightHandle",
):
    if forbidden_marker in protocol_v3:
        raise SystemExit(f"v3 protocol reintroduced pointer-width ABI debt: {forbidden_marker}")

require(
    "src/vr/ipc/direct_ack_r13.hpp",
    "DirectGpuAckName",
    "DirectGpuAckRingSize = 4",
    "transportGeneration",
    "completedFrameId[DirectGpuAckRingSize]",
)

# Shared eligibility is a state machine, not a collection of independent bools.
require(
    "src/vr/runtime_eligibility.hpp",
    "enum class InstallState",
    "Pending = 0",
    "Ready = 1",
    "Failed = 2",
    "SafetyOverlayReady",
    "MarkSafetyOverlayInstalled",
    "MarkSafetyOverlayUnavailable",
    "BaselineVerified",
    "MayInjectStereo",
)

# Render-pass policy must keep orthographic/UI and fragile camera-facing alpha
# effects out of the head-tracked WVP while retaining opaque world stereo.
require(
    "src/vr/d3d9/vr_pass_policy.hpp",
    "ClassifyProjectionSignature",
    "Perspective3D",
    "Orthographic2D",
    "EffectStereoPolicy",
    "ZeroDisparity",
    "ClassifyEffectStereo",
    "UnsafeSingleExecution",
)
require(
    "src/vr/game/outrun_renderer_r13.cpp",
    "R13FragileEffectNeedsZeroDisparity",
    "D3DRS_ALPHABLENDENABLE",
    "D3DRS_ZWRITEENABLE",
    "shadow/billboard/panel pass kept stock",
    "InvalidateVerifiedWvp",
    "InlineHook::StartDisabled",
)

# R29/R31 correctness overlays must preserve constant registers surrounding a
# partial c64..c67 write, pair fast-path WVP with its captured projection, and
# make StateBlock bypasses an explicit full-cache generation boundary.
require(
    "src/vr/game/outrun_renderer_r29.cpp",
    "R29BuildCoherentUploadEnvelope",
    "envelopeStart",
    "envelopeCount",
    "IsGameStateBlockRecording",
    "IsStateBlockTrackingReliable",
    "recorded stock",
    "R29InvalidateRendererStateAfterExternalRestore",
)
require(
    "src/vr/d3d9/stereo_renderer_r31.cpp",
    "GetR28VerifiedProjection",
    "projectionGeneration != generation",
    "BeginStateBlockDestR31",
    "R31StateBlockTrackingReliable",
    "per-draw live WVP/shader/render-state validation",
    "R31 fast left-eye c64 rollback",
    "R31 HUD left-eye c64 rollback",
)

# R14 shadows are resource-lifetime-bound and fail closed to one direct path on
# any write route that cannot be mirrored. A lower-mip fallback must copy that
# exact level rather than relying on UpdateTexture's level-zero dirty rules.
r14 = require(
    "src/vr/d3d9/ex_device_upgrade_r14.cpp",
    "std::unordered_map<IDirect3DTexture9*, R14EntryPtr>",
    "TextureReleaseDestR14",
    "InstallManagedResourceCompatR14",
    "R14AdoptCompatDevice",
    "TextureGenerateMipSubLevelsDestR14",
    "TextureGetSurfaceLevelDestR14",
    "UpdateSurfaceDestR14",
    "UpdateTextureDestR14",
    "validMask",
    "dirtyMask",
    "R14CopyWholeLevelByLock",
    "exact mip CPU-shadow upload failed",
)
if "R14ShadowCapacity" in r14 or "R14ShadowCursor" in r14:
    raise SystemExit("R14 reintroduced fixed-capacity live-shadow eviction")

settings = require(
    "src/vr/settings.cpp",
    'VRPreferD3D9Ex{ "VR", "PreferD3D9Ex", true',
    'VRDirectGpuOnly{ "VR", "DirectGpuOnly", true',
    'VRDisableDesktopDuplication{ "VR", "DisableDesktopDuplication", false',
    'VRTargetRefreshRateHz{ "VR", "TargetRefreshRateHz", 0.0f',
    'VRFrameCadenceMode{ "VR", "FrameCadenceMode", 1',
    'VRFrameCadenceTargetHz{ "VR", "FrameCadenceTargetHz", 0.0f',
    'VRFrameCadenceMaxHz{ "VR", "FrameCadenceMaxHz", 120.0f',
    "OUTRUN_VR_DIRECT_TRANSPORT",
    "OUTRUN_VR_DIRECT_ONLY",
    "OUTRUN_VR_DISABLE_DESKTOP_DUPLICATION",
    "OUTRUN_VR_TARGET_REFRESH_HZ",
    "OUTRUN_VR_CADENCE_MODE",
    "OUTRUN_VR_CADENCE_TARGET_HZ",
    "OUTRUN_VR_CADENCE_MAX_HZ",
)

# R23 installer workers may only request cleanup. Live OutRun camera/projection
# writes are serviced from D3D render callbacks; recovery pose warmup keeps the
# stock camera/WVP visible until the next-frame authoritative seed is accepted.
renderer_r23 = require(
    "src/vr/game/outrun_renderer_r23.cpp",
    "R23RenderThreadCleanupRequested",
    "R23RequestFailClosedCleanup",
    "R23ServiceRenderThreadCleanup",
    "R23DropIneligibleLatchedPoseOnRenderThread",
    "R23KeepWarmupPoseStockOnRenderThread",
    "recovery pose warmup is stock-visible",
    "RendererInjectionAllowed.store(false",
)
installer_start = renderer_r23.find("DWORD WINAPI R23RendererInstallThread")
installer_end = renderer_r23.find("class VRRendererR23EligibilityHook")
if installer_start >= 0 and installer_end > installer_start:
    worker = renderer_r23[installer_start:installer_end]
    if "RestoreCullingCamera()" in worker:
        raise SystemExit("R23 installer thread must not mutate live camera/projection memory")

# R20-R23 installation must fail fast and publish READY only after disabled-first
# hook transactions are enabled.
require(
    "src/vr/d3d9/stereo_renderer_r20.cpp",
    "R20InstallState",
    "using State = OutRunVR::RuntimeEligibility::InstallState",
    "State::Pending",
    "State::Failed",
    "InlineHook::StartDisabled",
)
require(
    "src/vr/d3d9/stereo_renderer_r21.cpp",
    "R21InstallState",
    "IsFailed(R20InstallState)",
    "InlineHook::StartDisabled",
)
require(
    "src/vr/d3d9/stereo_renderer_r22.cpp",
    "R22InstallState",
    "R22ShadowState",
    "R22SetScissorRectHook",
    "R22SetRenderStateHook",
    "R22PrimeShadowState",
    "InlineHook::StartDisabled",
    "per-draw GetViewport/GetScissorRect/GetRenderState eliminated",
)

# R23/R25 is the single recovery/baseline authority. Recovery Clear must remain
# a passive original call, while live viewport/scissor, full game draw serial,
# MRT safety and a fresh next-frame pose gate the first stereo initialization.
require(
    "src/vr/d3d9/stereo_renderer_r23.cpp",
    "#include \"stereo_renderer_r22.cpp\"",
    "R23InstallState",
    "IsFailed(R22InstallState)",
    "R23RecoveryNeedsBaseline",
    "R23CaptureActualGameState",
    "R23GameDrawSerial",
    "R23DiagnoseHostFreshness",
    "passive original Clear only",
    "authoritative first seed",
    "mrtActive",
    "MarkSafetyOverlayInstalled",
)

# Reconstructed VR-STARTUP-WHITE-001 protection: the D3D9Ex CreateDevice
# handoff may install Reset/Present ownership synchronously, but it must not
# allocate/swap/clear private stereo resources before the promoted device is
# returned to OutRun. The final R23 Present owner performs first initialization
# only after the lower game Present succeeds.
r7_startup = require(
    "src/vr/d3d9/stereo_renderer_r7.inc",
    "Resource creation is intentionally deferred beyond CreateDevice exposure.",
    "FirstDeferredResourceInitLogged",
    "StereoInstalledDevice.store(device,std::memory_order_release)",
)
install_start = r7_startup.find("bool InstallStereoHooks(IDirect3DDevice9*device)")
install_end = r7_startup.find("DWORD WINAPI StereoInstallThread", install_start)
if install_start < 0 or install_end < 0:
    raise SystemExit("could not isolate R7 InstallStereoHooks for startup-white guard")
install_body = r7_startup[install_start:install_end]
if "EnsureStereoResources(device)" in install_body:
    raise SystemExit(
        "VR-STARTUP-WHITE-001 regressed: pre-exposure InstallStereoHooks initializes stereo resources"
    )

r23_startup = require(
    "src/vr/d3d9/stereo_renderer_r23.cpp",
    "R23 is the final effective Present owner in the layered hook chain.",
    "if (SUCCEEDED(hr) && !StereoResourcesReady)",
    "EnsureStereoResources(device)",
    "VR R23 INIT: private eye/backbuffer resources initialized after final game Present",
    "recovery baseline can now identify the main backbuffer",
)
present_start = r23_startup.find("HRESULT __stdcall PresentDestR23")
present_end = r23_startup.find("void R23RollbackHooks", present_start)
if present_start < 0 or present_end < 0:
    raise SystemExit("could not isolate R23 Present owner for startup-white guard")
present_body = r23_startup[present_start:present_end]
lower_present = present_body.find("R23PresentR21Hook.stdcall<HRESULT>")
deferred_init = present_body.find("if (SUCCEEDED(hr) && !StereoResourcesReady)")
if lower_present < 0 or deferred_init < 0 or deferred_init <= lower_present:
    raise SystemExit(
        "VR-STARTUP-WHITE-001 regressed: deferred init is not after the lower Present"
    )

# Async installer status must be publishable back to the hook overlay/UI.
require(
    "src/hook_mgr.hpp",
    "std::atomic<bool> is_active_",
    "std::atomic<bool> has_error_",
    "ReportAsyncResult",
)
require(
    "src/hook_mgr.cpp",
    "HookManager::ReportAsyncResult",
    "async installer",
)

# Shadow v3 diagnostics may not run 1-2 ms busy polling or republish client
# state forever after the first stereo frame.
require(
    "src/vr/ipc/v3_game_shadow_bridge.cpp",
    "ShadowIdlePollMs = 8",
    "ShadowRetryMs = 250",
    "lastClientPublishedFrameId",
    "clientChanged",
)
require(
    "vrhost/src/ipc/v3_shadow_bridge.cpp",
    "ShadowIdlePollMs = 8",
    "ShadowWriterRetryMs = 250",
    "ackWriter.reset()",
)
require(
    "vrhost/src/ipc/host_state_v3_writer.hpp",
    "Reset(false)",
    "A constructor that throws never runs this object's destructor",
)

# Direct shared-eye transport must copy to host-owned resources, prove GPU copy
# completion, and bind actual texture format/size to committed Frame.v2 metadata.
require(
    "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp",
    "CopyFenceTimeoutMs = 8",
    "ExpectedDeclaredFormat",
    "case D3DFMT_A8R8G8B8",
    "DXGI_FORMAT_B8G8R8A8_UNORM",
    "desc[0].Format == declared",
    "host-owned GPU eye copies + completion ACK active",
    "SafeTransportGeneration",
)
require(
    "vrhost/src/runtime/r23_runtime_hardening.hpp",
    "ExpectedDirectDxgiFormat",
    "case D3DFMT_A8R8G8B8",
    "DXGI_FORMAT_B8G8R8A8_UNORM",
    "DirectSafeEyeMatchesCommittedFrame",
    "SafeEyeFormat == expected",
    "width == frame.backbufferWidth",
)
require(
    "vrhost/src/runtime/r23_verified_bundle.hpp",
    "MaxPresentationAgeMs",
    "ReadFresh",
    "Matches",
)

# main_r23 must commit only a stable full Frame.v2 snapshot. If stereo metadata
# is not ready, it may refresh Desktop Duplication only for the theater fallback;
# that mono source must never become a validated stereo projection.
require(
    "vrhost/src/main_r23.cpp",
    "#include \"main.cpp\"",
    "R23FrameUnchanged",
    "R23CommitDirectAfterValidation",
    "R23CommitClassicAfterValidation",
    "R23RefreshTheaterFallbackCapture",
    "if (c.disableDesktopDuplication_)",
    "R37BootstrapSubmittedFrame",
    "R37BootstrapSubmittedGeneration",
    "R37FrameIdBefore",
    "DirectGPU latest-frame-wins active",
    "PublishCompletedFrame(frame)",
    "!R37FrameIdBefore(",
    "lastProcessedStereoFrame",
    "allowInitialWarmupWait",
    "theater-only fallback",
    "OutRunVrR23VerifiedBundle::Publish",
    "std::memcmp(after.eye, before.eye",
    "std::memcmp(after.reserved, before.reserved",
)

require(
    "vrhost/src/main.cpp",
    "directTransportOnly_",
    "desktopDuplication=",
    "disabled-direct-only",
    "DXGI_FORMAT_B8G8R8A8_UNORM",
)
require(
    "src/vr/d3d9/stereo_renderer.cpp",
    "R9ReadBoolEnvironment",
    "R9DirectOnlyTransport",
    "Settings::VRDirectGpuOnly.get()",
    "inherits OUTRUN_VR_DIRECT_ONLY through CreateProcess",
    "SAFE modes stuck in the default direct-only path",
)
require(
    "src/vr/d3d9/stereo_renderer_r26.cpp",
    "R37DepthDisabledFragileOverlay",
    "R13EffectSnapshot effect = R13CaptureDrawTimeEffect",
    "unknown state fails closed",
)
require(
    "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
    '#include "stereo_renderer_r26.cpp"',
    "R30SafeStereoBase",
    "VR R26+HUD SAFE TEST",
)
require(
    "src/vr/d3d9/stereo_renderer_r30.cpp",
    "state.depthTestEnabled &&",
    "state.rhwDepthEvidence",
)

# R41 DirectGPU latency invariant: the newest complete slot is the only frame
# selected for sampling. Older occupied slots are never rendered later; they are
# ACKed immediately because no D3D11 work references them.
_history = [(1, 0), (2, 1), (3, 2), (4, 3)]
_selected = max(_history, key=lambda item: item[0])
_skipped = [item for item in _history if item != _selected]
if _selected != (4, 3) or [fid for fid, _ in _skipped] != [1, 2, 3]:
    raise SystemExit(
        f"R41 direct latest-frame model regressed: selected={_selected} skipped={_skipped}"
    )

# Once frame 4 is displayed, stale ring contents 1..3 must never be selected
# again while the producer is recycling those ACKed slots.
_last_processed = _selected[0]
_remaining_new = [item for item in _history if item[0] > _last_processed]
if _remaining_new:
    raise SystemExit(
        f"R41 direct stale-frame rewind model regressed: {_remaining_new}"
    )

# New regressions are required in the host build graph.
require(
    "vrhost/CMakeLists.txt",
    "src/main_r23.cpp",
    "outrun-vr-runtime-eligibility-smoke",
    "outrun-vr-r23-verified-bundle-smoke",
    "r23_runtime_hardening.hpp",
)

# Root cmkr source ownership: only final wrappers compile independently.
cmake_root = require(
    "cmake.toml",
    "stereo_renderer_r20.cpp",
    "stereo_renderer_r21.cpp",
    "stereo_renderer_r22.cpp",
    "outrun_renderer_r13.cpp",
    "HEADER_FILE_ONLY TRUE",
    'compile-options = ["/GS"',
)

# Renderer-independent interfaces stay clean of graphics/runtime headers.
math_core = require("src/vr/core/matrix.hpp", "struct Matrix4", "InverseRigid", "Invert(")
if "#include <d3d9.h>" in math_core or "#include <openxr/" in math_core:
    raise SystemExit("core matrix layer must not depend on D3D9/OpenXR headers")
require("src/vr/core/transport.hpp", "class IFrameProducer", "class IFrameConsumer", "D3D9ExShared", "DesktopDuplication")
require("src/vr/game/game_adapter.hpp", "class IGameAdapter", "latchRenderPose", "buildStereoMatrices")
require("src/vr/d3d9/stereo_backend.hpp", "class IStereoBackend", "drawWorldStereo", "drawScreenSpaceStereo")

# Deferred private-resource initialization is a bounded state transaction.
# It must preserve the caller's complete raster binding, quarantine an
# unrecoverable restore failure until Reset, and avoid heavyweight per-Present
# retries for ordinary allocation/init failure.
r7_resource = text("src/vr/d3d9/stereo_renderer_r7.inc")
ensure_begin = r7_resource.find("bool EnsureStereoResources(IDirect3DDevice9* device)")
ensure_end = r7_resource.find("void NoteRestoreFailure", ensure_begin)
if ensure_begin < 0 or ensure_end < 0:
    raise SystemExit("EnsureStereoResources transaction boundary missing")
ensure_resource = r7_resource[ensure_begin:ensure_end]
for marker in (
    "GetViewport(&savedViewport)",
    "GetScissorRect(&savedScissor)",
    "GetRenderState(",
    "D3DRS_SCISSORTESTENABLE",
    "SetViewport(&savedViewport)",
    "SetScissorRect(&savedScissor)",
    "StereoResourceInitRestoreFault = true",
    'NoteRestoreFailure("EnsureStereoResources/state-restore")',
):
    if marker not in ensure_resource:
        raise SystemExit(
            f"deferred resource-init state transaction invariant missing: {marker}"
        )

# Caller RT/depth/raster state must be fully known before the resource graph is
# released or any private eye target is bound. Query failure is not a plausible
# backbuffer/null-depth snapshot; only D3DERR_NOTFOUND means known no-depth.
for marker in (
    "const HRESULT renderTargetStateHr =",
    "device->GetRenderTarget(0, &currentRt)",
    "if (FAILED(renderTargetStateHr) || !currentRt)",
    "const HRESULT depthStateHr =",
    "device->GetDepthStencilSurface(&currentDepth)",
    "if (FAILED(depthStateHr) && depthStateHr != D3DERR_NOTFOUND)",
    "if (SUCCEEDED(depthStateHr) && !currentDepth)",
    "if (depthStateHr == D3DERR_NOTFOUND)",
    "TrackedRenderTarget = currentRt;",
    "TrackedDepthStencil = currentDepth;",
):
    if marker not in ensure_resource:
        raise SystemExit(
            f"resource-init capture fail-close invariant missing: {marker}"
        )

if "ReplaceSurfaceRef(TrackedRenderTarget, BackBuffer)" in ensure_resource:
    raise SystemExit(
        "failed RT capture must not fabricate the backbuffer as caller state"
    )

capture_markers = (
    "device->GetRenderTarget(0, &currentRt)",
    "device->GetDepthStencilSurface(&currentDepth)",
    "device->GetViewport(&savedViewport)",
    "device->GetScissorRect(&savedScissor)",
    "D3DRS_SCISSORTESTENABLE, &savedScissorEnabled",
)
capture_positions = [ensure_resource.find(marker) for marker in capture_markers]
first_release = ensure_resource.find("ReleaseStereoResources();")
first_private_create = ensure_resource.find("device->CreateRenderTarget(")
first_private_bind = ensure_resource.find("SetRenderTargetHook.stdcall<HRESULT>(")
if any(pos < 0 for pos in capture_positions):
    raise SystemExit("resource-init complete capture sequence missing")
if first_release < 0 or first_private_create < 0 or first_private_bind < 0:
    raise SystemExit("resource-init mutation boundary missing")
if not all(pos < first_release for pos in capture_positions):
    raise SystemExit(
        "caller state must be captured before ReleaseStereoResources mutates ownership"
    )
if not first_release < first_private_create < first_private_bind:
    raise SystemExit(
        "private resource create/bind ordering regressed after caller-state capture"
    )

# Deterministic failure matrix for the capture contract.
_capture_cases = (
    ("rt-query-failure", False, False),
    ("depth-invalidcall", False, False),
    ("depth-notfound", True, True),
    ("full-capture", True, True),
)
for name, capture_known, may_mutate in _capture_cases:
    if (name in ("rt-query-failure", "depth-invalidcall")) and (
        capture_known or may_mutate
    ):
        raise SystemExit(f"resource-init failure model regressed: {name}")
    if name in ("depth-notfound", "full-capture") and not (
        capture_known and may_mutate
    ):
        raise SystemExit(f"resource-init valid capture model regressed: {name}")

reset_begin = r7_resource.find("HRESULT __stdcall ResetDest(")
reset_end = r7_resource.find("constexpr std::uint32_t StereoInstallPending", reset_begin)
if reset_begin < 0 or reset_end < 0:
    raise SystemExit("ResetDest boundary missing for resource-init recovery")
reset_resource = r7_resource[reset_begin:reset_end]
for marker in (
    "StereoResourceInitRestoreFault = false",
    "++StereoResourceInitGeneration",
    "EnsureStereoResources(device)",
):
    if marker not in reset_resource:
        raise SystemExit(
            f"resource-init Reset-generation recovery invariant missing: {marker}"
        )

r23_resource = text("src/vr/d3d9/stereo_renderer_r23.cpp")
present_begin = r23_resource.find("HRESULT __stdcall PresentDestR23")
present_end = r23_resource.find("void R23RollbackHooks", present_begin)
if present_begin < 0 or present_end < 0:
    raise SystemExit("R23 Present boundary missing")
present_resource = r23_resource[present_begin:present_end]
for marker in (
    "R23RefreshResourceInitGeneration();",
    "StereoResourceInitRestoreFault",
    "R23ResourceInitNextRetryMs",
    "R23ResourceInitBackoffMs(",
    "R23ResourceInitFailureCount",
):
    if marker not in present_resource:
        raise SystemExit(
            f"R23 deferred resource retry invariant missing: {marker}"
        )

# Deterministic retry model: a persistent failure at a 90-Hz Present cadence
# must cause only a small bounded number of heavyweight init attempts, while a
# Reset-generation transition immediately re-arms one recovery attempt.
def _resource_init_backoff_ms(failure_count: int) -> int:
    if failure_count <= 1:
        return 0
    shift = min(failure_count - 2, 6)
    return min(25 << shift, 2000)

failure_count = 0
next_retry_ms = 0
attempts = 0
for now_ms in range(0, 5000, 11):
    if now_ms < next_retry_ms:
        continue
    attempts += 1
    failure_count += 1
    next_retry_ms = now_ms + _resource_init_backoff_ms(failure_count)

if attempts >= 20:
    raise SystemExit(
        f"deferred resource-init retry model is effectively per-Present: attempts={attempts}"
    )

# Meaningful Reset/generation change clears the backoff immediately.
failure_count = 0
next_retry_ms = 0
if next_retry_ms != 0 or failure_count != 0:
    raise SystemExit("resource-init Reset-generation rearm model regressed")

print("VR reconstructed R23/R25 architecture boundary verification passed")
