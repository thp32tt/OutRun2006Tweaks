#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

R30_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
R29_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"
R29_API_PATH = ROOT / "src/vr/core/r29_owner_api.hpp"
R31_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp"
R32_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
R33_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"
DRAW_STATE_HELPERS_PATH = ROOT / "src/vr/d3d9/draw_state_helpers.hpp"
STATEBLOCK_PATH = ROOT / "src/vr/state/state_block_tracker.hpp"
WORKFLOW_PATH = ROOT / ".github/workflows/vr-dx9ex-active.yml"
RUN_RECORD_PATH = ROOT / "docs/automation/runs/CONVERSION-DX9EX-00409.json"


def fail(message: str) -> None:
    raise SystemExit(
        "VR R31/R32 draw-retirement guard FAILED\n"
        f" - {message}"
    )


def load(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(text: str, owner: str, *markers: str) -> None:
    for marker in markers:
        if marker not in text:
            fail(f"{owner} missing retirement invariant: {marker}")


def forbid(text: str, owner: str, *markers: str) -> None:
    for marker in markers:
        if marker in text:
            fail(f"{owner} retained retired draw-layer marker: {marker}")


def function_body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        fail(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing function body for: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    fail(f"unterminated function body for: {marker}")
    return ""


r30 = load(R30_PATH)
r31 = load(R31_PATH)
r32 = load(R32_PATH)
r33 = load(R33_PATH)
draw_state_helpers = load(DRAW_STATE_HELPERS_PATH)
stateblock = load(STATEBLOCK_PATH)
workflow = load(WORKFLOW_PATH)
run_record = json.loads(load(RUN_RECORD_PATH))

# -1) Controller result identity is part of the retirement completion contract.
# Bookkeeping commits may follow the material result, but they must never become
# the Gate-owning result merely because they carry the task marker.
if run_record.get("task_id") != "CONVERSION-DX9EX-00409":
    fail("00409 durable record task identity changed")
result_sha = run_record.get("result_sha")
validation_sha = run_record.get("validation_bearing_result_sha")
queue_sha = run_record.get("queue_commit_sha")
state_sha = run_record.get("state_commit_sha")
if not result_sha:
    fail("00409 durable record is missing contract-required result_sha")
if result_sha != validation_sha:
    fail("00409 result_sha must equal validation_bearing_result_sha")
if result_sha in {queue_sha, state_sha}:
    fail("00409 bookkeeping SHA was promoted to validation-bearing result")
identity = run_record.get("result_identity", {})
if identity.get("queue_commit_role") != "BOOKKEEPING_ONLY":
    fail("00409 queue commit role must remain BOOKKEEPING_ONLY")
if identity.get("state_commit_role") != "BOOKKEEPING_ONLY":
    fail("00409 state commit role must remain BOOKKEEPING_ONLY")

# 0) R31/R32 retirement must continue reducing cross-layer helper ownership.
# Live vertex-shader identity checking is stateless draw-state validation, so it
# belongs to the neutral D3D9 helper boundary rather than the retained R31 owner.
require(
    draw_state_helpers,
    "neutral draw-state helper",
    "namespace OutRunVR::D3D9",
    "inline bool LiveVertexShaderMatches(",
    "device->GetVertexShader(&shader)",
    "reinterpret_cast<std::uintptr_t>(shader)",
    "shader->Release();",
)
if draw_state_helpers.count("LiveVertexShaderMatches(") != 1:
    fail("neutral LiveVertexShaderMatches must have exactly one definition")
for owner, source in (("R31", r31), ("R33", r33)):
    forbid(source, owner, "R31LiveShaderMatches(")
require(
    r31,
    "R31 neutral shader dependency",
    "#include \"draw_state_helpers.hpp\"",
    "OutRunVR::D3D9::LiveVertexShaderMatches(device, verifiedShader)",
)
require(
    r33,
    "R33 split-facade shader dependency",
    "R32ReviewLiveVertexShaderMatches(device, cachedShader)",
)
require(
    r32,
    "R32 split facade neutral shader delegation",
    "R32ReviewLiveVertexShaderMatches",
    "OutRunVR::D3D9::LiveVertexShaderMatches(d,e)",
)

# The raw D3D9 c64..c67 batch upload is also a neutral draw-state primitive.
# R32 keeps telemetry/failure accounting, but must not own the device write.
require(
    draw_state_helpers,
    "neutral shader-constant batch primitive",
    "inline bool SetVertexShaderConstantBatch(",
    "device->SetVertexShaderConstantF(",
)
r32_wvp_batch = function_body(r32, "bool R32SetWvpBatch(")
require(
    r32_wvp_batch,
    "R32 WVP telemetry wrapper",
    "++R32BatchWvpUploads",
    "OutRunVR::D3D9::SetVertexShaderConstantBatch(",
    "++R32BatchWvpFailures",
    "R32FirstBatchWvpLogged",
)
forbid(
    r32_wvp_batch,
    "R32 WVP telemetry wrapper",
    "device->SetVertexShaderConstantF(",
)
if r33.count("R32ReviewSetWvpBatch(") < 4:
    fail("R33 WVP sites unexpectedly stopped using the telemetry-preserving wrapper")

# Raw live effect render-state reads are ownership-neutral D3D9 observations.
# R32 keeps fail-close telemetry/warnings and effect policy classification.
require(
    draw_state_helpers,
    "neutral live effect-state snapshot",
    "struct LiveEffectRenderStateSnapshot",
    "inline bool ReadLiveEffectRenderStateSnapshot(",
    "D3DRS_ALPHABLENDENABLE",
    "D3DRS_ALPHATESTENABLE",
    "D3DRS_ZWRITEENABLE",
    "D3DRS_ZENABLE",
    "D3DRS_CULLMODE",
)
r32_effect_snapshot = function_body(r32, "bool R32ReadEffectSnapshot(")
require(
    r32_effect_snapshot,
    "R32 effect snapshot telemetry wrapper",
    "OutRunVR::D3D9::ReadLiveEffectRenderStateSnapshot(device, out)",
    "++R32StateSnapshotFailures",
    "R32FirstStateSnapshotFailureLogged",
    "draw is forced to stock-WVP zero disparity instead of fail-open world stereo",
)
forbid(
    r32_effect_snapshot,
    "R32 effect snapshot telemetry wrapper",
    "device->GetRenderState(",
)
r32_effect_policy = function_body(r32, "bool R32EffectIsFragileLive(")
require(
    r32_effect_policy,
    "R32 live effect policy",
    "OutRunVR::D3D9::LiveEffectRenderStateSnapshot state{}",
    "R32ReadEffectSnapshot(device, state)",
    "OutRunVR::PassPolicy::ClassifyEffectStereo(",
    "OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy)",
)
lower_fail_closed = function_body(r32, "HRESULT R32LowerFailClosed(")
require(
    lower_fail_closed,
    "R32 lower fail-close live-state probe",
    "OutRunVR::D3D9::LiveEffectRenderStateSnapshot snapshot{}",
    "R32ReadEffectSnapshot(device, snapshot)",
)

# Raw viewport reads are neutral D3D9 observations. R31/R32 keep their tracked
# viewport and StateBlock reliability policies; only the final device read moves.
require(
    draw_state_helpers,
    "neutral viewport read primitive",
    "inline bool ReadViewport(",
    "device->GetViewport(&viewport)",
)
r31_viewport = function_body(r31, "bool R31GetSavedViewport(")
require(
    r31_viewport,
    "R31 saved viewport policy",
    "TryGetTrackedViewport(viewport)",
    "OutRunVR::D3D9::ReadViewport(device, viewport)",
)
forbid(
    r31_viewport,
    "R31 saved viewport policy",
    "device->GetViewport(&viewport)",
)
r32_viewport = function_body(r32, "bool R32GetSavedViewport(")
require(
    r32_viewport,
    "R32 saved viewport policy",
    "OutRunVR::State::StateBlockTracker::Reliable()",
    "R31SupportGetSavedViewport(device, viewport)",
    "OutRunVR::D3D9::ReadViewport(device, viewport)",
)
forbid(
    r32_viewport,
    "R32 saved viewport policy",
    "device->GetViewport(&viewport)",
)
if r33.count("R32ReviewGetSavedViewport(") < 2:
    fail("R33 viewport sites unexpectedly stopped using the R32 StateBlock-aware wrapper")

# Terminal post-1100 dependency census: every remaining R33 -> R31/R32 call is
# intentionally owner-specific. Any new cross-layer call must be reviewed rather
# than silently growing this dependency surface.
observed_owner_calls = set(re.findall(r"\b(R3[12]\w+)\s*\(", r33))
legacy_r31_calls = sorted(call for call in observed_owner_calls if call.startswith("R31"))
if legacy_r31_calls:
    fail(
        "R33 regained direct R31 implementation dependencies after the split: "
        f"{legacy_r31_calls}"
    )
non_facade_r32_calls = sorted(
    call for call in observed_owner_calls
    if call.startswith("R32") and not call.startswith("R32Review"))
if non_facade_r32_calls:
    fail(
        "R33 bypassed the R32 review split facade: "
        f"{non_facade_r32_calls}"
    )
required_split_facade_calls = {
    "R32ReviewBuildFastWorldConstants",
    "R32ReviewDiscardUnreliableDrawCaches",
    "R32ReviewObserveDispatchDraw",
    "R32ReviewPrerequisiteStatus",
    "R32ReviewRunRasterReplayGuard",
    "R32ReviewCallLowerDrawPrimitive",
    "R32ReviewCallRawPresent",
    "R32ReviewRunLowerFailClosed",
    "R32ReviewRunPresentTelemetry",
    "R32ReviewRunResetLifecycle",
    "R32ReviewResolveDirectTransport",
    "R32ReviewSetWvpBatch",
}
missing_split_facades = sorted(required_split_facade_calls - observed_owner_calls)
if missing_split_facades:
    fail(
        "R33 split-facade census lost required owner boundaries: "
        f"{missing_split_facades}"
    )

# Completion contract: every allow-listed cross-layer call must carry explicit
# owner evidence. This closes the neutral-helper extraction chain: future work
# cannot add a new R31/R32 dependency by editing only the allow-list, and an
# existing helper cannot silently lose the state/telemetry/lifecycle reason that
# keeps it in its current owner.
owner_evidence = {
    "R31BuildFastWorldConstants": (
        r31, "bool R31BuildFastWorldConstants(",
        ("GetLastVerifiedWvp(", "R31BlockedVerifiedGeneration",
         "StateBlockTracker::Reliable()", "R31PrepareEyeTailCache("),
    ),
    "R31DiscardUnreliableDrawCaches": (
        r31, "void R31DiscardUnreliableDrawCaches(",
        ("StateBlockTracker::Reliable()", "InvalidateEffectStateCache()",
         "InvalidateTrackedRasterShadow()", "InvalidateLiveStateSample()"),
    ),
    "R31InstallStatus": (
        r31, "R31InstallStatus() noexcept",
        ("R31InstallState.load(std::memory_order_acquire)",),
    ),
    "R31ObserveDraw": (
        r31, "void R31ObserveDraw(",
        ("R31Frame.epoch", "++R31Frame.draws", "TargetIsBackBuffer()"),
    ),
    "R31TelemetryNoteFallback": (
        r31, "inline void R31TelemetryNoteFallback(",
        ("++R31Frame.fallback",),
    ),
    "R31TelemetryNoteFastWorld": (
        r31, "inline void R31TelemetryNoteFastWorld(",
        ("++R31FastWorldDraws", "++R31Frame.fastWorld"),
    ),
    "R31TelemetryNoteFragile": (
        r31, "inline void R31TelemetryNoteFragile(",
        ("++R31Frame.fragile",),
    ),
    "R31TelemetryNoteHud": (
        r31, "inline void R31TelemetryNoteHud(",
        ("++R31HudDraws", "++R31Frame.hud"),
    ),
    "R31TelemetryNoteUnstable": (
        r31, "inline void R31TelemetryNoteUnstable(",
        ("++R31Frame.unstable",),
    ),
    "R32ReviewEffectIsFragileLive": (
        r32, "bool R32EffectIsFragileLive(",
        ("R32ReadEffectSnapshot(device, state)",
         "PassPolicy::ClassifyEffectStereo(",
         "PassPolicy::AllowsEffectWorldStereo(policy)"),
    ),
    "R32ReviewGetSavedViewport": (
        r32, "bool R32GetSavedViewport(",
        ("StateBlockTracker::Reliable()",
         "R31SupportGetSavedViewport(device, viewport)",
         "OutRunVR::D3D9::ReadViewport(device, viewport)"),
    ),
    "R32ReviewRunLowerFailClosed": (
        r32, "HRESULT R32LowerFailClosed(",
        ("R32ReadEffectSnapshot(device, snapshot)",
         "R30SupportExchangeVertexShaderIdentity(0)",
         "R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity)",
         "R32FailClosedZeroDisparityDraws"),
    ),
    "R32ReviewObserveFrameWorkload": (
        r32, "void R32ObserveFrameWorkload(",
        ("R30SupportTelemetryEnabled()", "R32FrameWorkloadCounters",
         "frame.primitives += primitiveCount",
         "TryGetEffectTelemetrySnapshot(effect)"),
    ),
    "R32ReviewRestoreRightPassState": (
        r32, "bool R32RestoreRightPassState(",
        ("R30SupportCallOriginalSetRenderTarget(",
         "R30SupportCallOriginalSetDepthStencilSurface(",
         "device->SetViewport(&savedViewport)",
         "R32SetWvpBatch(device, originalConstants)"),
    ),
    "R32ReviewRunPresentTelemetry": (
        r32, "HRESULT R32WithPresentTelemetry(",
        ("R32CaptureStereoWorkload()",
         "QueryPerformanceCounter(&presentStart)",
         "const HRESULT hr = lowerPresent();",
         "R32FinalizeFramePerf(",
         "R32LogPerfWindow()"),
    ),
    "R32ReviewRunResetLifecycle": (
        r32, "HRESULT R32WithResetLifecycle(",
        ("const HRESULT hr = lowerReset();",
         "R32ResetAfterGameReset();",
         "R32InvalidateResetCaches();",
         "++R32ResetFailures"),
    ),
    "R32ReviewResolveDirectTransport": (
        r32, "bool R32ResolveDirectTransport(",
        ("R30SupportOverlayReadyForTransport()",
         "return lowerResolve();",
         "R32EnsureDirectResources(device)",
         "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)",
         "DirectTransportFrameReadyAfterPresent() is",
         "R30SupportMarkDirectTransportSlotPending(selected, frameId);",
         "R30SupportSetActiveDirectTransportSlot(selected);"),
    ),
    "R32ReviewSetWvpBatch": (
        r32, "bool R32SetWvpBatch(",
        ("R32BatchWvpUploads",
         "OutRunVR::D3D9::SetVertexShaderConstantBatch(",
         "R32BatchWvpFailures"),
    ),
}
for call, (source, marker, evidence) in owner_evidence.items():
    require(
        function_body(source, marker),
        f"terminal owner evidence for {call}",
        *evidence,
    )

require(
    function_body(r31, "bool R31BuildFastWorldConstants("),
    "R31 fast-world cache/pose owner",
    "GetLastVerifiedWvp(",
    "R31BlockedVerifiedGeneration",
    "StateBlockTracker::Reliable()",
    "R31PrepareEyeTailCache(",
)
require(
    function_body(r31, "void R31DiscardUnreliableDrawCaches("),
    "R31 unreliable-cache owner",
    "StateBlockTracker::Reliable()",
    "InvalidateEffectStateCache()",
    "InvalidateTrackedRasterShadow()",
    "InvalidateLiveStateSample()",
)
require(
    function_body(r31, "void R31ObserveDraw("),
    "R31 draw-telemetry owner",
    "R31Frame.epoch",
    "++R31Frame.draws",
    "TargetIsBackBuffer()",
)
require(
    function_body(r32, "bool R32EffectIsFragileLive("),
    "R32 effect-policy owner",
    "R32ReadEffectSnapshot(device, state)",
    "PassPolicy::ClassifyEffectStereo(",
    "PassPolicy::AllowsEffectWorldStereo(policy)",
)
require(
    function_body(r32, "HRESULT R32LowerFailClosed("),
    "R32 fail-close owner",
    "R32ReadEffectSnapshot(device, snapshot)",
    "R30SupportExchangeVertexShaderIdentity(0)",
    "R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity)",
    "R32FailClosedZeroDisparityDraws",
)
require(
    function_body(r32, "void R32ObserveFrameWorkload("),
    "R32 workload-telemetry owner",
    "R32FrameWorkloadCounters",
    "frame.primitives += primitiveCount",
    "TryGetEffectTelemetrySnapshot(effect)",
)
require(
    function_body(r32, "bool R32RestoreRightPassState("),
    "R32 right-pass restore owner",
    "R30SupportCallOriginalSetRenderTarget(",
    "R30SupportCallOriginalSetDepthStencilSurface(",
    "device->SetViewport(&savedViewport)",
    "R32SetWvpBatch(device, originalConstants)",
)
# 1) R31 is retained only as the neutral StateBlock event-consumer/state-cache
# owner. R22 owns the physical StateBlock lifecycle hooks; when that optional
# coverage is unavailable, reliability stays fail-closed instead of installing
# a second physical fallback layer.
forbid(
    r31,
    "R31",
    "SafetyHookInline R31DrawPrimitiveR30Hook{};",
    "SafetyHookInline R31DrawIndexedPrimitiveR30Hook{};",
    "SafetyHookInline R31DrawPrimitiveUPR30Hook{};",
    "SafetyHookInline R31DrawIndexedPrimitiveUPR30Hook{};",
    "HRESULT R31Dispatch(",
    "HRESULT __stdcall DrawPrimitiveDestR31(",
    "HRESULT __stdcall DrawIndexedPrimitiveDestR31(",
    "HRESULT __stdcall DrawPrimitiveUPDestR31(",
    "HRESULT __stdcall DrawIndexedPrimitiveUPDestR31(",
    "R31RollbackDrawHooks()",
    "R31EnableDrawHooks()",
    "R31OwnedResult R31TryFastWorld(",
    "R31OwnedResult R31TryHud(",
    "SafetyHookInline R31CreateStateBlockHook{};",
    "SafetyHookInline R31BeginStateBlockHook{};",
    "SafetyHookInline R31EndStateBlockHook{};",
    "SafetyHookInline R31StateBlockApplyHook{};",
    "R31StateBlockApplyTarget",
    "StateBlockApplyDestR31(",
    "R31EnsureStateBlockApplyHook(",
    "CreateStateBlockDestR31(",
    "BeginStateBlockDestR31(",
    "EndStateBlockDestR31(",
    "safetyhook::create_inline(",
)
require(
    r31,
    "R31 StateBlock event consumer",
    "StateBlockRecovery::Configure(",
    "StateBlockEvents::Configure(",
    "StateBlockTracker::LifecycleHooksReady()",
    "StateBlockTracker::MarkCoverageLost()",
    "R31 physical StateBlock fallback retired; fast-path trust remains disabled",
    "StateBlockTracker::SetEventConsumerReady(true)",
    "R31InstallStatus() noexcept",
    "R31OwnedResult",
    "R31BuildFastWorldConstants(",
    "R31TelemetryNoteFastWorld()",
    "R31TelemetryNoteHud()",
)
r31_install = function_body(r31, "DWORD WINAPI R31InstallThread(void*)")
require(
    r31_install,
    "R31 install",
    "const auto r30 = R30InstallStatus();",
    "const auto renderer = R30SupportRendererInstallStatus();",
    "const bool lifecycleReady =",
    "StateBlockTracker::LifecycleHooksReady();",
    "R22 lifecycle hooks are authoritative; R31 is event-consumer only",
    "R31 physical StateBlock fallback retired; fast-path trust remains disabled",
    "StateBlockEvents::Clear();",
    "StateBlockRecovery::Clear();",
    "StateBlockTracker::MarkCoverageLost();",
)
# The R84 split puts the original renderer status in R29, not R30.
require(function_body(load(R29_PATH), "R29OwnerRendererInstallStatus()"),
        "R29 renderer-status physical owner",
        "return OutRunVRRenderer::R29RendererState();")
require(load(R29_API_PATH), "R29 renderer-status declaration",
        "R29OwnerRendererInstallStatus()")
r30_renderer_status = function_body(
    r30, "R30SupportRendererInstallStatus() noexcept")
require(
    r30_renderer_status,
    "R30 renderer-status support",
    "return R29OwnerRendererInstallStatus();",
)

forbid(
    r31_install,
    "R31 install",
    "DrawPrimitiveDestR30",
    "DrawIndexedPrimitiveDestR30",
    "DrawPrimitiveUPDestR30",
    "DrawIndexedPrimitiveUPDestR30",
    "fallbackEndArmed",
    "fallbackBeginArmed",
    "fallbackCreateArmed",
    "R31CreateStateBlockHook",
    "R31BeginStateBlockHook",
    "R31EndStateBlockHook",
    "R31StateBlockApplyHook",
    "safetyhook::create_inline(",
)
recovery_configure = r31_install.find("StateBlockRecovery::Configure(")
configure_pos = r31_install.find("StateBlockEvents::Configure(")
lifecycle_owner_pos = r31_install.find("const bool lifecycleReady =")
degraded_log_pos = r31_install.find(
    "R31 physical StateBlock fallback retired; fast-path trust remains disabled")
coverage_degrade_pos = r31_install.rfind(
    "StateBlockTracker::MarkCoverageLost()", 0, degraded_log_pos)
consumer_ready_pos = r31_install.find("StateBlockTracker::SetEventConsumerReady(true)")
ready_pos = r31_install.find("R31InstallState.store(State::Ready", consumer_ready_pos)
if min(recovery_configure, configure_pos, lifecycle_owner_pos,
       coverage_degrade_pos, degraded_log_pos, consumer_ready_pos, ready_pos) < 0 or not (
       recovery_configure < configure_pos < lifecycle_owner_pos <
       coverage_degrade_pos < degraded_log_pos < consumer_ready_pos < ready_pos):
    fail(
        "R31 must configure neutral StateBlock consumers, fail closed when "
        "R22 lifecycle coverage is absent, then publish readiness"
    )

require(
    stateblock,
    "StateBlockTracker",
    "return R22Reliable() &&",
    "EventConsumerReady() &&",
    "!CoverageLost();",
    "static bool LifecycleHooksReady() noexcept",
)

# 2) R32 is now a hook-free functional owner for DirectGPU, Reset/Present,
# fail-close and state helpers. All former physical Reset/Present/DirectGPU/draw
# overlays must be gone; R33 is the sole upper physical dispatcher.
forbid(
    r32,
    "R32",
    "SafetyHookInline R32DrawPrimitiveR31Hook{};",
    "SafetyHookInline R32DrawIndexedPrimitiveR31Hook{};",
    "SafetyHookInline R32DrawPrimitiveUPR31Hook{};",
    "SafetyHookInline R32DrawIndexedPrimitiveUPR31Hook{};",
    "HRESULT R32Dispatch(",
    "HRESULT __stdcall DrawPrimitiveDestR32(",
    "HRESULT __stdcall DrawIndexedPrimitiveDestR32(",
    "HRESULT __stdcall DrawPrimitiveUPDestR32(",
    "HRESULT __stdcall DrawIndexedPrimitiveUPDestR32(",
    "R31OwnedResult R32TryFastWorld(",
    "R31OwnedResult R32TryHud(",
    "SafetyHookInline R32PresentR13Hook{};",
    "HRESULT __stdcall PresentDestR32(",
    "SafetyHookInline R32ResetR22Hook{};",
    "HRESULT __stdcall ResetDestR32(",
    "SafetyHookInline R32ResolveDirectR13Hook{};",
    "ResolveDirectTransportR32(",
    "safetyhook::create_inline(",
)
require(
    r32,
    "R32 lifecycle owner",
    "void R32ObserveFrameWorkload(",
    "HRESULT R32WithPresentTelemetry(",
    "HRESULT R32WithResetLifecycle(",
    "bool R32ResolveDirectTransport(",
    "HRESULT R32LowerFailClosed(",
    "R32EffectIsFragileLive(",
    "R32SetWvpBatch(",
    "R32GetSavedViewport(",
    "R32RestoreRightPassState(",
)
for retired in (
    "R32InstallState",
    "R32InstallThread",
    "VRStereoR32ReviewHook",
    "R32InstallStatus()",
    "OpenXRVRStereoR32Review",
):
    if retired in r32:
        fail(f"R32 retained retired async install/status shim: {retired}")

reset_lifecycle = function_body(r32, "HRESULT R32WithResetLifecycle(")
require(
    reset_lifecycle,
    "R32 Reset lifecycle owner",
    "const HRESULT hr = lowerReset();",
    "R32ResetAfterGameReset();",
    "R32InvalidateResetCaches();",
    "++R32ResetFailures",
)
reset_lower = reset_lifecycle.find("const HRESULT hr = lowerReset();")
reset_success = reset_lifecycle.find("R32ResetAfterGameReset();")
reset_failure = reset_lifecycle.find("R32InvalidateResetCaches();", reset_lower)
if min(reset_lower, reset_success, reset_failure) < 0 or not (
        reset_lower < reset_success and reset_lower < reset_failure):
    fail("R32 Reset lifecycle must run lower R22 Reset before success/failure cache handling")
present_telemetry = function_body(r32, "HRESULT R32WithPresentTelemetry(")
require(
    present_telemetry,
    "R32 Present telemetry owner",
    "R32CaptureStereoWorkload()",
    "const HRESULT hr = lowerPresent();",
    "R32FinalizeFramePerf(",
    "R32LogPerfWindow()",
)
resolve32 = function_body(r32, "bool R32ResolveDirectTransport(")
require(
    resolve32,
    "R32 DirectGPU owner helper",
    "R30SupportOverlayReadyForTransport()",
    "return lowerResolve();",
    "R32EnsureDirectResources(device)",
    "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)",
    "DirectTransportFrameReadyAfterPresent() is",
    "R30SupportMarkDirectTransportSlotPending(selected, frameId);",
    "R30SupportSetActiveDirectTransportSlot(selected);",
)
forbid(
    resolve32,
    "R32 DirectGPU pre-Present fence wait retirement",
    "R32WaitProducerFence(slot.fence)",
    "R32ProducerFencePending[selected] = true;",
    "R32ProducerPendingFrame[selected] = frameId;",
)
lower_fail_closed = function_body(r32, "HRESULT R32LowerFailClosed(")
require(
    lower_fail_closed,
    "R32 lower fail-close",
    "!R30SupportStereoBaselineSeeded()",
    "R30SupportExchangeVertexShaderIdentity(0)",
    "const HRESULT hr = lowerDraw();",
    "R30SupportRestoreVertexShaderIdentityIfEmpty(savedIdentity)",
    "R32FailClosedZeroDisparityDraws",
)

# 3) R33 is the sole upper physical Reset/Present/DirectGPU/draw dispatcher.
# Reset hooks R22; Present and DirectGPU hook R13; draws hook R30. R32 semantics
# are preserved through owner helpers without retaining any physical hook.
forbid(
    r33,
    "R33",
    "R33DrawPrimitiveR32Hook",
    "R33DrawIndexedPrimitiveR32Hook",
    "R33DrawPrimitiveUPR32Hook",
    "R33DrawIndexedPrimitiveUPR32Hook",
    "reinterpret_cast<void*>(&DrawPrimitiveDestR32)",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR32)",
    "reinterpret_cast<void*>(&DrawPrimitiveUPDestR32)",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR32)",
)
require(
    r33,
    "R33",
    "SafetyHookInline R33DrawPrimitiveR30Hook{};",
    "SafetyHookInline R33DrawIndexedPrimitiveR30Hook{};",
    "SafetyHookInline R33DrawPrimitiveUPR30Hook{};",
    "SafetyHookInline R33DrawIndexedPrimitiveUPR30Hook{};",
    "R32ReviewDrawPrimitiveTarget()",
    "R32ReviewDrawIndexedPrimitiveTarget()",
    "R32ReviewDrawPrimitiveUPTarget()",
    "R32ReviewDrawIndexedPrimitiveUPTarget()",
    "SafetyHookInline R33ResetR22Hook{};",
    "R32ReviewResetTarget()",
    "R32ReviewRunResetLifecycle(",
    "R33ResetR22Hook.stdcall<HRESULT>",
    "SafetyHookInline R33PresentR13Hook{};",
    "R32ReviewPresentTarget()",
    "R32ReviewRunPresentTelemetry(",
    "R33PresentR13Hook.stdcall<HRESULT>",
    "SafetyHookInline R33ResolveDirectR13Hook{};",
    "R32ReviewDirectTransportTarget()",
    "ResolveDirectTransportDestR33",
    "R32ReviewResolveDirectTransport(",
    "R33ResolveDirectR13Hook.call<bool>",
)
require(
    r32,
    "R32 split target facade",
    "R32ReviewDrawPrimitiveTarget() noexcept{return R30SupportDrawPrimitiveTarget();}",
    "R32ReviewDrawIndexedPrimitiveTarget() noexcept{return R30SupportDrawIndexedPrimitiveTarget();}",
    "R32ReviewDrawPrimitiveUPTarget() noexcept{return R30SupportDrawPrimitiveUPTarget();}",
    "R32ReviewDrawIndexedPrimitiveUPTarget() noexcept{return R30SupportDrawIndexedPrimitiveUPTarget();}",
    "R32ReviewResetTarget() noexcept{return R30SupportResetTarget();}",
    "R32ReviewPresentTarget() noexcept{return R30SupportPresentTarget();}",
    # R30 support now owns the same physical lower target addresses.
    # A separate fail-closed owner verifier protects the exact R22/R13 identities.
    "R32ReviewDirectTransportTarget() noexcept{return R30SupportDirectTransportTarget();}",
)

