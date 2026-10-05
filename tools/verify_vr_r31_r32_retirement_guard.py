#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

R30_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
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
    "R33 neutral shader dependency",
    "OutRunVR::D3D9::LiveVertexShaderMatches(device, cachedShader)",
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
if r33.count("R32SetWvpBatch(") < 4:
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
    "R31GetSavedViewport(device, viewport)",
    "OutRunVR::D3D9::ReadViewport(device, viewport)",
)
forbid(
    r32_viewport,
    "R32 saved viewport policy",
    "device->GetViewport(&viewport)",
)
if r33.count("R32GetSavedViewport(") < 2:
    fail("R33 viewport sites unexpectedly stopped using the R32 StateBlock-aware wrapper")

# Terminal post-1100 dependency census: every remaining R33 -> R31/R32 call is
# intentionally owner-specific. Any new cross-layer call must be reviewed rather
# than silently growing this dependency surface.
expected_owner_calls = {
    "R31BuildFastWorldConstants",
    "R31DiscardUnreliableDrawCaches",
    "R31ObserveDraw",
    "R31TelemetryNoteFallback",
    "R31TelemetryNoteFastWorld",
    "R31TelemetryNoteFragile",
    "R31TelemetryNoteHud",
    "R31TelemetryNoteUnstable",
    "R32EffectIsFragileLive",
    "R32GetSavedViewport",
    "R32InstallStatus",
    "R32LowerFailClosed",
    "R32ObserveFrameWorkload",
    "R32RestoreRightPassState",
    "R32SetWvpBatch",
}
observed_owner_calls = set(re.findall(r"\b(R3[12]\w+)\s*\(", r33))
if observed_owner_calls != expected_owner_calls:
    missing = sorted(expected_owner_calls - observed_owner_calls)
    added = sorted(observed_owner_calls - expected_owner_calls)
    fail(
        "terminal R33 owner-boundary census changed: "
        f"missing={missing}, added={added}"
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
    "R32EffectIsFragileLive": (
        r32, "bool R32EffectIsFragileLive(",
        ("R32ReadEffectSnapshot(device, state)",
         "PassPolicy::ClassifyEffectStereo(",
         "PassPolicy::AllowsEffectWorldStereo(policy)"),
    ),
    "R32GetSavedViewport": (
        r32, "bool R32GetSavedViewport(",
        ("StateBlockTracker::Reliable()",
         "R31GetSavedViewport(device, viewport)",
         "OutRunVR::D3D9::ReadViewport(device, viewport)"),
    ),
    "R32InstallStatus": (
        r32, "R32InstallStatus() noexcept",
        ("R32InstallState.load(std::memory_order_acquire)",),
    ),
    "R32LowerFailClosed": (
        r32, "HRESULT R32LowerFailClosed(",
        ("R32ReadEffectSnapshot(device, snapshot)",
         "CurrentVertexShaderIdentity.exchange(0",
         "R32FailClosedZeroDisparityDraws"),
    ),
    "R32ObserveFrameWorkload": (
        r32, "void R32ObserveFrameWorkload(",
        ("Settings::VRTelemetry", "R32FrameWorkloadCounters",
         "frame.primitives += primitiveCount",
         "TryGetEffectTelemetrySnapshot(effect)"),
    ),
    "R32RestoreRightPassState": (
        r32, "bool R32RestoreRightPassState(",
        ("SetRenderTargetHook.stdcall<HRESULT>",
         "SetDepthStencilSurfaceHook",
         "device->SetViewport(&savedViewport)",
         "R32SetWvpBatch(device, originalConstants)"),
    ),
    "R32SetWvpBatch": (
        r32, "bool R32SetWvpBatch(",
        ("R32BatchWvpUploads",
         "OutRunVR::D3D9::SetVertexShaderConstantBatch(",
         "R32BatchWvpFailures"),
    ),
}
if set(owner_evidence) != expected_owner_calls:
    missing = sorted(expected_owner_calls - set(owner_evidence))
    added = sorted(set(owner_evidence) - expected_owner_calls)
    fail(
        "terminal owner-evidence map drifted from census: "
        f"missing={missing}, added={added}"
    )
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
    "CurrentVertexShaderIdentity.exchange(0",
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
    "SetRenderTargetHook.stdcall<HRESULT>",
    "SetDepthStencilSurfaceHook",
    "device->SetViewport(&savedViewport)",
    "R32SetWvpBatch(device, originalConstants)",
)
require(
    function_body(r32, "R32InstallStatus() noexcept"),
    "R32 install-state owner",
    "R32InstallState.load(std::memory_order_acquire)",
)

