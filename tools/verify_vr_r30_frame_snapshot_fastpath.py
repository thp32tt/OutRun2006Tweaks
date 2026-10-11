#!/usr/bin/env python3
"""R30 stereo hot-path owner-snapshot reuse and destructive safety checks."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r30.cpp"


def block(src, name):
    pos = src.index(name + "(")
    first = src.index("{", pos)
    depth = 0
    for i in range(first, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[first:i + 1]
    raise AssertionError("function scope unbalanced: " + name)


def verify(text):
    for name in (
        "R30EnsureSkyGlowResources",
        "R30CaptureSkyGlowSceneBeforeHud",
        "R30ApplyStereoSkyGlow",
        "R30HudAspectCompensation",
        "R30ExecuteXyzrhwStereo",
    ):
        part = block(text, name)
        assert part.count("R29OwnerCaptureFrameSnapshot()") == 1, name
        assert "const auto frame = R29OwnerCaptureFrameSnapshot();" in part, name
        assert "R29OwnerCaptureFrameSnapshot()." not in part, name
    for name, expected in (
        ("R30ConfigureXyzrhwWorldEffect", 2),
        ("R30TryScreenSpaceFovDraw", 3),
    ):
        part = block(text, name)
        assert part.count("R29OwnerCaptureFrameSnapshot()") == expected, name
        assert "auto frame = R29OwnerCaptureFrameSnapshot();" in part, name
        assert "R29OwnerCaptureFrameSnapshot()." not in part, name
        assert part.index("R29OwnerTryBootstrapRightDepth(device);") < part.index(
            "                frame = R29OwnerCaptureFrameSnapshot();"), name
        for token in ("frame.trackedDepthStencil", "frame.rightDepthSynchronized",
                      "frame.rightStencilSynchronized", "R29OwnerDepthTestActive(device)",
                      "R29OwnerStencilTestActive(device)"):
            assert token in part, (name, token)
    for name in ("R30ExecuteXyzrhwStereo", "R30TryScreenSpaceFovDraw"):
        part = block(text, name)
        for token in ("frame.rightEyeSurface", "frame.rightEyeDepth",
                      "frame.trackedDepthStencil", "R29OwnerRestoreRightPassState"):
            assert token in part, (name, token)
    xyz = block(text, "R30ExecuteXyzrhwStereo")
    assert xyz.index("const HRESULT leftHr = leftDraw();") < xyz.index(
        "const auto frame = R29OwnerCaptureFrameSnapshot();") < xyz.index(
        "rightHr = R29OwnerCallOriginalSetRenderTarget(")
    fov = block(text, "R30TryScreenSpaceFovDraw")
    assert fov.index("const HRESULT leftHr = actualDraw();") < fov.rindex(
        "frame = R29OwnerCaptureFrameSnapshot();") < fov.index(
        "rightHr = R29OwnerCallOriginalSetRenderTarget(")
    sky = block(text, "R30ApplyStereoSkyGlow")
    assert "R30SkyGlowSceneCaptureEpoch != frame.presentEpoch" in sky
    assert "R30SkyGlow.factor > 1" in sky
    assert "stateBlock->Apply()" in sky
    scene = block(text, "R30CaptureSkyGlowSceneBeforeHud")
    assert "R30SkyGlowSceneCaptureEpoch == frame.presentEpoch" in scene
    assert "frame.backBuffer, frame.rightEyeSurface" in scene


if __name__ == "__main__":
    src = SRC.read_text(encoding="utf-8")
    verify(src)
    negatives = (
        ("const auto frame = R29OwnerCaptureFrameSnapshot();", "const auto frame = {};"),
        ("frame.rightEyeSurface", "nullptr"),
        ("frame.rightEyeDepth", "nullptr"),
        ("frame.trackedDepthStencil", "nullptr"),
        ("                frame = R29OwnerCaptureFrameSnapshot();", "                // no bootstrap refresh"),
        ("R29OwnerTryBootstrapRightDepth(device);", "// no bootstrap"),
        ("R29OwnerRestoreRightPassState", "R29OwnerNoRestore"),
        ("R30SkyGlowSceneCaptureEpoch != frame.presentEpoch", "true"),
        ("R30SkyGlow.factor > 1", "false"),
    )
    for good, bad in negatives:
        assert good in src, good
        try:
            verify(src.replace(good, bad, 1))
        except AssertionError:
            pass
        else:
            raise AssertionError("destructive mutation survived: " + good)
    print("PASS R30 frame snapshot reuse and %d negative mutations" % len(negatives))
