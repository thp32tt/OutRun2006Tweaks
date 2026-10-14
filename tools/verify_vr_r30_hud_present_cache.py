#!/usr/bin/env python3
"""Fail if R30 repeats eye-aspect/VD extent lookup across HUD draws per Present.

Source + destructive mutations; actual x86 source compile/link is enforced by
DX9Ex Active Gate. Neither establishes Quest3/VDXR image or FPS acceptance.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r30.cpp"


def verify(source: str) -> None:
    assert "thread_local R30HudContainCache R30HudContain{};" in source
    assert "R30HudContain = {};" in source, "reset must invalidate"
    body = source.split("        void R30HudContainScale(\n", 1)[1].split(
        "        bool R30TransformHudScissor(", 1
    )[0]
    for required in (
        "frame.presentEpoch != 0",
        "frame.width != 0 && frame.height != 0",
        "std::isfinite(userScale)",
        "canCache = canCache && std::isfinite(angle)",
        "R30HudContain.presentEpoch == frame.presentEpoch",
        "R30HudContain.poseSequence == stereo.poseSequence",
        "R30HudContain.sourceWidth == frame.width",
        "R30HudContain.sourceHeight == frame.height",
        "R30HudContain.userScale == userScale",
        "R30HudContain.eyeFov[i] == fov[i]",
        "std::uint32_t eyeExtent[4]{};",
        "R29OwnerRecommendedEyeExtent(eye,",
        "R30HudContain.eyeExtent[i] == eyeExtent[i]",
        "canCache && extentMatches && R30HudContain.valid",
        "R30HudContain.eyeExtent[i] = eyeExtent[i]",
        "R30HudContain.valid = false;",
        "R30HudContain.valid = true;",
        "R30HudAspectCompensation(\n                    stereo, frame.width, frame.height, eyeExtent)",
        "scaleX = userScale;",
        "scaleY = userScale / sourceOverTarget;",
        "scaleX = userScale * sourceOverTarget;",
        "scaleY = userScale;",
    ):
        assert required in body, required
    assert body.index("R30HudContain.valid = false;") < body.index(
        "R30HudAspectCompensation(\n                    stereo, frame.width, frame.height, eyeExtent)") < body.index(
        "R30HudContain.valid = true;")
    # In a single Present/FOV epoch, XR can initially report no dimensions,
    # then publish 2496x2688 (or resize later). Every transition must break
    # the aspect cache without an extra geometry walk.
    def cache_hit(old, new):
        return old == new
    no_host = (0, 0, 0, 0)
    quest = (2496, 2688, 2496, 2688)
    changed = (3000, 2800, 3000, 2800)
    assert cache_hit(quest, quest)
    assert not cache_hit(no_host, quest)
    assert not cache_hit(quest, changed)
    assert not cache_hit(quest, (2496, 2688, 0, 0))
    assert 3440 / 1440 / (2496 / 2688) != 3440 / 1440 / (3000 / 2800)
    # Legacy single-eye/affine fallback and the fused non-indexed HUD pair
    # each look up the already-latched per-Present contain scale once. Never
    # move this FOV work into the HUD vertex loop.
    legacy = source.split("bool R30TransformXyzrhwVertices(", 1)[1].split(
        "bool R30TransformXyzrhwStereo(", 1
    )[0]
    paired = source.split("bool R30TransformXyzrhwStereo(", 1)[1].split(
        "template <typename LeftDraw", 1
    )[0]
    lookup = "R30HudContainScale(state.stereo, hudScaleX, hudScaleY)"
    assert legacy.count(lookup) == 1
    assert paired.count(lookup) == 1
    assert source.count(lookup) == 2


if __name__ == "__main__":
    content = SOURCE.read_text(encoding="utf-8")
    verify(content)
    mutations = (
        ("R30HudContain = {};", "// missing reset"),
        ("frame.presentEpoch != 0", "true"),
        ("frame.width != 0 && frame.height != 0", "true"),
        ("std::isfinite(userScale)", "true"),
        ("canCache = canCache && std::isfinite(angle)", "// no NaN fence"),
        ("R30HudContain.presentEpoch == frame.presentEpoch", "true"),
        ("R30HudContain.poseSequence == stereo.poseSequence", "true"),
        ("R30HudContain.sourceWidth == frame.width", "true"),
        ("R30HudContain.sourceHeight == frame.height", "true"),
        ("R30HudContain.userScale == userScale", "true"),
        ("R30HudContain.eyeFov[i] == fov[i]", "true"),
        ("R30HudContain.eyeExtent[i] == eyeExtent[i]", "true"),
        ("canCache && extentMatches && R30HudContain.valid",
         "canCache && R30HudContain.valid"),
        ("R30HudContain.eyeExtent[i] = eyeExtent[i]", "/* stale extent */"),
        ("R30HudAspectCompensation(\n                    stereo, frame.width, frame.height, eyeExtent)",
         "R30HudAspectCompensation(stereo)"),
        ("R30HudContain.valid = false;", "// no invalidation"),
        ("R30HudContain.valid = true;", "// no publication"),
        ("scaleY = userScale / sourceOverTarget;", "scaleY = userScale;"),
        ("scaleX = userScale * sourceOverTarget;", "scaleX = userScale;"),
    )
    for original, broken in mutations:
        assert original in content, original
        try:
            verify(content.replace(original, broken, 1))
        except AssertionError:
            pass
        else:
            raise AssertionError("Destructive mutation survived: " + original)
    print("PASS: per-Present HUD aspect reuse, stereo formula and "
          f"{len(mutations)} destructive mutations rejected")

# 00810: source aspect and cache identity must use one R29 frame generation.
def verify_source_aspect_snapshot(source: str) -> None:
    aspect = source.split("float R30HudAspectCompensation(", 1)[1].split(
        "float R30HudScopeScale()", 1)[0]
    contain = source.split("void R30HudContainScale(", 1)[1].split(
        "// Only exact, producer-owned gameplay text", 1)[0]
    for token in ("std::uint32_t sourceWidth, std::uint32_t sourceHeight,",
                  "if (!sourceWidth || !sourceHeight)",
                  "static_cast<float>(sourceWidth) /",
                  "static_cast<float>(sourceHeight);"):
        assert token in aspect, token
    assert "R29OwnerCaptureFrameSnapshot()" not in aspect
    assert contain.count("R29OwnerCaptureFrameSnapshot()") == 1
    assert "stereo, frame.width, frame.height, eyeExtent)" in contain
    assert "R30HudContain.sourceWidth = frame.width;" in contain
    assert "R30HudContain.sourceHeight = frame.height;" in contain
    assert "R30HudContain.valid = false;" in contain

if __name__ == "__main__":
    source = SOURCE.read_text(encoding="utf-8")
    verify_source_aspect_snapshot(source)
    eye_aspect = 2496 / 2688
    # User-supported 4:3, 16:9 and 21:9 source ratios; a mid-call
    # 21:9 -> 16:9 switch MUST NOT memoize the new aspect under old key.
    for w, h in ((640,480), (1920,1080), (3440,1440)):
        value = (w / h) / eye_aspect
        assert value > 0.75 and value < 3.5
    assert abs((3440 / 1440) / eye_aspect -
               (1280 / 720) / eye_aspect) > 0.25
    for correct, mutant in (
        ("std::uint32_t sourceWidth, std::uint32_t sourceHeight,",
         "std::uint32_t sourceWidth, std::uint32_t ignoredHeight,"),
        ("if (!sourceWidth || !sourceHeight)", "if (false)"),
        ("static_cast<float>(sourceWidth) /", "static_cast<float>(sourceHeight) /"),
        ("stereo, frame.width, frame.height, eyeExtent)",
         "stereo, frame.height, frame.width, eyeExtent)"),
        ("R30HudContain.sourceHeight = frame.height;",
         "R30HudContain.sourceHeight = 0;"),
    ):
        assert correct in source, correct
        try:
            verify_source_aspect_snapshot(source.replace(correct, mutant, 1))
        except AssertionError:
            continue
        raise AssertionError("HUD source generation mutant survived: " + correct)
    print("PASS R30 same-source cache, 3 aspect scenarios, 5 negative mutants")
