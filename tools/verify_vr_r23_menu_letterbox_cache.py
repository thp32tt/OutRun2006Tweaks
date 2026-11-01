#!/usr/bin/env python3
"""R23 front-end 2D ownership: menu/restart must be a centered LOCAL quad.

The old menu path wrote a menu object anchor into
XrCompositionLayerProjectionView::pose. ProjectionView::pose is the view/camera
pose, so a pre-rasterized 2D front-end could appear in an eye-dependent corner.
The production menu now uses the existing LOCAL-space theater quad. This is a
static source contract; Quest optical validation remains runtime-only.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vrhost/src/main_r23.cpp"
source = SOURCE.read_text(encoding="utf-8-sig")


def verify(text: str) -> None:
    # The generic theater owner itself must be a LOCAL-space quad.
    theater = text.split("bool R23RenderTheater(", 1)[1].split(
        "void R23CopyMatchedViews", 1)[0]
    required_theater = (
        "quad = { XR_TYPE_COMPOSITION_LAYER_QUAD };",
        "quad.space = localSpace;",
        "quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;",
        "quad.pose = c.theaterAnchor_;",
        "c.GetCapturedGameUv(",
        "PlanTopLeftLogicalCaptureUv(",
        "R23PublishedMirrorUv(",
        "GAME_PUBLISHED_D3D9_HWND_CLIENT_RECT",
        "ORIGINAL_TITLE_MENU_4_3_WITHIN_GAME_HWND",
        "logicalRectVisible=1",
        "LOGICAL_CANVAS_CAPTURE_SOURCE_RECT",
        "c.EnsureTheaterAnchor(viewSpace, localSpace, displayTime)",
    )
    for token in required_theater:
        assert token in theater, "missing LOCAL quad contract: " + token

    # Presentation changes invalidate the theater anchor, so menu entry and
    # post-race restart reacquire the current HMD-centred LOCAL anchor.
    transition = text.split("if (presentation != lastPresentation)", 1)[1].split(
        "bool layerReady = false;", 1)[0]
    assert "compositor.ReferenceSpaceChanged();" in transition
    legacy = (ROOT / "vrhost/src/main.cpp").read_text(encoding="utf-8-sig")
    ref_change = legacy.split("void ReferenceSpaceChanged()", 1)[1].split(
        "void Shutdown()", 1)[0]
    assert "theaterAnchorValid_ = false;" in ref_change

    # The actual non-gameplay/menu branch must submit the quad, not put an
    # object/menu anchor into ProjectionView::pose.
    menu = text.split(
        "const std::uint32_t clientGameState = shared.GameState();", 1
    )[1].split("QueryPerformanceCounter(&re);", 1)[0]
    required_menu = (
        "if (capture.available &&",
        "R23RenderTheater(",
        "compositor, viewSpace, localSpace,",
        "fs.predictedDisplayTime, quad, false",
        "reinterpret_cast<const XrCompositionLayerBaseHeader*>(",
        "&quad);",
        'menu-local-fixed-quad-fresh',
        'menu-local-fixed-quad-cached',
        "cachedMenuProjectionValid = false;",
    )
    for token in required_menu:
        assert token in menu, "missing menu quad route: " + token
    assert "R23RenderWorldLockedMenuProjection(" not in menu
    assert "projection.views = pv.data();" not in menu
    assert "intentionalMonoProjection = true;" not in menu

    # Capture remains game-client cropped, so the quad must not contain
    # unrelated desktop pixels. A taller XR client may extend off the monitor;
    # only the exact 1920x1080 logical rectangle itself must be fully visible.
    # 2026-11-01 real Quest log: QPC-missed menu must use CURRENT
    # same-process HWND, never the 3440x1440 Desktop Duplication rectangle.
    assert 'bool R23LiveGameWindowUv(' in text
    assert 'GetWindowThreadProcessId(hwnd, &ownerPid)' in text
    assert 'ownerPid != c.gamePid_' in text
    assert 'GetClientRect(hwnd, &client)' in text
    assert 'ClientToScreen(hwnd, &tl)' in text
    assert 'ClientToScreen(hwnd, &br)' in text
    assert 'if (!clipped.fullyVisible)' in text
    assert 'R23LiveGameWindowUv(c, liveUv, liveRect)' in theater
    assert 'capturedTheaterClient = liveRect;' in theater
    assert 'publishedMirrorApplied = true;' in theater
    assert 'else if (clientGameState != 0xFFFFFFFFu)' in theater
    assert '"CURRENT_SAME_PID_WIN32_CLIENT_RECT"' in theater
    assert 'CURRENT_SAME_PID_WIN32_CLIENT_RECT_CENTERED_16_9_FRONTEND_MIRROR' in theater
    assert 'normalized16x9=' in theater
    assert 'rawClient=' in theater
    assert 'PlanCenteredContent(' in theater
    assert 'const bool publishedMirrorGeometryEligible =' in theater
    assert 'mirrorFrame->clientPid == c.gamePid_' in theater
    assert 'CanUsePublishedMirrorGeometry(' in theater
    assert "GetCapturedGameUv(" in theater
    assert "capturedTheaterFullyVisible &&" not in theater
    assert "LOGICAL_CANVAS_CAPTURE_SOURCE_RECT" in theater
    assert "fitPixels=" in theater
    assert "physicalReceipt=0" in theater
    assert "[VR TRACE SUMO WHOLE COMPOSITE FULL]" in theater
    assert "COMPLETE_2D_3D_GAME_MIRROR_NO_LOGICAL_CROP" in theater
    assert "RecentSumoPhysicalCanvasReceipt(" not in theater
    assert "frame.clientPid != c.gamePid_" in text
    assert "publishedMirrorApplied" in theater
    assert "!publishedMirrorApplied" in theater
    assert "authoredFourThreeApplied" in theater
    assert "(clientGameState == 0x04u || clientGameState == 0x09u)" in theater
    assert "PlanCenteredContent(" in theater


verify(source)

mutations = (
    ("quad.space = localSpace;", "quad.space = viewSpace;"),
    ("quad.pose = c.theaterAnchor_;", "quad.pose = {};"),
    ("R23RenderTheater(", "R23RenderWorldLockedMenuProjection("),
    ("fs.predictedDisplayTime, quad, false",
     "fs.predictedDisplayTime, projection, false"),
    ('menu-local-fixed-quad-fresh', 'menu-local-fixed-projection-fresh'),
    ("if (presentation != lastPresentation)\n            {\n                compositor.ReferenceSpaceChanged();",
     "if (presentation != lastPresentation)\n            {\n                /* no anchor reset */"),
)
for old, bad in mutations:
    assert old in source, "mutation fixture missing: " + old
    altered = source.replace(old, bad, 1)
    try:
        verify(altered)
    except (AssertionError, IndexError, ValueError):
        continue
    raise AssertionError("unsafe menu quad mutation escaped: " + old)

print("PASS R23 menu/restart centered LOCAL quad ownership; six destructive mutants")
print("RUNTIME_VALIDATION=UNTESTED")