# R30, not R32, owns the physical lower target pointers after the split.
for label in ("DrawPrimitive", "DrawIndexedPrimitive", "DrawPrimitiveUP", "DrawIndexedPrimitiveUP"):
    lower = function_body(r30, f"void* R30Support{label}Target() noexcept")
    require(lower, f"R30 {label} hook target owner",
            f"reinterpret_cast<void*>(&{label}DestR30)")

r33_install = function_body(r33, "DWORD WINAPI R33InstallThread(void*)")
require(
    r33_install,
    "R33 split prerequisite ownership",
    "const auto prerequisites = R32ReviewPrerequisiteStatus();",
    "prerequisites == State::Failed",
    "prerequisites == State::Ready",
    "R33ReportInstallResult(false);",
    "R33ReportInstallResult(true);",
)
require(
    r32,
    "R32 split prerequisite delegation",
    "R32ReviewPrerequisiteStatus() noexcept",
    "R31SupportInstallStatus()",
    "const auto lower = R30SupportLowerPrerequisiteStatus();",
    "lower == State::Failed",
    "lower == State::Ready",
)
forbid(
    r33_install,
    "R33 direct prerequisite ownership",
    "R32InstallStatus()",
    "R32InstallState",
)

direct33 = function_body(r33, "bool ResolveDirectTransportDestR33(")
require(
    direct33,
    "R33 direct DirectGPU owner",
    "R32ReviewResolveDirectTransport(",
    "R33ResolveDirectR13Hook.call<bool>",
)
if direct33.find("R32ReviewResolveDirectTransport(") > direct33.find(
        "R33ResolveDirectR13Hook.call<bool>"):
    fail("R32 DirectGPU helper must own the direct R13 trampoline call")

