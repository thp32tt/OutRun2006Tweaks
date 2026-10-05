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
r30 = text("src/vr/d3d9/stereo_renderer_r30.cpp")
r30_safe = text("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
r26 = text("src/vr/d3d9/stereo_renderer_r26.cpp")
r31 = text("src/vr/d3d9/stereo_renderer_r31.cpp")
r32 = text("src/vr/d3d9/stereo_renderer_r32.cpp")
r33 = text("src/vr/d3d9/stereo_renderer_r33.cpp")
r34_path = ROOT / "src/vr/d3d9/stereo_renderer_r34.cpp"
if r34_path.exists():
    errors.append("retired R34 source shim reappeared")
cmake = text("CMakeLists.txt")
cmake_toml = text("cmake.toml")
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
    ("R30", r30), ("R30_SAFE", r30_safe),
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

for rel, source in (("R30", r30), ("R30_SAFE", r30_safe)):
    if "R9NoteMainDepthContentWrite()" not in source:
        errors.append(f"{rel} missing R9 main-depth write owner API")

for rel, source in (("R20", r20), ("R23", r23), ("R33", r33)):
    if re.search(r"\\bR9MainDepthGeneration\\b", source):
        errors.append(
            f"{rel} retained direct R9 main-depth generation dependency")
    if "R9MainDepthGenerationValue()" not in source:
        errors.append(
            f"{rel} missing R9 main-depth generation owner query")
if "R9MainDepthGenerationValue()" not in r9:
    errors.append("R9 missing main-depth generation owner query API")

# Post-1000 dispatcher flattening: R31/R33 may call the R30 lower-draw
# boundary, but they must not reach into R30's private SafetyHookInline storage.
for rel, source in (("R31", r31), ("R33", r33)):
    for banned in (
        "R30DrawPrimitiveR29Hook",
        "R30DrawIndexedPrimitiveR29Hook",
        "R30DrawPrimitiveUPR29Hook",
        "R30DrawIndexedPrimitiveUPR29Hook",
    ):
        if banned in source:
            errors.append(
                f"{rel} retained direct R30 lower-hook storage dependency: {banned}")
for marker in (
    "R30CallLowerDrawPrimitive(",
    "R30CallLowerDrawIndexedPrimitive(",
    "R30CallLowerDrawPrimitiveUP(",
    "R30CallLowerDrawIndexedPrimitiveUP(",
):
    if marker not in r30:
        errors.append(f"R30 missing lower-draw owner boundary: {marker}")
    if marker not in r31 or marker not in r33:
        errors.append(f"R31/R33 missing R30 lower-draw owner boundary use: {marker}")

# R31 prerequisite polling must observe R30 through an owner status query.
if re.search(r"\\bR30InstallState\\b", r31):
    errors.append("R31 retained direct R30 install-state dependency")
if "R30InstallStatus()" not in r30:
    errors.append("R30 missing install-state owner query")
if "R30InstallStatus()" not in r31:
    errors.append("R31 missing R30 install-state owner query")

# R32 fail-closed gating may ask whether the R9 stereo baseline is seeded, but
# the seed flag itself remains R9-owned.
if re.search(r"\\bR9StereoSeeded\\b", r32):
    errors.append("R32 retained direct R9 stereo-seed dependency")
if "R9StereoBaselineSeeded()" not in r9:
    errors.append("R9 missing stereo-seed owner query")
if "R9StereoBaselineSeeded()" not in r32:
    errors.append("R32 missing R9 stereo-seed owner query")

# Post-1000 R33 owner-boundary continuation: the final dispatcher may ask R9
# whether the currently tracked main depth carries stencil, but must not read
# R9's private identity/descriptor/known-state tuple directly.
if "inline bool R9TrackedMainDepthHasStencil() noexcept" not in r9:
    errors.append("R9 missing tracked-main-depth stencil owner query API")
if "R9TrackedMainDepthHasStencil()" not in r33:
    errors.append("R33 missing R9 tracked-main-depth stencil owner query")
for banned in ("R9MainDepthKnown", "R9MainDepthIdentity", "R9MainDepthDesc"):
    if banned in r33:
        errors.append(
            f"R33 retained direct R9 main-depth metadata dependency: {banned}")

# Post-1000 successor: R33 must not directly mutate R9-owned right-depth/
# stencil synchronization flags. Preserve exact invalidation semantics through
# one lower-owner API so later final-dispatch cleanup cannot split ownership.
r9_depth_sync_owner = re.search(
    r"inline void R9InvalidateRightDepthStencilSync\(\s*"
    r"bool invalidateDepth, bool invalidateStencil\) noexcept\s*"
    r"\{(?P<body>.*?)\n\t\}",
    r9,
    re.DOTALL,
)
if not r9_depth_sync_owner:
    errors.append("R9 missing right depth/stencil sync invalidation owner API")
else:
    sync_body = r9_depth_sync_owner.group("body")
    sync_order = [
        sync_body.find("if (invalidateDepth)"),
        sync_body.find("RightDepthSynchronized = false;"),
        sync_body.find("if (invalidateStencil)"),
        sync_body.find("RightStencilSynchronized = false;"),
    ]
    if min(sync_order) < 0 or sync_order != sorted(sync_order):
        errors.append(
            "R9 right-depth sync owner API must preserve depth/stencil invalidation order")
for banned in ("RightDepthSynchronized = false;",
               "RightStencilSynchronized = false;"):
    if banned in r33:
        errors.append(
            f"R33 retained direct R9 right-depth sync mutation: {banned}")
if r33.count("R9InvalidateRightDepthStencilSync(") < 2:
    errors.append(
        "R33 missing R9 right-depth sync owner API at left-write and fail-close boundaries")

# Post-1000 successor: R33 may consult right depth/stencil synchronization
# readiness only through R9 owner queries. Direct reads split ownership just as
# direct writes do and make later final-dispatch flattening harder to reason about.
for marker in (
    "inline bool R9IsRightDepthInSync() noexcept",
    "inline bool R9IsRightStencilInSync() noexcept",
):
    if marker not in r9:
        errors.append(f"R9 missing right depth/stencil sync owner query: {marker}")
for raw in ("RightDepthSynchronized", "RightStencilSynchronized"):
    if re.search(rf"\b{raw}\b", r33):
        errors.append(f"R33 retained direct R9 right-depth sync read: {raw}")
if r33.count("R9IsRightDepthInSync()") < 4:
    errors.append("R33 missing R9 depth-sync owner query at both world/HUD readiness gates")
if r33.count("R9IsRightStencilInSync()") < 4:
    errors.append("R33 missing R9 stencil-sync owner query at both world/HUD readiness gates")
if "return RightDepthSynchronized;" not in r9:
    errors.append("R9 depth-sync owner query no longer preserves tracked-state read")
if "return RightStencilSynchronized;" not in r9:
    errors.append("R9 stencil-sync owner query no longer preserves tracked-state read")

if "R9DrawCalls" in r20:
    errors.append("R20 retained direct R9 draw-count dependency")
if "R9DrawCallCount()" not in r20:
    errors.append("R20 missing R9 draw-count owner query")
if "R9DrawCallCount()" not in r9:
    errors.append("R9 missing draw-count owner query API")

for rel, source in (("R30", r30), ("R30_SAFE", r30_safe)):
    if "--R9DrawCalls;" in source:
        errors.append(f"{rel} retained direct R9 draw-count rollback")
    if "R9UndoStereoDrawCount();" not in source:
        errors.append(f"{rel} missing R9 draw-count rollback owner API")
if "R9UndoStereoDrawCount()" not in r9:
    errors.append("R9 missing draw-count rollback owner API")

for rel, source in (("R29", r29), ("R31", r31), ("R32", r32), ("R33", r33)):
    if "R9NoteMainDepthContentWrite()" not in source:
        errors.append(f"{rel} missing R9 main-depth write owner API")

for banned in ("R23GameDrawSerial", "R23BeforeTopLevelDraw", "GetTopLevelDrawSerial()"):
    if banned in r26:
        errors.append(f"R26 regained R23 implementation dependency: {banned}")

if "R23GameDrawSerial" in r30_safe:
    errors.append("active R30-safe HUD path retained direct R23 draw-serial state")
if "TopLevelDrawSerial() + 1u" not in r30_safe:
    errors.append("active R30-safe HUD path missing R23 draw-serial owner query")

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

# Cycle 911-1000 owner-boundary convergence.
# Upper layers may update lower-layer telemetry only through owner APIs.
for rel, source in (("R31", r31), ("R32", r32), ("R33", r33)):
    if "++R29StableTwoEyeDraws;" in source:
        errors.append(
            f"{rel} retained direct R29 stable-two-eye telemetry mutation")
    if "++R30ScreenSpaceFovDraws;" in source:
        errors.append(
            f"{rel} retained direct R30 screen-space telemetry mutation")

if "R29TelemetryNoteStableTwoEyeDraw()" not in r29:
    errors.append("R29 missing stable-two-eye telemetry owner API")
if "R30TelemetryNoteScreenSpaceFovDraw()" not in r30:
    errors.append("R30 missing screen-space telemetry owner API")

# A duplicated stereo draw without a complete independent mono replay has one
# R9-owned accounting transition: increment draw calls + mark the mono backup
# incomplete. Upper layers must not reproduce that state pair themselves.
for rel, source in (
    ("R29", r29), ("R30", r30), ("R30_SAFE", r30_safe),
    ("R31", r31), ("R32", r32), ("R33", r33),
):
    for banned in ("++R9DrawCalls;", "R9MonoBackupGap = true;"):
        if banned in source:
            errors.append(
                f"{rel} retained direct R9 stereo-draw accounting mutation: {banned}")
    if "R9NoteStereoDrawWithoutMonoBackup();" not in source:
        errors.append(
            f"{rel} missing R9 stereo-draw accounting owner API use")
if "R9NoteStereoDrawWithoutMonoBackup()" not in r9:
    errors.append("R9 missing stereo-draw accounting owner API")

# R32 may consume R13 DirectGPU contracts, but readiness, ACK mapping and R13's
# safety telemetry remain R13-owned state.
for banned in (
    "R13OverlayReady.load(",
    "R13ReadGpuCompletedFrame(",
    "++R13SafeAckBackpressure;",
):
    if banned in r32:
        errors.append(
            f"R32 retained direct R13 DirectGPU owner-state dependency: {banned}")
for marker in (
    "R13OverlayReadyForTransport()",
    "R13TryGetGpuCompletedFrame(",
    "R13NoteSafeAckBackpressure()",
):
    if marker not in r13:
        errors.append(f"R13 missing DirectGPU owner API: {marker}")
    if marker not in r32:
        errors.append(f"R32 missing R13 DirectGPU owner API use: {marker}")

for rel, source in (("R32", r32), ("R33", r33)):
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
    if banned in r33:
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

if "R22ShadowState =" in r33:
    errors.append("R33 final dispatcher retained direct R22 raster-shadow mutation")

for banned in ("R22ReplayScope", "R22FailClosedReplayState"):
    if banned in r33:
        errors.append(
            f"R33 final dispatcher retained private R22 raster-replay dependency: {banned}")
if "class R22RasterReplayGuard" not in r22:
    errors.append("R22 missing public raster-replay owner guard")
if "R22RasterReplayGuard replay(" not in r33:
    errors.append("R33 final dispatcher missing R22 raster-replay owner guard")

if "R29ArmMonoSafety(" in r33:
    errors.append("R33 retained private R29 mono-safety helper dependency")
if "ArmStereoRecoverySafety(" not in r33:
    errors.append("R33 missing R29 owner stereo-recovery safety API")
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
for marker, source, owner in (
    ("R32InstallStatus()", r32, "R32"),
):
    if marker not in source:
        errors.append(f"{owner} missing install-state owner query API: {marker}")
if "R32InstallStatus()" not in r33:
    errors.append("R33 missing R32 install-state owner query")
if "R33InstallStatus()" in r33:
    errors.append("R33 retained obsolete compatibility-only install-status observer API")
if "R33InstallState" in r33:
    errors.append("R33 retained write-only final install state after observer retirement")

# Post-1000 hook-chain flattening: all former R34 runtime responsibilities are
# owned by R33. The source shim and historical R34 compatibility Hook/status
# alias are both retired and must stay absent.
for marker in (
    "R33GuardStereoRasterState(",
    "R33SynchronizeResetReplayGuardState(",
    "R33ReportInstallResult(",
    "R33ResetReplayBlocked",
    "LastResetStateReplaySucceeded()",
    "TestCooperativeLevel()",
    "R30TryXyzrhwPrimitiveVB(",
    "R30TryXyzrhwIndexedPrimitiveVB(",
    "R30TryXyzrhwPrimitiveUP(",
    "R30TryXyzrhwIndexedPrimitiveUP(",
):
    if marker not in r33:
        errors.append(f"R33 missing folded final-dispatch responsibility: {marker}")

for banned in (
    "class VRStereoR34ResetGuardHook",
    "OpenXRVRStereoR34ResetGuard",
    "R33InstallStatus()",
):
    if banned in r33:
        errors.append(
            f"R33 retained retired R34 compatibility observer/status alias: {banned}")

# Post-1000 successor: after the R34 shim retirement, the normal full-chain
# build must compile R33 directly. Comparison modes may disable R33 in favor of
# their isolated owner, but R34 must never become a compiled stereo owner again.
post_review = re.search(
    r"set\(OUTRUN_VR_POST_REVIEW_FINAL_TUS(?P<body>.*?)\)",
    cmake,
    re.DOTALL,
)
if not post_review:
    errors.append("CMake post-review final-TU list missing")
else:
    body = post_review.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("CMake full-chain final TU must terminate directly at R33")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("CMake retained R34 shim as post-review compiled final TU")

if "src/vr/d3d9/stereo_renderer_r34.cpp" in cmake:
    errors.append("CMake retained retired R34 source shim")

owners = re.search(
    r"set\(_vr_stereo_owner_candidates(?P<body>.*?)\)",
    cmake,
    re.DOTALL,
)
if not owners:
    errors.append("CMake stereo-owner candidate list missing")
else:
    body = owners.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("CMake stereo-owner candidates missing R33 final dispatcher")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("CMake stereo-owner candidates still include R34 shim")

for option in (
    "OUTRUN_VR_SAFE_DRAW_COMPARE",
    "OUTRUN_VR_R26_HUD_COMPARE",
    "OUTRUN_VR_C1_COMPARE OR OUTRUN_VR_C2_COMPARE",
):
    start = cmake.find(f"if({option})")
    end = cmake.find("endif()", start)
    if start < 0 or end <= start:
        errors.append(f"CMake comparison block missing: {option}")
        continue
    block = cmake[start:end]
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in block:
        errors.append(f"CMake comparison block must disable R33 final owner: {option}")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in block:
        errors.append(f"CMake comparison block still toggles obsolete R34 shim owner: {option}")

# CMakeLists.txt is generated from cmake.toml. Guard the generator source too
# so cmkr cannot silently restore R34 as the compiled stereo owner.
generator_post_review = re.search(
    r"set\(OUTRUN_VR_POST_REVIEW_FINAL_TUS(?P<body>.*?)\)",
    cmake_toml, re.DOTALL)
if not generator_post_review:
    errors.append("cmake.toml post-review final-TU list missing")
else:
    body = generator_post_review.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("cmake.toml full-chain final TU must terminate directly at R33")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("cmake.toml retained R34 shim as post-review compiled final TU")
if "src/vr/d3d9/stereo_renderer_r34.cpp" in cmake_toml:
    errors.append("cmake.toml retained retired R34 source shim")
generator_owners = re.search(
    r"set\(_vr_stereo_owner_candidates(?P<body>.*?)\)", cmake_toml, re.DOTALL)
if not generator_owners:
    errors.append("cmake.toml stereo-owner candidate list missing")
else:
    body = generator_owners.group("body")
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in body:
        errors.append("cmake.toml stereo-owner candidates missing R33 final dispatcher")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in body:
        errors.append("cmake.toml stereo-owner candidates still include R34 shim")
for option in ("OUTRUN_VR_SAFE_DRAW_COMPARE", "OUTRUN_VR_R26_HUD_COMPARE",
               "OUTRUN_VR_C1_COMPARE OR OUTRUN_VR_C2_COMPARE"):
    start = cmake_toml.find(f"if({option})")
    end = cmake_toml.find("endif()", start)
    if start < 0 or end <= start:
        errors.append(f"cmake.toml comparison block missing: {option}")
        continue
    owner_block = cmake_toml[start:end]
    if "src/vr/d3d9/stereo_renderer_r33.cpp" not in owner_block:
        errors.append(f"cmake.toml comparison block must disable R33 final owner: {option}")
    if "src/vr/d3d9/stereo_renderer_r34.cpp" in owner_block:
        errors.append(f"cmake.toml comparison block still toggles obsolete R34 shim owner: {option}")

for banned in ("R22FailClosedEligibility();", "R22ResetBaselineTracking();"):
    if banned in r33:
        errors.append(f"R33 retained direct R22 reset fail-close primitive: {banned}")
if "FailClosedResetBaselineState();" not in r33:
    errors.append("R33 missing consolidated R22 reset fail-close owner API")

if "FailClosedDepthStencilState();" not in r33:
    errors.append("R33 final dispatcher missing consolidated depth/stencil owner API")

install_start = r33.find("DWORD WINAPI R33InstallThread(")
install_end = r33.find("class VRStereoR33DispatchHook", install_start)
if install_start < 0 or install_end <= install_start:
    errors.append("R33 install transaction body missing")
else:
    install_body = r33[install_start:install_end]
    sync_pos = install_body.find(
        "R33SynchronizeResetReplayGuardState(installedDevice)")
    publish_pos = install_body.find(
        "R33ReportInstallResult(true)", sync_pos)
    if min(sync_pos, publish_pos) < 0 or not (sync_pos < publish_pos):
        errors.append(
            "R33 must synchronize replay-health before terminal publication")


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
        depth_body.find("R9InvalidateRightDepthStencilSync(true, true);"),
    ]
    if min(depth_order) < 0 or depth_order != sorted(depth_order):
        errors.append(
            "R33 depth/stencil fail-close API must preserve cache then R9 sync invalidation order")

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

if "R31FlushPendingStateBlockResync" in r33:
    errors.append("R33 regained R31 StateBlock resync execution dependency")
if "StateBlockRecovery::FlushPendingResync(device)" not in r33:
    errors.append("R33 missing neutral StateBlock recovery boundary")
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

for rel, source in (("R31", r31), ("R32", r32), ("R33", r33)):
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
