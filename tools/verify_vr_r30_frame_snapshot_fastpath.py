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
        "PresentDestR30",
        "R30PrepareXyzrhwState",
        "R30CaptureSkyGlowSceneBeforeHud",
        "R30ApplyStereoSkyGlow",
        "R30ExecuteXyzrhwStereo",
    ):
        part = block(text, name)
        assert part.count("R29OwnerCaptureFrameSnapshot()") == 1, name
        assert "const auto frame = R29OwnerCaptureFrameSnapshot();" in part, name
        assert "R29OwnerCaptureFrameSnapshot()." not in part, name
    # R30HudAspectCompensation now BORROWS source width/height from the
    # caller's single Present snapshot. Capturing again here could interleave
    # a game Reset and store the wrong source ratio under the old HUD key.
    aspect = block(text, "R30HudAspectCompensation")
    assert "R29OwnerCaptureFrameSnapshot()" not in aspect
    assert "if (!sourceWidth || !sourceHeight)" in aspect
    assert "static_cast<float>(sourceWidth) /" in aspect
    assert "static_cast<float>(sourceHeight)" in aspect
    hud = block(text, "R30HudContainScale")
    assert hud.count("R29OwnerCaptureFrameSnapshot()") == 1
    assert "stereo, frame.width, frame.height, eyeExtent)" in hud
    assert "R30HudContain.sourceWidth = frame.width;" in hud
    assert "R30HudContain.sourceHeight = frame.height;" in hud
    # Existing world/SkyGlow/eye RT snapshot ownership remains unchanged.
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
    assert "IDirect3DSurface9* savedDepth = frame.trackedDepthStencil;" in xyz
    assert xyz.index("const HRESULT leftHr = leftDraw();") < xyz.index(
        "const auto frame = R29OwnerCaptureFrameSnapshot();") < xyz.index(
        "rightHr = R29OwnerCallOriginalSetRenderTarget(")
    fov = block(text, "R30TryScreenSpaceFovDraw")
    assert fov.index("const HRESULT leftHr = actualDraw();") < fov.rindex(
        "frame = R29OwnerCaptureFrameSnapshot();") < fov.index(
        "rightHr = R29OwnerCallOriginalSetRenderTarget(")
    sky = block(text, "R30ApplyStereoSkyGlow")
    assert "R30SkyGlowSceneCaptureEpoch != frame.presentEpoch" in sky
    assert "R30SkyGlow.factor > 1;" in sky
    assert "stateBlock->Apply()" in sky
    scene = block(text, "R30CaptureSkyGlowSceneBeforeHud")
    assert "R30SkyGlowSceneCaptureEpoch == frame.presentEpoch" in scene
    assert "frame.backBuffer, frame.rightEyeSurface" in scene


if __name__ == "__main__":
    src = SRC.read_text(encoding="utf-8")
    verify(src)
    # Target each destructive mutation to the function actually being checked.
    # A global first match may hit an earlier SkyGlow path instead and pass.
    # Replace every matching occurrence inside the selected function: the
    # SkyGlow branch has multiple independent factor>1 consumers.
    def mutate_function(src, name, good, bad):
        anchor = src.index(name + "(")
        scope_start = src.index("{", anchor)
        scope = block(src, name)
        assert good in scope, (name, good)
        return (src[:scope_start] + scope.replace(good, bad) +
                src[scope_start + len(scope):])

    negatives = (
        ("R30HudAspectCompensation",
         "static_cast<float>(sourceWidth) /",
         "static_cast<float>(sourceHeight) /"),
        ("R30HudAspectCompensation",
         "if (!sourceWidth || !sourceHeight)",
         "if (false)"),
        ("R30HudContainScale",
         "stereo, frame.width, frame.height, eyeExtent)",
         "stereo, frame.height, frame.width, eyeExtent)"),
        ("R30EnsureSkyGlowResources",
         "const auto frame = R29OwnerCaptureFrameSnapshot();",
         "const auto frame = {};"),
        ("R30ExecuteXyzrhwStereo", "frame.rightEyeSurface", "nullptr"),
        ("R30ExecuteXyzrhwStereo", "frame.rightEyeDepth", "nullptr"),
        ("R30ExecuteXyzrhwStereo", "frame.trackedDepthStencil", "nullptr"),
        ("R30ConfigureXyzrhwWorldEffect",
         "                frame = R29OwnerCaptureFrameSnapshot();",
         "                // no bootstrap refresh"),
        ("R30ConfigureXyzrhwWorldEffect",
         "R29OwnerTryBootstrapRightDepth(device);", "// no bootstrap"),
        ("R30ExecuteXyzrhwStereo",
         "R29OwnerRestoreRightPassState", "R29OwnerNoRestore"),
        ("R30ApplyStereoSkyGlow",
         "R30SkyGlowSceneCaptureEpoch != frame.presentEpoch", "true"),
        ("R30ApplyStereoSkyGlow", "R30SkyGlow.factor > 1;", "false;"),
    )
    for name, good, bad in negatives:
        try:
            verify(mutate_function(src, name, good, bad))
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError(
                "destructive mutation survived: " + name + " / " + good)
    print("PASS R30 frame snapshot reuse and %d negative mutations" % len(negatives))