# 1) R31 is retained only for StateBlock/state-cache ownership. Its physical
# draw overlay over R30 must be gone.
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
)
require(
    r31,
    "R31 StateBlock owner",
    "SafetyHookInline R31CreateStateBlockHook{};",
    "SafetyHookInline R31BeginStateBlockHook{};",
    "SafetyHookInline R31EndStateBlockHook{};",
    "SafetyHookInline R31StateBlockApplyHook{};",
    "StateBlockRecovery::Configure(",
    "StateBlockEvents::Configure(",
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
    "const auto renderer = OutRunVRRenderer::R29RendererState();",
    "StateBlockTracker::LifecycleHooksReady()",
    "R22 lifecycle hooks are authoritative; R31 physical StateBlock hooks are not installed",
    "R31 fallback StateBlock hooks armed",
    "fallbackEndArmed = R31EndStateBlockHook.enable().has_value();",
    "fallbackBeginArmed = R31BeginStateBlockHook.enable().has_value();",
    "fallbackCreateArmed = R31CreateStateBlockHook.enable().has_value();",
    "StateBlockEvents::Clear();",
    "StateBlockRecovery::Clear();",
    "StateBlockTracker::MarkCoverageLost();",
)
forbid(
    r31_install,
    "R31 install",
    "DrawPrimitiveDestR30",
    "DrawIndexedPrimitiveDestR30",
    "DrawPrimitiveUPDestR30",
    "DrawIndexedPrimitiveUPDestR30",
    "draw hooks unavailable",
)
fallback_end = r31_install.find(
    "fallbackEndArmed = R31EndStateBlockHook.enable().has_value();")
fallback_begin = r31_install.find(
    "fallbackBeginArmed = R31BeginStateBlockHook.enable().has_value();")
fallback_create = r31_install.find(
    "fallbackCreateArmed = R31CreateStateBlockHook.enable().has_value();")
ready_publish = r31_install.find(
    "StateBlockTracker::SetEventConsumerReady(true)")
if min(fallback_end, fallback_begin, fallback_create, ready_publish) < 0 or not (
    fallback_end < fallback_begin < fallback_create < ready_publish
):
    fail(
        "R31 fallback StateBlock transaction must arm End -> Begin -> Create "
        "before publishing EventConsumerReady"
    )

require(
    stateblock,
    "StateBlockTracker",
    "return R22Reliable() &&",
    "EventConsumerReady() &&",
    "!CoverageLost();",
    "static bool LifecycleHooksReady() noexcept",
)

