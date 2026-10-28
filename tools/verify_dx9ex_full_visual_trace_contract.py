#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

renderer = read("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
present = read("src/vr/d3d9/stereo_renderer.cpp")
graphics = read("src/hooks_graphics.cpp")
ui = read("src/hooks_uiscaling.cpp")
host_main = read("vrhost/src/main.cpp")
host_r23 = read("vrhost/src/main_r23.cpp")
dllmain = read("src/dllmain.cpp")
user_runner = read("tools/Run-DX9ExFocusTest.ps1")
official_runner = read("tools/Run-FocusOfficialTest.ps1")

required = {
    "lens source provenance": (graphics, [
        "VR TRACE LENS SOURCE FULL:",
        "sourceCallSerial={}",
        "sequence={}",
        "ordinal={}",
        "alpha={:.9g}",
    ]),
    "lens ownership/GPU": (renderer, [
        "VR TRACE LENS C64 PROOF FULL:",
        "VR TRACE LENS R30 ENTRY FULL:",
        "VR TRACE LENS LOWER FALLBACK FULL:",
        "VR TRACE LENS GPU STATE FULL:",
        "VR TRACE LENS MATRIX FULL:",
        "VR TRACE LENS DRAW CALL FULL:",
    ]),
    "full D3D9 pipeline": (renderer, [
        "VR TRACE STEREO POSE FULL:",
        "VR TRACE PIPELINE FULL:",
        "VR TRACE FIXEDFN MATRIX FULL:",
        "VR TRACE TARGET FULL:",
        "VR TRACE TEXTURE FULL:",
        "VR TRACE SHADER CONSTANTS FULL:",
        "D3DRS_ALPHAREF",
        "D3DRS_ALPHAFUNC",
        "D3DRS_BLENDOPALPHA",
        "D3DRS_SCISSORTESTENABLE",
        "D3DSAMP_SRGBTEXTURE",
        "D3DTSS_TEXTURETRANSFORMFLAGS",
        "GetDepthStencilSurface",
    ]),
    "time/goal source+queue": (ui, [
        "VR TRACE PLUS_TIME SOURCE ENTRY:",
        "VR TRACE PLUS_TIME QUEUE ENTRY FULL:",
        "VR TRACE PLUS_TIME QUEUE EXIT FULL:",
        "VR TRACE GOAL_PERCENT SOURCE ENTRY:",
        "VR TRACE GOAL_PERCENT QUEUE ENTRY FULL:",
        "VR TRACE GOAL_PERCENT QUEUE EXIT FULL:",
        "VR TRACE GOAL TEXT FULL:",
        "VR TRACE HUD NODE FULL:",
        "VR TRACE HUD NODE0 FULL:",
        "VR TRACE HUD NODE1 FULL:",
        "VR TRACE D3DX DRAW FULL:",
    ]),
    "time/goal physical eyes": (renderer, [
        "VR TRACE RESULT R62 ENTRY FULL:",
        "VR TRACE RESULT R62 REJECT FULL:",
        "VR TRACE RESULT GPU STATE FULL:",
        "VR TRACE RESULT MATRIX FULL:",
        "VR TRACE RESULT AFFINE FULL:",
        "VR TRACE RESULT PHYSICAL EYES FULL:",
    ]),
    "game frame join": (present, [
        "VR TRACE FRAME PUBLISH FULL:",
        "pendingFrameId",
        "pendingPoseSequence",
        "presentStart.QuadPart",
    ]),
    "host projection": (host_main, [
        "VR TRACE HOST PROJECTION BLIT FULL",
        "outrun-vr-host-full-trace.log",
        "OutRunVrEmitFullTrace",
        "log.flush()",
    ]),
    "host actual XR submit": (host_r23, [
        "VR TRACE XR FRAME FULL",
        "VR TRACE XR EYE FULL",
        "cachedProjectionFrameId",
        "cachedProjectionPoseSequence",
        "submittedSourceFrameId",
        "submittedSourcePoseSequence",
        'frameCachedProjection ? "CACHED"',
        "viewStateFlags=0x",
        "headFlags=0x",
        "refSpacePending=",
        "fullTraceQpc.QuadPart",
    ]),
    "game log flush": (dllmain, [
        "spdlog::flush_on(spdlog::level::debug)",
    ]),
    "user collection": (user_runner, [
        "outrun-vr-host*.log",
        "FULL_TRACE_STATUS.txt",
        "FULL_TRACE_CONTRACT.txt",
    ]),
    "official collection": (official_runner, [
        "outrun-vr-host*.log",
        "FULL_TRACE_STATUS.txt",
        "outrun-vr-host-full-trace.log",
    ]),
}

for label, (body, needles) in required.items():
    for needle in needles:
        assert needle in body, f"{label}: missing {needle!r}"

# Critical correctness regression: cached projection must report the actually
# submitted cached XrCompositionLayerProjectionView, never unconditional pv[].
cached_select = """const auto* submitted =
                            frameCachedProjection
                                ? &cachedProjectionViews[eye]
                                : (frameFreshProjection ? &pv[eye] : nullptr);"""
assert cached_select in host_r23, "cached XR submission source selection regressed"
assert "cachedProjectionFrameId = matchedStereoFrameId;" in host_r23
assert "cachedProjectionPoseSequence =" in host_r23
assert "matchedStereoPoseSequence =" in host_r23

# Full tracing is intentionally performance-heavy and must remain opt-in under
# the already-enabled VR telemetry switch, not silently promoted to all users.
assert "if (!Settings::VRTelemetry || !device)" in renderer
assert "Telemetry = true" in read("OutRun2006Tweaks.ini")

print("PASS DX9Ex one-pass FULL visual trace contract: source -> queue -> D3DX -> D3D9 -> frame -> OpenXR -> collected ZIP")
print("RUNTIME_VALIDATION=UNTESTED")
