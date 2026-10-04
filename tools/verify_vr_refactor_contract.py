#!/usr/bin/env python3
"""Deterministic guards for the staged VR R-series flattening."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def text(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        errors.append(f"missing required refactor file: {rel}")
        return ""
    return p.read_text(encoding="utf-8")

r22 = text("src/vr/d3d9/stereo_renderer_r22.cpp")
r23 = text("src/vr/d3d9/stereo_renderer_r23.cpp")
r9 = text("src/vr/d3d9/stereo_renderer.cpp")
r13 = text("src/vr/d3d9/stereo_renderer_r13.cpp")
r20 = text("src/vr/d3d9/stereo_renderer_r20.cpp")
r21 = text("src/vr/d3d9/stereo_renderer_r21.cpp")
r29 = text("src/vr/d3d9/stereo_renderer_r29.cpp")
r26 = text("src/vr/d3d9/stereo_renderer_r26.cpp")
r31 = text("src/vr/d3d9/stereo_renderer_r31.cpp")
r32 = text("src/vr/d3d9/stereo_renderer_r32.cpp")
r33 = text("src/vr/d3d9/stereo_renderer_r33.cpp")
r34 = text("src/vr/d3d9/stereo_renderer_r34.cpp")
renderer_r29 = text("src/vr/game/outrun_renderer_r29.cpp")
draw_class = text("src/vr/render/draw_class.hpp")
raster = text("src/vr/state/d3d9_raster_state.hpp")
state_block_tracker = text("src/vr/state/state_block_tracker.hpp")
state_block_recovery = text("src/vr/state/state_block_recovery.hpp")
state_block_events = text("src/vr/state/state_block_events.hpp")
overlay_hooks = text("src/overlay/hooks_overlay.cpp")
render_semantics = text("src/vr/game/render_semantics.hpp")
r30_safe = text("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
text("tools/verify_vr_hook_graph.py")

# F11/Tweaks ImGui is external screen-space UI. During gameplay it must not
# consume a pending game semantic token, and it must enter the already-proven
# SCREEN_OVERLAY_2D stereo convergence path instead of falling back to R26.
for marker in (
    "ScopedExternalOverlaySemantic",
    "ExternalOverlaySemanticDepth",
    "if (ExternalOverlaySemanticDepth != 0)",
):
    if marker not in render_semantics:
        errors.append(f"render semantics missing external-overlay guard: {marker}")
for marker in (
    "ScopedExternalOverlaySemantic",
    "RenderScope::ScreenOverlay2D",
    "ImGui_ImplDX9_RenderDrawData",
):
    if marker not in overlay_hooks:
        errors.append(f"F11 overlay missing explicit stereo semantic scope: {marker}")
if "CorroboratesScreenOverlay2D" not in r30_safe or "semanticOverlay2D" not in r30_safe:
    errors.append("active R26+R30 path missing SCREEN_OVERLAY_2D owner route")

if "R22FailClosedReplayState" in r23:
    errors.append("R23 retained private R22 fail-closed replay dependency")
if "FailClosedTrackedRasterReplay(" not in r22:
    errors.append("R22 missing fail-closed raster owner API")
if "FailClosedTrackedRasterReplay(" not in r23:
    errors.append("R23 missing fail-closed raster owner API use")

if "R23GameDrawSerial" in r29:
    errors.append("R29 retained direct R23 draw-serial state dependency")
if "TopLevelDrawSerial()" not in r29:
    errors.append("R29 missing R23 draw-serial owner query")

if "R22PrimeShadowState" in r31:
    errors.append("R31 retained private R22 raster-prime dependency")
if "PrimeTrackedRasterShadow(" not in r22:
    errors.append("R22 missing raster-prime owner API")
if "PrimeTrackedRasterShadow" not in r31:
    errors.append("R31 missing raster-prime owner API use")

for banned in ("R22ScissorSnapshot", "R22CaptureGameScissor",
               "R22GameClearCoversBackbuffer"):
    if banned in r23:
        errors.append(
            f"R23 retained private R22 raster helper dependency: {banned}")
for marker in ("CaptureTrackedRasterState(", "TrackedGameClearCoversBackbuffer("):
    if marker not in r22:
        errors.append(f"R22 missing raster owner API: {marker}")
    if marker not in r23:
        errors.append(f"R23 missing raster owner API use: {marker}")

for banned in ("R22ShadowState", "R22StateBlockTrackingReliable"):
    if banned in r23:
        errors.append(f"R23 regained direct lower-layer state dependency: {banned}")
if "R22StateBlockTrackingReliable" in r22:
    errors.append("R22 retained removed StateBlock reliability authority")
if "StateBlockTracker::SetLifecycleHooksReady(stateBlockHooks)" not in r22.replace("\n", " ").replace("  ", " "):
    # Whitespace-independent fallback below checks the two required markers.
    if not ("SetLifecycleHooksReady(" in r22 and "stateBlockHooks" in r22):
        errors.append("R22 missing neutral StateBlock lifecycle coverage publication")
if "StateBlockTracker::SetLifecycleHooksReady(false)" not in r22:
    errors.append("R22 rollback/install path missing lifecycle coverage reset")

for rel, source in (
    ("R20", r20), ("R23", r23), ("R29", r29),
    ("R31", r31), ("R32", r32), ("R33", r33),
):
    for banned in ("R9MainDepthContentSerial", "R9MonoDepthContentSerial"):
        if banned in source:
            errors.append(
                f"{rel} retained direct R9 depth-content state dependency: {banned}")
for marker in (
    "R9SynchronizeDepthContentSerials()",
    "R9NoteMainDepthContentWrite()",
):
    if marker not in r9:
        errors.append(f"R9 missing depth-content owner API: {marker}")
for rel, source in (("R20", r20), ("R23", r23)):
    if "R9SynchronizeDepthContentSerials()" not in source:
        errors.append(f"{rel} missing R9 depth-content synchronization owner API")
for rel, source in (("R29", r29), ("R31", r31), ("R32", r32), ("R33", r33)):
    if "R9NoteMainDepthContentWrite()" not in source:
        errors.append(f"{rel} missing R9 main-depth write owner API")

for banned in ("R23GameDrawSerial", "R23BeforeTopLevelDraw", "GetTopLevelDrawSerial()"):
    if banned in r26:
        errors.append(f"R26 regained R23 implementation dependency: {banned}")

for marker, source, owner in (
    ("InvalidateLiveStateSample()", r23, "R23"),
    ("InvalidateEffectStateCache()", r29, "R29"),
    ("ArmStereoRecoverySafety(", r29, "R29"),
):
    if marker not in source:
        errors.append(f"{owner} missing explicit cache invalidation API: {marker}")

for banned in (
    "R29Effect",
    "R23LastStateSampleDrawSerial",
    "R23LastStateSampleEpoch",
    "R22ShadowState",
    "R29ArmMonoSafety",
):
    if banned in r31:
        errors.append(
            f"R31 regained direct lower-layer cache mutation: {banned}")

for marker in (
    "InvalidateEffectStateCache()",
    "InvalidateTrackedRasterShadow()",
    "InvalidateLiveStateSample()",
    "TryGetTrackedViewport(viewport)",
    "ArmStereoRecoverySafety()",
):
    if marker not in r31:
        errors.append(
            f"R31 missing owner cache invalidation boundary: {marker}")

required_r22 = (
    '#include "../state/d3d9_raster_state.hpp"',
    "using R22ScissorSnapshot = OutRunVR::State::D3D9RasterSnapshot;",
    "GetTrackedRasterShadow()",
    "TryGetTrackedViewport(",
    "SetTrackedRasterShadow(",
    "InvalidateTrackedRasterShadow()",
    "IsTrackedStateBlockReliable()",
)
for marker in required_r22:
    if marker not in r22:
        errors.append(f"R22 missing state-boundary marker: {marker}")

for marker in (
    "enum class DrawClass",
    "FromGameSemantic",
    "FromHudSpace",
    "FromPassSemantic",
):
    if marker not in draw_class:
        errors.append(f"draw semantic contract missing: {marker}")

if "SameRasterSnapshot" not in raster:
    errors.append("neutral raster snapshot comparison missing")

for marker in (
    "class StateBlockTracker",
    "SetR22Reliable(",
    "R22Reliable()",
    "SetEventConsumerReady(",
    "EventConsumerReady()",
    "Reliable()",
    "SetLifecycleHooksReady(",
    "LifecycleHooksReady()",
    "MarkCoverageLost()",
    "ResetCoverageLoss()",
    "CoverageLost()",
    "RequireResync()",
    "ConsumeResync()",
    "NoteRecording()",
    "NoteApply()",
    "RecordingGeneration()",
    "ApplyGeneration()",
    "SetRecording(",
    "Recording()",
):
    if marker not in state_block_tracker:
        errors.append(f"StateBlockTracker missing API marker: {marker}")

for rel, source in (
    ("R22", r22),
    ("R31", r31),
    ("R33", r33),
):
    if '../state/state_block_tracker.hpp' not in source:
        errors.append(f"{rel} missing neutral StateBlockTracker include")
if '../state/state_block_events.hpp' not in r22:
    errors.append("R22 missing neutral StateBlock event boundary include")

for rel, source in (("R32", r32), ("R33", r33)):
    if "R31StateBlockTrackingReliable" in source:
        errors.append(
            f"{rel} regained removed R31 StateBlock reliability dependency")

for banned in ("R31StateBlockRecordings", "R31StateBlockApplies"):
    for rel, source in (("R32", r32), ("R33", r33)):
        if banned in source:
            errors.append(
                f"{rel} regained R31 StateBlock generation dependency: {banned}")
    if banned in r31:
        errors.append(
            f"R31 retained migrated StateBlock generation owner: {banned}")

for marker in (
    "class StateBlockEvents",
    "Configure(",
    "Configured()",
    "Clear()",
    "NotifyBegin(",
    "NotifyEnd(",
    "NotifyApply(",
):
    if marker not in state_block_events:
        errors.append(f"StateBlockEvents missing API marker: {marker}")

clear_events = re.search(
    r"static void Clear\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_events,
    re.DOTALL,
)
if not clear_events:
    errors.append("StateBlockEvents Clear body missing")
else:
    clear_body = clear_events.group("body")
    begin_clear = clear_body.find("BeginCallback().store(nullptr")
    end_clear = clear_body.find("EndCallback().store(nullptr")
    apply_clear = clear_body.find("ApplyCallback().store(nullptr")
    if min(begin_clear, end_clear, apply_clear) < 0:
        errors.append("StateBlockEvents callback clear marker missing")
    elif not (begin_clear < end_clear and begin_clear < apply_clear):
        errors.append(
            "StateBlockEvents must clear Begin before terminal callbacks")

configure_events = re.search(
    r"static void Configure\(BeginFn begin, EndFn end, ApplyFn apply\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_events,
    re.DOTALL,
)
if not configure_events:
    errors.append("StateBlockEvents Configure body missing")
else:
    configure_body = configure_events.group("body")
    begin_publish = configure_body.find("BeginCallback().store")
    end_publish = configure_body.find("EndCallback().store")
    apply_publish = configure_body.find("ApplyCallback().store")
    if min(begin_publish, end_publish, apply_publish) < 0:
        errors.append("StateBlockEvents callback publication marker missing")
    elif not (end_publish < begin_publish and apply_publish < begin_publish):
        errors.append(
            "StateBlockEvents must publish End/Apply callbacks before Begin")

for marker in (
    "class StateBlockRecovery",
    "Configure(",
    "Clear()",
    "FlushPendingResync(",
    "StateBlockTracker::ConsumeResync()",
):
    if marker not in state_block_recovery:
        errors.append(f"StateBlockRecovery missing API marker: {marker}")

clear_recovery = re.search(
    r"static void Clear\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_recovery,
    re.DOTALL,
)
if not clear_recovery:
    errors.append("StateBlockRecovery Clear body missing")
else:
    clear_body = clear_recovery.group("body")
    if "ResynchronizeShaderEpoch().store(nullptr" not in clear_body or \
            "PrimeShadowState().store(nullptr" not in clear_body:
        errors.append("StateBlockRecovery Clear must withdraw both providers")

flush_match = re.search(
    r"static void FlushPendingResync\(IDirect3DDevice9\* device\) noexcept\s*\{(?P<body>.*?)\n        \}",
    state_block_recovery,
    re.DOTALL,
)
if not flush_match:
    errors.append("StateBlockRecovery FlushPendingResync body missing")
else:
    flush_body = flush_match.group("body")
    callback_ready = flush_body.find("if (!resynchronizeShaderEpoch || !primeShadowState)")
    consume = flush_body.find("StateBlockTracker::ConsumeResync()")
    shader_resync = flush_body.find("resynchronizeShaderEpoch(device)")
    shadow_prime = flush_body.find("primeShadowState(device)")
    if min(callback_ready, consume, shader_resync, shadow_prime) < 0:
        errors.append("StateBlockRecovery recovery-order marker missing")
    elif not callback_ready < consume < shader_resync < shadow_prime:
        errors.append(
            "StateBlockRecovery must validate callbacks before consuming resync "
            "and preserve shader-resync before shadow-prime ordering")

for rel, source in (("R32", r32), ("R33", r33), ("R34", r34)):
    for banned in (
        "R31FastWorldDraws",
        "R31FastWorldLiveValidations",
        "R31FastWorldValidationRejects",
        "R31HudDraws",
        "R31Frame",
        "R31Window",
    ):
        if banned in source:
            errors.append(
                f"{rel} retained direct R31 telemetry state dependency: {banned}")

for marker in (
    "R31TelemetryNoteFastWorld()",
    "R31TelemetryNoteHud()",
    "R31TelemetryNoteFallback()",
    "R31TelemetryNoteUnstable()",
    "R31TelemetryNoteFragile()",
    "R31TelemetryResetFrameWindow()",
    "R31TelemetryFrameSnapshot()",
    "R31TelemetryLiveWvpChecks()",
    "R31TelemetryLiveWvpRejects()",
):
    if marker not in r31:
        errors.append(f"R31 missing owner telemetry API: {marker}")

for name, required in (
    ("R31TelemetryNoteFastWorld", ("++R31FastWorldDraws;", "++R31Frame.fastWorld;")),
    ("R31TelemetryNoteHud", ("++R31HudDraws;", "++R31Frame.hud;")),
):
    match = re.search(
        rf"inline void {name}\(\) noexcept\s*\{{(?P<body>.*?)\n        \}}",
        r31,
        re.DOTALL,
    )
    if not match:
        errors.append(f"R31 telemetry owner body missing: {name}")
        continue
    body = match.group("body")
    if f"{name}();" in body:
        errors.append(f"R31 telemetry owner recurses into itself: {name}")
    for required_marker in required:
        if required_marker not in body:
            errors.append(
                f"R31 telemetry owner missing counter update: {name} -> {required_marker}")

window_decl = r31.find("R31WindowPerf R31Window{};")
reset_window = r31.find("inline void R31TelemetryResetFrameWindow()")
if min(window_decl, reset_window) < 0 or not window_decl < reset_window:
    errors.append(
        "R31 telemetry reset API must be declared after the R31 window owner")

for banned in (
    "R31BlockedVerifiedGeneration =",
    "R31FastWorldCandidates =",
    "R31EyeCache =",
):
    if banned in r32:
        errors.append(
            f"R32 retained direct R31 reset-state ownership: {banned}")
    if banned in r33 or banned in r34:
        errors.append(
            f"upper renderer retained direct R31 reset-state ownership: {banned}")

reset_fast = re.search(
    r"inline void R31ResetFastPathState\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    r31,
    re.DOTALL,
)
if not reset_fast:
    errors.append("R31 fast-path reset owner API missing")
else:
    reset_body = reset_fast.group("body")
    reset_order = [
        reset_body.find("R31BlockedVerifiedGeneration = 0;"),
        reset_body.find("R31FastWorldCandidates = 0;"),
        reset_body.find("R31EyeCache = {};"),
        reset_body.find("R31TelemetryResetFrameWindow();"),
    ]
    if min(reset_order) < 0 or reset_order != sorted(reset_order):
        errors.append(
            "R31 fast-path reset API must preserve blocked/candidate/eye/telemetry order")

if "R31ResetFastPathState();" not in r32:
    errors.append("R32 reset path missing R31 fast-path owner reset API")

for banned, owner_api in (
    ("R29Effect = {};", "InvalidateEffectStateCache();"),
    ("R23LastStateSampleDrawSerial = 0;", "InvalidateLiveStateSample();"),
    ("R23LastStateSampleEpoch = 0;", "InvalidateLiveStateSample();"),
):
    if banned in r32:
        errors.append(
            f"R32 retained lower-layer reset-state ownership: {banned}")
    if owner_api not in r32:
        errors.append(
            f"R32 reset path missing lower-layer owner API: {owner_api}")

for banned in ("R29Effect.", "R23GameDrawSerial"):
    if banned in r32:
        errors.append(
            f"R32 retained direct R29 effect telemetry dependency: {banned}")

for marker in (
    "struct R29EffectTelemetrySnapshot",
    "TryGetEffectTelemetrySnapshot(",
):
    if marker not in r29:
        errors.append(f"R29 missing effect telemetry owner API: {marker}")

if "TryGetEffectTelemetrySnapshot(effect)" not in r32:
    errors.append("R32 workload telemetry missing R29 owner snapshot API")

if "R22ShadowState =" in r34:
    errors.append("R34 retained direct R22 raster-shadow mutation")

for banned in ("R22ReplayScope", "R22FailClosedReplayState"):
    if banned in r34:
        errors.append(
            f"R34 retained private R22 raster-replay dependency: {banned}")
if "class R22RasterReplayGuard" not in r22:
    errors.append("R22 missing public raster-replay owner guard")
if "R22RasterReplayGuard replay(" not in r34:
    errors.append("R34 missing R22 raster-replay owner guard")

for rel, source in (("R33", r33), ("R34", r34)):
    if "R29ArmMonoSafety(" in source:
        errors.append(
            f"{rel} retained private R29 mono-safety helper dependency")
    if "ArmStereoRecoverySafety(" not in source:
        errors.append(
            f"{rel} missing R29 owner stereo-recovery safety API")

for banned in ("R29ArmMonoSafety(", "R29MonoSafetyThroughEpoch"):
    if banned in r32:
        errors.append(
            f"R32 retained private R29 recovery-safety dependency: {banned}")
for marker in (
    "ArmStereoRecoverySafety(",
    "SetStereoRecoverySafetyThroughEpoch(",
):
    if marker not in r32:
        errors.append(
            f"R32 missing R29 recovery-safety owner API: {marker}")
if "SetStereoRecoverySafetyThroughEpoch(" not in r29:
    errors.append("R29 missing exact-epoch recovery-safety owner API")

for marker, source, owner in (
    ("R9InstallStatus()", r9, "R9"),
    ("R13InstallStatus()", r13, "R13"),
    ("R20InstallStatus()", r20, "R20"),
    ("R21InstallStatus()", r21, "R21"),
):
    if marker not in source:
        errors.append(f"{owner} missing install-state owner query API: {marker}")

for rel, source in (("R20", r20), ("R21", r21), ("R23", r23)):
    for banned in ("R9InstallState", "R9InstallReady", "R9InstallFailed",
                   "R13InstallState", "R13InstallReady", "R13InstallFailed"):
        if banned in source:
            errors.append(
                f"{rel} retained direct lower install-state dependency: {banned}")
for rel, source in (("R21", r21), ("R23", r23)):
    if "R20InstallState" in source:
        errors.append(f"{rel} retained direct R20 install-state dependency")
if "R21InstallState" in r23:
    errors.append("R23 retained direct R21 install-state dependency")
if "R22InstallState" in r23:
    errors.append("R23 retained direct R22 install-state dependency")

for marker in ("R9InstallStatus()", "R13InstallStatus()",
               "R20InstallStatus()", "R21InstallStatus()", "R22InstallStatus()"):
    if marker not in r23:
        errors.append(f"R23 missing prerequisite install owner query: {marker}")

for banned in ("R13InstallState", "R13InstallReady", "R13InstallFailed"):
    if banned in r32:
        errors.append(
            f"R32 retained direct R13 install-state dependency: {banned}")
if "R13InstallStatus()" not in r13:
    errors.append("R13 missing install-state owner query API")
if "R13InstallStatus()" not in r32:
    errors.append("R32 missing R13 install-state owner query")

for banned in ("R22InstallState", "R31InstallState"):
    if banned in r32:
        errors.append(
            f"R32 retained direct lower-layer install-state dependency: {banned}")
for marker, source, owner in (
    ("R22InstallStatus()", r22, "R22"),
    ("R31InstallStatus()", r31, "R31"),
):
    if marker not in source:
        errors.append(f"{owner} missing install-state owner query API: {marker}")
for marker in ("R22InstallStatus()", "R31InstallStatus()"):
    if marker not in r32:
        errors.append(f"R32 missing lower-layer install-state owner query: {marker}")

if "R32InstallState" in r33:
    errors.append("R33 retained direct R32 install-state dependency")
if "R33InstallState" in r34:
    errors.append("R34 retained direct R33 install-state dependency")
for marker, source, owner in (
    ("R32InstallStatus()", r32, "R32"),
    ("R33InstallStatus()", r33, "R33"),
):
    if marker not in source:
        errors.append(f"{owner} missing install-state owner query API: {marker}")
if "R32InstallStatus()" not in r33:
    errors.append("R33 missing R32 install-state owner query")
if "R33InstallStatus()" not in r34:
    errors.append("R34 missing R33 install-state owner query")

for banned in ("R22FailClosedEligibility();", "R22ResetBaselineTracking();"):
    if banned in r34:
        errors.append(f"R34 retained direct R22 reset fail-close primitive: {banned}")
if "FailClosedResetBaselineState();" not in r34:
    errors.append("R34 missing consolidated R22 reset fail-close owner API")

for banned in (
    "R33InvalidateDepthStencilCache();",
    "RightDepthSynchronized = false;",
    "RightStencilSynchronized = false;",
):
    if banned in r34:
        errors.append(
            f"R34 retained direct R33 depth/stencil fail-close state: {banned}")
if "FailClosedDepthStencilState();" not in r34:
    errors.append("R34 missing consolidated R33 depth/stencil owner API")

fail_closed_depth = re.search(
    r"inline void FailClosedDepthStencilState\(\) noexcept\s*\{(?P<body>.*?)\n    \}",
    r33,
    re.DOTALL,
)
if not fail_closed_depth:
    errors.append("R33 consolidated depth/stencil fail-close owner API missing")
else:
    depth_body = fail_closed_depth.group("body")
    depth_order = [
        depth_body.find("R33InvalidateDepthStencilCache();"),
        depth_body.find("RightDepthSynchronized = false;"),
        depth_body.find("RightStencilSynchronized = false;"),
    ]
    if min(depth_order) < 0 or depth_order != sorted(depth_order):
        errors.append(
            "R33 depth/stencil fail-close API must preserve cache/depth/stencil order")

fail_closed_reset = re.search(
    r"inline void FailClosedResetBaselineState\(\) noexcept\s*\{(?P<body>.*?)\n    \}",
    r22,
    re.DOTALL,
)
if not fail_closed_reset:
    errors.append("R22 consolidated reset fail-close owner API missing")
else:
    fail_closed_body = fail_closed_reset.group("body")
    fail_closed_order = [
        fail_closed_body.find("R22FailClosedEligibility();"),
        fail_closed_body.find("R22ResetBaselineTracking();"),
        fail_closed_body.find("InvalidateTrackedRasterShadow();"),
    ]
    if min(fail_closed_order) < 0 or fail_closed_order != sorted(fail_closed_order):
        errors.append(
            "R22 reset fail-close owner API must preserve eligibility/baseline/raster order")

for rel, source in (("R33", r33), ("R34", r34)):
    if "R31FlushPendingStateBlockResync" in source:
        errors.append(
            f"{rel} regained R31 StateBlock resync execution dependency")
    if "StateBlockRecovery::FlushPendingResync(device)" not in source:
        errors.append(
            f"{rel} missing neutral StateBlock recovery boundary")

if "StateBlockRecovery::Configure(" not in r31:
    errors.append("R31 missing neutral StateBlock recovery callback registration")
if "StateBlockEvents::Configure(" not in r31:
    errors.append("R31 missing neutral StateBlock event callback registration")
coverage_reset = r31.find("StateBlockTracker::ResetCoverageLoss()")
event_configure = r31.find("StateBlockEvents::Configure(")
if min(coverage_reset, event_configure) < 0 or not coverage_reset < event_configure:
    errors.append(
        "R31 must reset stale coverage before publishing StateBlock event callbacks")
for marker in (
    "StateBlockEvents::NotifyBegin(device)",
    "StateBlockEvents::NotifyEnd(device, hr)",
    "StateBlockEvents::NotifyApply(device, hr)",
):
    if marker not in r22:
        errors.append(f"R22 StateBlock owner missing neutral event dispatch: {marker}")
    if marker not in r31:
        errors.append(f"R31 fallback StateBlock hook missing neutral event dispatch: {marker}")

if "StateBlockTracker::LifecycleHooksReady()" not in r31:
    errors.append("R31 missing conditional R22 StateBlock ownership gate")
if "R22 lifecycle hooks are authoritative" not in r31:
    errors.append("R31 missing authoritative R22 lifecycle-owner path")
if "R31 fallback StateBlock hooks armed" not in r31:
    errors.append("R31 missing fallback physical StateBlock hook path")
if "StateBlockTracker::SetEventConsumerReady(" not in r31 or \
        "StateBlockEvents::Configured()" not in r31:
    errors.append("R31 missing neutral event-consumer readiness publication")
install_start = r31.find("DWORD WINAPI R31InstallThread(")
install_end = r31.find("class VRStereoR31PerfHook", install_start)
if install_start < 0 or install_end <= install_start:
    errors.append("R31 install transaction body missing")
else:
    install_body = r31[install_start:install_end]
    recovery_configure_pos = install_body.find("StateBlockRecovery::Configure(")
    configure_pos = install_body.find("StateBlockEvents::Configure(")
    enable_draw_pos = install_body.find("if (!R31EnableDrawHooks())")
    lifecycle_owner_pos = install_body.find("StateBlockTracker::LifecycleHooksReady()")
    fallback_end_pos = install_body.find("fallbackEndArmed = R31EndStateBlockHook.enable().has_value()")
    fallback_begin_pos = install_body.find("fallbackBeginArmed = R31BeginStateBlockHook.enable().has_value()")
    fallback_create_pos = install_body.find("fallbackCreateArmed = R31CreateStateBlockHook.enable().has_value()")
    consumer_ready_pos = install_body.find("StateBlockTracker::SetEventConsumerReady(true)")
    ready_pos = install_body.find("R31InstallState.store(State::Ready", consumer_ready_pos)
    if min(recovery_configure_pos, configure_pos, enable_draw_pos,
            lifecycle_owner_pos, fallback_end_pos, fallback_begin_pos,
            fallback_create_pos, consumer_ready_pos, ready_pos) < 0 or not (
            recovery_configure_pos < configure_pos < enable_draw_pos <
            lifecycle_owner_pos < fallback_end_pos < fallback_begin_pos <
            fallback_create_pos < consumer_ready_pos < ready_pos):
        errors.append(
            "R31 must establish physical StateBlock ownership before publishing readiness")

    if "R31EndStateBlockHook.enable().has_value() &&" in install_body or \
            "R31BeginStateBlockHook.enable().has_value() &&" in install_body:
        errors.append("R31 fallback hooks regained short-circuit partial-install enable")

    fail_start = install_body.find("const auto failInstall =")
    fail_end = install_body.find(
        "                    };\n\n                    OutRunVR::State::StateBlockTracker::SetEventConsumerReady(false)",
        fail_start)
    if fail_start < 0 or fail_end <= fail_start:
        errors.append("R31 install rollback boundary missing")
    else:
        fail_body = install_body[fail_start:fail_end]
        order = [
            fail_body.find("StateBlockTracker::SetEventConsumerReady(false)"),
            fail_body.find("R31CreateStateBlockHook = {}"),
            fail_body.find("R31BeginStateBlockHook = {}"),
            fail_body.find("R31EndStateBlockHook = {}"),
            fail_body.find("StateBlockEvents::Clear()"),
            fail_body.find("StateBlockRecovery::Clear()"),
            fail_body.find("StateBlockTracker::MarkCoverageLost()"),
            fail_body.find("R31InstallState.store(State::Failed"),
        ]
        if min(order) < 0 or order != sorted(order):
            errors.append(
                "R31 rollback must withdraw readiness, fallback hooks in reverse "
                "order, event/recovery callbacks, then fail closed")
if "StateBlockEvents::Clear()" not in r31:
    errors.append("R31 draw-hook failure path missing StateBlock event rollback")

dirty_match = re.search(
    r"void R31MarkStateBlockCachesDirty\(\) noexcept\s*\{(?P<body>.*?)\n        \}",
    r31,
    re.DOTALL,
)
if not dirty_match:
    errors.append("R31 StateBlock cache-dirty boundary missing")
elif "StateBlockRecovery::Configure(" in dirty_match.group("body"):
    errors.append(
        "R31 StateBlock recovery callbacks must be configured once at install, "
        "not rewritten on every lifecycle event")
if "SetR31Reliable" in state_block_tracker or "R31Reliable" in state_block_tracker:
    errors.append("StateBlockTracker retained obsolete R31 reliability naming")
if "SetR31Reliable" in r31 or "R31Reliable" in r31:
    errors.append("R31 retained obsolete overloaded StateBlock reliability producer")

r22_apply_owner = re.search(
    r"bool R22EnsureStateBlockApplyHook\(.*?\n        \}",
    r22,
    re.DOTALL,
)
if not r22_apply_owner:
    errors.append("R22 shared StateBlock Apply hook owner body missing")
elif "StateBlockTracker::MarkCoverageLost()" not in r22_apply_owner.group(0):
    errors.append(
        "R22 shared StateBlock Apply owner must preserve coverage-loss semantics")

if "R31FlushPendingStateBlockResync" in r31:
    errors.append("R31 retained obsolete StateBlock resync execution wrapper")

for rel, source in (("R31", r31), ("R32", r32), ("R33", r33), ("R34", r34)):
    if "R31StateBlockRecording" in source:
        errors.append(
            f"{rel} regained R31 StateBlock recording-state dependency")

for banned in ("IsGameStateBlockRecording", "IsStateBlockTrackingReliable"):
    if banned in r31:
        errors.append(f"R31 retained obsolete StateBlock status export: {banned}")
    if banned in renderer_r29:
        errors.append(f"renderer R29 retained stereo StateBlock status dependency: {banned}")

for marker in ("StateBlockTracker::Recording()", "StateBlockTracker::Reliable()"):
    if marker not in renderer_r29:
        errors.append(f"renderer R29 missing neutral StateBlock status access: {marker}")

misplaced_tracker = ROOT / "src/vr/d3d9/state/state_block_tracker.hpp"
if misplaced_tracker.exists():
    errors.append(
        "misplaced legacy StateBlockTracker copy still exists under src/vr/d3d9/state")

for p in (ROOT / "src/vr/d3d9").glob("stereo_renderer_r*.cpp"):
    m = re.fullmatch(r"stereo_renderer_r(\d+)\.cpp", p.name)
    if m and int(m.group(1)) > 34:
        errors.append(f"new legacy R overlay forbidden during flattening: {p.name}")

if errors:
    print("VR refactor contract FAILED", file=sys.stderr)
    for error in errors:
        print(f" - {error}", file=sys.stderr)
    raise SystemExit(1)

print("VR refactor contract PASS")
