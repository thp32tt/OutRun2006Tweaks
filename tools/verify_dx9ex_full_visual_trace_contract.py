#!/usr/bin/env python3
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

renderer = read("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
present = read("src/vr/d3d9/stereo_renderer.cpp")
graphics = read("src/hooks_graphics.cpp")
ui = read("src/hooks_uiscaling.cpp")
reset_trace = read("src/vr/d3d9/reset_trace.hpp")
ex_upgrade = read("src/vr/d3d9/ex_device_upgrade.cpp")
host_main = read("vrhost/src/main.cpp")
host_r23 = read("vrhost/src/main_r23.cpp")
host_r24 = read("vrhost/src/runtime/r24_black_screen_guard.hpp")
host_r19 = read("vrhost/src/runtime/sbs_capture_override.hpp")
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
        "resetEpoch={}",
        "resetQpc={}",
        "resetFlags=0x{:X}",
        "resetSnapshotStable={}",
        "sourceEventQpc={} thread={} resetQpcRole=RESET_ENTRY",
    ]),
    "lens ownership/GPU": (renderer, [
        "VR TRACE LENS C64 PROOF FULL:",
        "VR TRACE LENS R30 ENTRY FULL:",
        "VR TRACE LENS LOWER FALLBACK FULL:",
        "VR TRACE VISUAL LOWER PHYSICAL RESULT FULL:",
        "VR TRACE XYZRHW VISUAL EYES FULL:",
        "VR TRACE R7 VISUAL EYES FULL:",
        "VR TRACE LENS GPU STATE FULL:",
        "VR TRACE LENS MATRIX FULL:",
        "VR TRACE LENS DRAW CALL FULL:",
        "VR LENS R30 PHYSICAL EYES:",
        "preViewport={},{},{}x{}",
        "resetSnapshotStable={}",
        "resetViewportExtentMatchesPre={}",
        "resetViewportRectMatchesPre={}",
        "resetScissorMatchesPre={}",
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
        "VR TRACE PLUS_TIME SOURCE EXIT:",
        "VR TRACE GOAL_TIME SOURCE:",
        "VR P0 GOAL B9200 ENTRY:",
        "VR HUD D3DX LIFECYCLE:",
        "phase={}",
        "invalidated={}",
        "entryDrawCount={}",
        "postDrawCount={}",
        "resetEpoch={}",
        "resetSnapshotStable={}",
    ]),
    "time/goal physical eyes": (renderer, [
        "VR TRACE RESULT R62 ENTRY FULL:",
        "VR TRACE RESULT R62 REJECT FULL:",
        "VR TRACE RESULT GPU STATE FULL:",
        "VR TRACE RESULT MATRIX FULL:",
        "VR TRACE RESULT AFFINE FULL:",
        "VR TRACE RESULT PHYSICAL EYES FULL:",
        "VR TRACE RESULT SCREENSPACE EYES FULL:",
        "VR TRACE XYZRHW VISUAL EYES FULL:",
        "VR TRACE VISUAL LOWER PHYSICAL RESULT FULL:",
        "VR TRACE R7 VISUAL EYES FULL:",
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
        "VR TRACE XR PIXEL GRID FULL",
        "R23ProjectionSamplesX = 17",
        "R23ProjectionSamplesY = 11",
        "R23PixelIntervalMs = 100",
        "projectionFrameId = sourceFrameId;",
        "projectionPoseSequence = sourcePoseSequence;",
        "rgbHashL=0x",
        "alphaHashL=0x",
        "pairAbsLinearMean=",
        "brightCentroidL=",
        "brightDisparity=",
        "brightMetricRole=GLOBAL_BRIGHT_NEGATIVE_CONTROL_NOT_FLARE_ROI",
        "rawGridRetainedForOfflineFlareRoi=1",
        "metricRole=SAME_INDEX_CONTROL_NOT_STEREO_CORRESPONDENCE",
        "coverage=UNIFORM_GRID_NOT_FLARE_CENSUS",
        "submissionSerialBefore=",
        "submissionSerialAfter=",
        "receiptAdvanced=",
        "r19ReceiptSerial=",
        "r19PoseSequence=",
    ]),
    "Reset epoch join": (reset_trace + ex_upgrade + renderer + graphics + ui, [
        "struct Snapshot",
        "trace.resetSerial =",
        "OutRunVR::D3D9ResetTrace::Publish(trace);",
        "VR D3D9Ex RESET TRACE: resetEpoch=",
        "contract=XR_RESET_EPOCH_V3",
        "OutRunVR::D3D9ResetTrace::Read()",
        "resetEpoch={}",
        "resetQpc={}",
        "resetFlags=0x{:X}",
        "resetSnapshotStable={}",
        "Writer.test_and_set(std::memory_order_acquire)",
        "PublishedResetSerial.store(",
    ]),
    "R19/R24 final receipt": (host_r19 + host_r24, [
        "LastEndFrameReceiptSerial",
        "LastEndFrameReceiptProjection",
        "LastEndFrameReceiptFrameId",
        "LastEndFrameReceiptPoseSequence",
        "LastEndFrameReceiptLayerCount",
        "RecordEndFrameReceipt(",
        "SubmitClassicFallbackWithReceipt(",
        "preservedHasLayer",
    ]),
    "game log flush": (dllmain, [
        "spdlog::flush_on(spdlog::level::debug)",
    ]),
    "user collection": (user_runner, [
        "outrun-vr-host*.log",
        "FULL_TRACE_STATUS.txt",
        "FULL_TRACE_CONTRACT.txt",
        "OUTRUN_VR_R23_PIXEL_PROBE = '1'",
    ]),
    "official collection": (official_runner, [
        "outrun-vr-host*.log",
        "FULL_TRACE_STATUS.txt",
        "outrun-vr-host-full-trace.log",
        "OUTRUN_VR_R23_PIXEL_PROBE = '1'",
    ]),
}