reset33 = function_body(r33, "HRESULT __stdcall ResetDestR33(")
require(
    reset33,
    "R33 direct Reset owner",
    "R32ReviewRunResetLifecycle(",
    "R33ResetR22Hook.stdcall<HRESULT>",
    "R33InvalidateDepthStencilCache();",
    "R33SetResetReplayGuardState(",
)
if reset33.find("R32ReviewRunResetLifecycle(") > reset33.find(
        "R33ResetR22Hook.stdcall<HRESULT>"):
    fail("R32 Reset lifecycle helper must own the direct R22 Reset call")
if reset33.find("R33ResetR22Hook.stdcall<HRESULT>") > reset33.find(
        "R33InvalidateDepthStencilCache();"):
    fail("R33 depth/replay post-processing must remain after the wrapped R22 Reset")

present33 = function_body(r33, "HRESULT __stdcall PresentDestR33(")
require(
    present33,
    "R33 direct Present owner",
    "R32ReviewRunPresentTelemetry(",
    "R33PresentR13Hook.stdcall<HRESULT>",
)
if present33.find("Present/pre") > present33.find("R32ReviewRunPresentTelemetry("):
    fail("R33 must reassert Reset replay fail-close before R32 Present telemetry/lower Present")
if present33.find("R32ReviewRunPresentTelemetry(") > present33.find(
        "R33PresentR13Hook.stdcall<HRESULT>"):
    fail("R32 Present telemetry wrapper must own the direct R13 Present call")

