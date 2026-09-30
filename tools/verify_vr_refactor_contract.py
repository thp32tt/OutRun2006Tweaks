#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        errors.append(f"missing required file: {rel}")
        return ""
    return path.read_text(encoding="utf-8")

tracker = read("src/vr/state/state_block_tracker.hpp")
r22 = read("src/vr/d3d9/stereo_renderer_r22.cpp")
r31 = read("src/vr/d3d9/stereo_renderer_r31.cpp")
r32 = read("src/vr/d3d9/stereo_renderer_r32.cpp")
r33 = read("src/vr/d3d9/stereo_renderer_r33.cpp")
r34 = read("src/vr/d3d9/stereo_renderer_r34.cpp")

for marker in (
    "class StateBlockTracker final",
    "SetR22Reliable",
    "SetR31Reliable",
    "R22Reliable",
    "R31Reliable",
    "Reliable",
    "MarkCoverageLost",
    "ResetCoverageLoss",
    "CoverageLost",
    "RequireResync",
    "ConsumeResync",
    "BeginRecording",
    "EndRecording",
    "IsRecording",
    "NoteApply",
    "RecordingCount",
    "ApplyCount",
):
    if marker not in tracker:
        errors.append(f"StateBlockTracker API missing marker: {marker}")

for rel, source in (
    ("src/vr/d3d9/stereo_renderer_r22.cpp", r22),
    ("src/vr/d3d9/stereo_renderer_r31.cpp", r31),
    ("src/vr/d3d9/stereo_renderer_r33.cpp", r33),
):
    if "state_block_tracker.hpp" not in source:
        errors.append(f"{rel}: StateBlockTracker include missing")

for legacy in (
    "R22StateBlockTrackingReliable",
    "R31StateBlockTrackingReliable",
    "R31StateBlockCoverageLost",
    "R31StateBlockResyncPending",
    "R31StateBlockRecordings",
    "R31StateBlockApplies",
    "R31StateBlockRecording",
):
    for rel, source in (
        ("src/vr/d3d9/stereo_renderer_r22.cpp", r22),
        ("src/vr/d3d9/stereo_renderer_r31.cpp", r31),
        ("src/vr/d3d9/stereo_renderer_r32.cpp", r32),
        ("src/vr/d3d9/stereo_renderer_r33.cpp", r33),
    ):
        if legacy in source:
            errors.append(f"{rel}: legacy StateBlock authority reintroduced: {legacy}")

if "StateBlockTracker::Reliable()" not in r33:
    errors.append("R33: neutral aggregate StateBlock reliability query missing")

for required in (
    "src/vr/render/screen_space_kind.hpp",
    "src/vr/render/screen_space_api.hpp",
    "src/vr/render/stereo_base_policy.hpp",
    "src/vr/render/fast_path_support.hpp",
    "src/vr/render/lower_draw_api.hpp",
    "src/vr/render/xyzrhw_api.hpp",
    "src/vr/state/right_depth_stencil_sync.hpp",
    "src/vr/state/depth_target_state.hpp",
    "src/vr/lifecycle/frame_accounting.hpp",
):
    read(required)

for legacy in (
    "R9",
    "R13",
    "R20",
    "R21",
    "R22",
    "R23",
    "R26",
    "R29",
    "R30",
    "R31",
):
    import re
    if re.search(rf"\\b{legacy}[A-Za-z0-9_]+", r32):
        errors.append(f"R32 regained lower-layer implementation dependency: {legacy}*")

for legacy in (
    "R29StableStereoBase",
    "R29FragileEffectCached",
    "R29ArmMonoSafety",
    "R29StableTwoEyeDraws",
    "R30ScreenSpaceKind",
    "R30ClassifyScreenSpacePass",
    "R30BuildScreenSpaceEyeConstants",
    "R30ScreenSpaceFovDraws",
    "R30DrawPrimitiveR29Hook",
    "R30DrawIndexedPrimitiveR29Hook",
    "R30DrawPrimitiveUPR29Hook",
    "R30DrawIndexedPrimitiveUPR29Hook",
    "R31BuildFastWorldConstants",
    "R31DiscardUnreliableDrawCaches",
    "R31LiveShaderMatches",
    "R31ObserveDraw",
    "R31Frame",
    "R31FastWorldDraws",
    "R31HudDraws",
    "R31FlushPendingStateBlockResync",
    "R32EffectIsFragileLive",
    "R32GetSavedViewport",
    "R32SetWvpBatch",
    "R32RestoreRightPassState",
    "R32LowerFailClosed",
    "R32InstallState",
    "R9MainDepthIdentity",
    "R9MainDepthKnown",
    "R9MainDepthDesc",
    "R9MainDepthGeneration",
    "R9MainDepthContentSerial",
    "R9DrawCalls",
    "R9MonoBackupGap",
    "R9Poison",
):
    if legacy in r33:
        errors.append(f"R33 regained lower-layer implementation dependency: {legacy}")

for legacy in (
    "R22ReplayScope",
    "R30TryXyzrhwPrimitiveVB",
    "R30TryXyzrhwIndexedPrimitiveVB",
    "R30TryXyzrhwPrimitiveUP",
    "R30TryXyzrhwIndexedPrimitiveUP",
):
    if legacy in r34:
        errors.append(f"R34 regained lower-layer implementation dependency: {legacy}")

reset_begin = r34.find("HRESULT __stdcall ResetDestR34")
rollback_begin = r34.find("void R34RollbackHooks")
if reset_begin >= 0 and rollback_begin > reset_begin:
    callback_region = r34[reset_begin:rollback_begin]
    for legacy in ("R34ResetR33Hook.stdcall", "R34PresentR33Hook.stdcall"):
        if legacy in callback_region:
            errors.append(f"R34 callback bypassed lifecycle facade: {legacy}")

if errors:
    print("R84 refactor contract FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("R84 refactor contract OK")