for label, (body, needles) in required.items():
    for needle in needles:
        assert needle in body, f"{label}: missing {needle!r}"

# Reset trace must publish one stable epoch and full raster rectangle proof.
# A same-size viewport is not evidence of the same X/Y origin, and a bounded
# read failure must remain distinguishable from "no Reset has happened".
assert "resetViewportMatchesPre" not in renderer
assert "NextResetSerial()" not in reset_trace
assert "NextResetSerial()" not in ex_upgrade
assert ex_upgrade.index("trace.resetSerial =") < ex_upgrade.index("OutRunVR::D3D9ResetTrace::Publish(trace);")
for token in (
    "lensResetTrace.readStable",
    "resetViewportExtentMatchesPre",
    "resetViewportRectMatchesPre",
    "resetScissorMatchesPre",
    "lensResetTrace.viewportX == savedViewport.X",
    "lensResetTrace.viewportY == savedViewport.Y",
    "OutRunVR::D3D9ResetTrace::ResetSucceeded",
    "OutRunVR::D3D9ResetTrace::ViewportValid",
    "OutRunVR::D3D9ResetTrace::ScissorValid",
):
    assert token in renderer, token
for token in (
    "Writer.test_and_set(std::memory_order_acquire)",
    "Writer.clear(std::memory_order_release)",
    "NextSerial.fetch_add(1",
    "PublishedResetSerial.store(",
    "snapshot.readStable = true;",
):
    assert token in reset_trace, token

# Reset epoch is publish-ordered; the inherited QPC is entry time. Keep
# separate real event clocks, and bracket publication without claiming its
# pre-lock timestamp is the exact serialized publish instant.
assert graphics.count("sourceEventQpc={} thread={} resetQpcRole=RESET_ENTRY") == 2
assert graphics.count("QueryPerformanceCounter(&sourceEventQpc);") == 2
reset_body = ex_upgrade.split("HRESULT __stdcall ResetCompatDest(", 1)[1].split(
    "HRESULT __stdcall CreateVertexBufferCompatDest(", 1)[0]
for token in ("qpcRole=RESET_ENTRY", "resetReturnQpc={}",
              "snapshotReadyQpc={}", "publishReturnQpc={}", "qpcFrequency={}"):
    assert token in reset_body, token
assert reset_body.index("deviceEx->ResetEx(") < reset_body.index(
    "QueryPerformanceCounter(&resetReturnQpc);") < reset_body.index(
    "RestoreClassicResetState(device)")
assert reset_body.index("QueryPerformanceCounter(&snapshotReadyQpc);") < reset_body.index(
    "OutRunVR::D3D9ResetTrace::Publish(trace);") < reset_body.index(
    "QueryPerformanceCounter(&publishReturnQpc);")

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

# Fresh projection pixels must be tagged with the render-time source identity.
# Reading the pre-publication verified global from ScheduleProjection recreates
# the A-labelled/B-pixels bug documented by the lens-flare review.
schedule_start = host_r23.index("void ScheduleProjection(")
schedule_end = host_r23.index("void ScheduleTheater(", schedule_start)
schedule_body = host_r23[schedule_start:schedule_end]
assert "ReadFresh(" not in schedule_body, "pixel probe regressed to stale verified-bundle attribution"
assert "projectionFrameId = sourceFrameId;" in schedule_body
assert "projectionPoseSequence = sourcePoseSequence;" in schedule_body
assert "sourceKind, &views" in host_r23

# A pixel-grid final-submission join is valid only when this xrEndFrame advanced
# the final receipt serial. Matching a previous frame/kind is not enough.
note_start = host_r23.index("void NoteFinalSubmission(")
note_end = host_r23.index("void ScheduleSource(", note_start)
note_body = host_r23[note_start:note_end]
assert "submissionSerialAfter <= submissionSerialBefore" in note_body
assert "projectionFinalReceiptSerial = submissionSerialAfter;" in note_body

# R24 fallback paths must write a current receipt rather than leaving a prior
# successful projection receipt visible to XR FRAME FULL.
assert "SubmitClassicFallbackWithReceipt" in host_r24
assert "LastEndFrameReceiptFrameId" in host_r24
assert "preservedHasLayer" in host_r24

# Full tracing is intentionally performance-heavy and must remain opt-in under
# the already-enabled VR telemetry switch, not silently promoted to all users.
assert "if (!Settings::VRTelemetry || !device)" in renderer
assert "Telemetry = true" in read("OutRun2006Tweaks.ini")

runpy.run_path(str(ROOT / "tools/verify_vr_lens_transaction_trace.py"), run_name="__main__")
print("PASS DX9Ex one-pass FULL visual trace contract: source -> queue -> D3DX -> D3D9 -> frame -> OpenXR -> collected ZIP")
print("RUNTIME_VALIDATION=UNTESTED")