# 2) R32 is retained only for Reset/Present/DirectGPU and fail-close helpers.
# Its physical draw overlay over R31 must be gone.
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
)
require(
    r32,
    "R32 lifecycle owner",
    "SafetyHookInline R32ResetR22Hook{};",
    "SafetyHookInline R32ResolveDirectR13Hook{};",
    "SafetyHookInline R32PresentR13Hook{};",
    "void R32ObserveFrameWorkload(",
    "HRESULT R32LowerFailClosed(",
    "R32InstallStatus() noexcept",
    "R32EffectIsFragileLive(",
    "R32SetWvpBatch(",
    "R32GetSavedViewport(",
    "R32RestoreRightPassState(",
)
r32_install = function_body(r32, "DWORD WINAPI R32InstallThread(void*)")
require(
    r32_install,
    "R32 install",
    "const auto r31 = R31InstallStatus();",
    "const auto r22 = R22InstallStatus();",
    "const auto r13 = R13InstallStatus();",
    "r31 == State::Failed || r22 == State::Failed",
    "r31 == State::Ready && r22 == State::Ready",
    "reinterpret_cast<void*>(&ResetDestR22), ResetDestR32, disabled",
    "reinterpret_cast<void*>(&ResolveDirectTransportR13)",
    "ResolveDirectTransportR32, disabled",
    "reinterpret_cast<void*>(&PresentDestR13), PresentDestR32, disabled",
)
forbid(
    r32_install,
    "R32 install",
    "DrawPrimitiveDestR31",
    "DrawIndexedPrimitiveDestR31",
    "DrawPrimitiveUPDestR31",
    "DrawIndexedPrimitiveUPDestR31",
)
reset32 = function_body(r32, "HRESULT __stdcall ResetDestR32(")
if reset32.find("R32ResetR22Hook.stdcall<HRESULT>") > reset32.find(
        "R32ResetAfterGameReset();"):
    fail("R32 Reset must complete R22 before R32 rearm")
present32 = function_body(r32, "HRESULT __stdcall PresentDestR32(")
require(present32, "R32 Present", "R32PresentR13Hook.stdcall<HRESULT>")
resolve32 = function_body(r32, "bool ResolveDirectTransportR32(")
require(resolve32, "R32 DirectGPU", "R32ResolveDirectR13Hook.call<bool>")
lower_fail_closed = function_body(r32, "HRESULT R32LowerFailClosed(")
require(
    lower_fail_closed,
    "R32 lower fail-close",
    "!R9StereoBaselineSeeded()",
    "CurrentVertexShaderIdentity.exchange(0",
    "const HRESULT hr = lowerDraw();",
    "R32FailClosedZeroDisparityDraws",
)

# 3) R33 is the only physical draw dispatcher. Reset/Present intentionally
# remain chained through R32, while all four draw families hook R30 directly.
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
    "reinterpret_cast<void*>(&DrawPrimitiveDestR30)",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR30)",
    "reinterpret_cast<void*>(&DrawPrimitiveUPDestR30)",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR30)",
    "R33ResetR32Hook.stdcall<HRESULT>",
    "R33PresentR32Hook.stdcall<HRESULT>",
)

# R32 workload telemetry used to live at its draw entry. Once R33 hooks R30
# directly, R33 must preserve the same one-call-per-top-level-draw accounting.
for marker, expected in (
    ("HRESULT __stdcall DrawPrimitiveDestR33(", "R32ObserveFrameWorkload(device, type, primitiveCount, false, false);"),
    ("HRESULT __stdcall DrawIndexedPrimitiveDestR33(", "R32ObserveFrameWorkload(device, type, primitiveCount, true, false);"),
    ("HRESULT __stdcall DrawPrimitiveUPDestR33(", "R32ObserveFrameWorkload(device, type, primitiveCount, false, true);"),
    ("HRESULT __stdcall DrawIndexedPrimitiveUPDestR33(", "R32ObserveFrameWorkload(device, type, primitiveCount, true, true);"),
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
    "R31DiscardUnreliableDrawCaches();",
    "return R32LowerFailClosed(device,",
    "std::forward<LowerR29Draw>(lowerR29Draw)",
)
for marker in (
    "R30CallLowerDrawPrimitive(",
    "R30CallLowerDrawIndexedPrimitive(",
    "R30CallLowerDrawPrimitiveUP(",
    "R30CallLowerDrawIndexedPrimitiveUP(",
):
    if marker not in r33:
        fail(f"R33 final fallback lost R30 owner call: {marker}")

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
    "(R31=StateBlock owner, R32=Reset/Present/DirectGPU owner, "
    "R33=sole physical draw dispatcher over R30, neutral-helper census=terminal, remaining R31/R32 calls=owner-specific)"
)