# R32 workload telemetry used to live at its draw entry. Once R33 hooks R30
# directly, R33 must preserve the same one-call-per-top-level-draw accounting.
for marker, expected in (
    ("HRESULT __stdcall DrawPrimitiveDestR33(", "R32ReviewObserveFrameWorkload(device, type, primitiveCount, false, false);"),
    ("HRESULT __stdcall DrawIndexedPrimitiveDestR33(", "R32ReviewObserveFrameWorkload(device, type, primitiveCount, true, false);"),
    ("HRESULT __stdcall DrawPrimitiveUPDestR33(", "R32ReviewObserveFrameWorkload(device, type, primitiveCount, false, true);"),
    ("HRESULT __stdcall DrawIndexedPrimitiveUPDestR33(", "R32ReviewObserveFrameWorkload(device, type, primitiveCount, true, true);"),
):
    body = function_body(r33, marker)
    if expected not in body:
        fail(f"R33 draw entry lost R32 workload accounting: {expected}")

# 4) Final fallback remains fail-closed through R32 and then R30-owned lower R29.
dispatch33 = function_body(
    r33, "HRESULT R33Dispatch(IDirect3DDevice9* device,")
require(
    dispatch33,
    "R33 dispatch",
    "R32ReviewDiscardUnreliableDrawCaches();",
    "return R32ReviewRunLowerFailClosed(device,",
    "std::forward<LowerR29Draw>(lowerR29Draw)",
)
for marker in (
    "R32ReviewCallLowerDrawPrimitive(",
    "R32ReviewCallLowerDrawIndexedPrimitive(",
    "R32ReviewCallLowerDrawPrimitiveUP(",
    "R32ReviewCallLowerDrawIndexedPrimitiveUP(",
):
    if marker not in r33:
        fail(f"R33 final fallback lost R32 split facade lower-owner call: {marker}")

