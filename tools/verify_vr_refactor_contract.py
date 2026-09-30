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
r33 = text("src/vr/d3d9/stereo_renderer_r33.cpp")
r34 = text("src/vr/d3d9/stereo_renderer_r34.cpp")
draw_class = text("src/vr/render/draw_class.hpp")
raster = text("src/vr/state/d3d9_raster_state.hpp")
text("tools/verify_vr_hook_graph.py")

for banned in ("R22ShadowState", "R22StateBlockTrackingReliable"):
    if banned in r23:
        errors.append(f"R23 regained direct lower-layer state dependency: {banned}")

for banned in ("R23GameDrawSerial", "R23BeforeTopLevelDraw", "GetTopLevelDrawSerial()"):
    if banned in r26:
        errors.append(f"R26 regained R23 implementation dependency: {banned}")

for banned in (
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
    "R31Frame",
    "R31BuildFastWorldConstants",
    "R31DiscardUnreliableDrawCaches",
    "R31LiveShaderMatches",
    "R31ObserveDraw",
    "R31StateBlockRecording",
    "R31StateBlockTrackingReliable",
    "R31FlushPendingStateBlockResync",
    "R32EffectIsFragileLive",
    "R32GetSavedViewport",
    "R32SetWvpBatch",
    "R32RestoreRightPassState",
    "R32LowerFailClosed",
    "R32InstallState",
):
    if banned in r33:
        errors.append(f"R33 regained revision-layer dependency: {banned}")

for banned in (
    "R33InstallState",
    "R22ShadowState",
    "R22FailClosedEligibility",
    "R22ResetBaselineTracking",
    "R22ReplayScope",
    "R22FailClosedReplayState",
    "R31StateBlockRecording",
    "R31FlushPendingStateBlockResync",
    "R30TryXyzrhw",
    "OutRunVR::GameSemantic::ConsumeForDraw",
    "OutRunVR::GameSemantic::CurrentScope",
):
    if banned in r34:
        errors.append(f"R34 regained direct lower-layer dependency: {banned}")

draw_begin = r34.find("HRESULT __stdcall DrawPrimitiveDestR34")
draw_end = r34.find("HRESULT __stdcall ResetDestR34")
if draw_begin >= 0 and draw_end > draw_begin:
    draw_bodies = r34[draw_begin:draw_end]
    for banned in (
        "R34DrawPrimitiveR33Hook",
        "R34DrawIndexedPrimitiveR33Hook",
        "R34DrawPrimitiveUPR33Hook",
        "R34DrawIndexedPrimitiveUPR33Hook",
    ):
        if banned in draw_bodies:
            errors.append(f"R34 draw body bypassed trampoline facade: {banned}")

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

for rel in (
    "src/vr/core/dispatch_result.hpp",
    "src/vr/core/raster_guard_policy.hpp",
    "src/vr/render/eye_tail_cache.hpp",
    "src/vr/render/screen_space_kind.hpp",
    "src/vr/render/draw_semantic_scope.hpp",
    "src/vr/state/depth_stencil_write_state.hpp",
    "src/vr/lifecycle/reset_replay_state.hpp",
    "src/vr/telemetry/performance_counters.hpp",
    "src/vr/telemetry/depth_stencil_metrics.hpp",
    "src/vr/telemetry/raster_guard_metrics.hpp",
):
    text(rel)

for rel in (
    "src/vr/d3d9/stereo_renderer_r31.cpp",
    "src/vr/d3d9/stereo_renderer_r33.cpp",
    "src/vr/d3d9/stereo_renderer_r34.cpp",
):
    source = text(rel)
    if re.search(r"\(\)s\b", source):
        errors.append(f"{rel}: malformed accessor substitution token '()s'")

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
