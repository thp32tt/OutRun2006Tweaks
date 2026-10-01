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
text("tools/verify_vr_hook_graph.py")

for banned in ("R22ShadowState", "R22StateBlockTrackingReliable"):
    if banned in r23:
        errors.append(f"R23 regained direct lower-layer state dependency: {banned}")
if "R22StateBlockTrackingReliable" in r22:
    errors.append("R22 retained removed StateBlock reliability authority")

for banned in ("R23GameDrawSerial", "R23BeforeTopLevelDraw", "GetTopLevelDrawSerial()"):
    if banned in r26:
        errors.append(f"R26 regained R23 implementation dependency: {banned}")

required_r22 = (
    '#include "../state/d3d9_raster_state.hpp"',
    "using R22ScissorSnapshot = OutRunVR::State::D3D9RasterSnapshot;",
    "GetTrackedRasterShadow()",
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
    "SetR31Reliable(",
    "R31Reliable()",
    "Reliable()",
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
    "NotifyBegin(",
    "NotifyEnd(",
    "NotifyApply(",
):
    if marker not in state_block_events:
        errors.append(f"StateBlockEvents missing API marker: {marker}")

for marker in (
    "class StateBlockRecovery",
    "Configure(",
    "FlushPendingResync(",
    "StateBlockTracker::ConsumeResync()",
):
    if marker not in state_block_recovery:
        errors.append(f"StateBlockRecovery missing API marker: {marker}")

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
for marker in (
    "StateBlockEvents::NotifyBegin(device)",
    "StateBlockEvents::NotifyEnd(device, hr)",
    "StateBlockEvents::NotifyApply(device, hr)",
):
    if marker not in r31:
        errors.append(f"R31 physical StateBlock hook missing neutral event dispatch: {marker}")
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