for function_marker, owner_marker in (
    ("R30CallLowerDrawPrimitive(", "R30DrawPrimitiveR29Hook.stdcall<HRESULT>"),
    ("R30CallLowerDrawIndexedPrimitive(", "R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>"),
    ("R30CallLowerDrawPrimitiveUP(", "R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>"),
    ("R30CallLowerDrawIndexedPrimitiveUP(", "R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>"),
):
    body = function_body(r30, f"inline HRESULT {function_marker}")
    if owner_marker not in body:
        fail(
            f"{function_marker.rstrip('(')} no longer delegates to "
            f"{owner_marker}"
        )

# 5) Canonical DX9Ex Active CI owns this guard.
require(
    workflow,
    "DX9Ex Active workflow",
    "- 'tools/verify_vr_r31_r32_retirement_guard.py'",
    "'tools/verify_vr_r31_r32_retirement_guard.py'",
    "foreach ($verifier in $verifiers)",
    "python $verifier",
    "if ($LASTEXITCODE -ne 0)",
)

print(
    "VR R31/R32 draw-retirement guard PASS "
    "(R31=StateBlock owner, R32=hook-free DirectGPU + Reset/Present helper owner, "
    "R33=sole physical draw dispatcher over R30, neutral-helper census=terminal, remaining R31/R32 calls=owner-specific)"
)
