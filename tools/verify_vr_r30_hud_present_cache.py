#!/usr/bin/env python3
"""Fail if R30 repeats eye-aspect/VD extent lookup across HUD draws per Present.

Source + destructive mutations; actual x86 source compile/link is enforced by
DX9Ex Active Gate. Neither establishes Quest3/VDXR image or FPS acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
R29_SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"
R29_API = ROOT / "src/vr/core/r29_owner_api.hpp"
HOST_SOURCE = ROOT / "vrhost/src/main.cpp"


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
        "R30HudContain.pauseResponsive == pauseResponsive",
        "R30HudContain.eyeFov[i] == fov[i]",
        "std::uint32_t eyeExtent[4]{};",
        "R29OwnerReadCoherentEyeExtentPair(eyeExtent);",
        "R30HudContain.eyeExtent[i] == eyeExtent[i]",
        "canCache && extentMatches && R30HudContain.valid",
        "R30HudContain.eyeExtent[i] = eyeExtent[i]",
        "R30HudContain.valid = false;",
        "R30HudContain.valid = true;",
        "R30HudAspectCompensation(\n                    stereo, frame.width, frame.height, eyeExtent)",
        "const bool pauseResponsive = R30IsPauseMenuElement() &&",
        "std::isfinite(Settings::VRPauseMenuScale.get()) &&",
        "R30HudContain.pauseResponsive = pauseResponsive;",
        "const float opticalScale =",
        "OutRunVrPauseEye::ResponsiveMenuScale(",
        "userScale, sourceOverTarget, pauseResponsive);",
        "scaleX = opticalScale;",
        "scaleY = opticalScale / sourceOverTarget;",
        "scaleX = opticalScale * sourceOverTarget;",
        "scaleY = opticalScale;",
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
        ("R30HudContain.pauseResponsive == pauseResponsive", "true"),
        ("R30HudContain.eyeFov[i] == fov[i]", "true"),
        ("R30HudContain.eyeExtent[i] == eyeExtent[i]", "true"),
        ("canCache && extentMatches && R30HudContain.valid",
         "canCache && R30HudContain.valid"),
        ("R30HudContain.eyeExtent[i] = eyeExtent[i]", "/* stale extent */"),
        ("R30HudAspectCompensation(\n                    stereo, frame.width, frame.height, eyeExtent)",
         "R30HudAspectCompensation(stereo)"),
        ("R30HudContain.valid = false;", "// no invalidation"),
        ("R30HudContain.valid = true;", "// no publication"),
        ("R30HudContain.pauseResponsive = pauseResponsive;",
         "R30HudContain.pauseResponsive = false;"),
        ("userScale, sourceOverTarget, pauseResponsive);",
         "userScale, sourceOverTarget, false);"),
        ("scaleX = opticalScale;", "scaleX = userScale;"),
        ("scaleY = opticalScale / sourceOverTarget;", "scaleY = userScale / sourceOverTarget;"),
        ("scaleX = opticalScale * sourceOverTarget;", "scaleX = userScale * sourceOverTarget;"),
        ("scaleY = opticalScale;", "scaleY = userScale;"),
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
    # A one-time HUD diagnostic log is also compiled into the independent
    # R29-R33 Win32 TU. It must follow the widened signature and reuse the
    # already-captured frame rather than leaving an orphan one-arg call.
    # Diagnostic indentation changes when stereo-success publication is\n    # guarded, but the SAME frame snapshot must remain the argument owner.\n    import re\n    assert re.search(\n        r"R30HudAspectCompensation\\s*\\(\\s*stereo\\s*,\\s*"\n        r"frame\\.width\\s*,\\s*frame\\.height\\s*\\)\\s*\\);",\n        source\n    ) is not None
    assert "R30HudAspectCompensation(stereo)" not in source

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


# 00828: host's two recommended eye extents must be read under ONE
# SharedPoseState seqlock epoch, not as four unrelated width/height loads.
def verify_coherent_eye_extent_pair(r29: str, api: str, host: str, r30: str) -> None:
    assert "bool R29OwnerReadCoherentEyeExtentPair(std::uint32_t out[4]) noexcept;" in api
    body = r29.split("bool R29OwnerReadCoherentEyeExtentPair(", 1)[1].split(
        "bool R29OwnerTryGetDirectTransportIdentity(", 1
    )[0]
    for token in (
        "out[0] = out[1] = out[2] = out[3] = 0;",
        "for (unsigned attempt = 0; attempt < 4u; ++attempt)",
        "const std::uint32_t before = shared->sequence;",
        "if (before & 1u)",
        "const std::uint32_t leftW = shared->recommendedWidth[0];",
        "const std::uint32_t leftH = shared->recommendedHeight[0];",
        "const std::uint32_t rightW = shared->recommendedWidth[1];",
        "const std::uint32_t rightH = shared->recommendedHeight[1];",
        "const std::uint32_t after = shared->sequence;",
        "if (before != after || (after & 1u))",
        "size != sizeof(OutRunVR::SharedPoseState)",
        "!leftW || !leftH || !rightW || !rightH",
        "out[0] = leftW;", "out[1] = leftH;",
        "out[2] = rightW;", "out[3] = rightH;",
    ):
        assert token in body, token
    assert body.count("MemoryBarrier();") == 2
    assert body.index("const std::uint32_t before") < body.index("const std::uint32_t leftW")
    assert body.index("const std::uint32_t rightH") < body.index("const std::uint32_t after")
    assert body.index("if (before != after") < body.index("out[0] = leftW;")
    assert host.count("state_->recommendedWidth[eye] =") >= 2
    assert host.count("state_->recommendedHeight[eye] =") >= 2
    assert "Begin();" in host and "End();" in host
    hud = r30.split("void R30HudContainScale(", 1)[1].split(
        "// Only exact, producer-owned gameplay text", 1
    )[0]
    assert hud.count("R29OwnerReadCoherentEyeExtentPair(eyeExtent);") == 1
    assert "R29OwnerRecommendedEyeExtent(eye," not in hud
    assert "R30HudContain.eyeExtent[i] == eyeExtent[i]" in hud
    assert "R30HudAspectCompensation(\n                    stereo, frame.width, frame.height, eyeExtent)" in hud


if __name__ == "__main__":
    r29 = R29_SOURCE.read_text(encoding="utf-8")
    api = R29_API.read_text(encoding="utf-8")
    host = HOST_SOURCE.read_text(encoding="utf-8")
    r30 = SOURCE.read_text(encoding="utf-8")
    verify_coherent_eye_extent_pair(r29, api, host, r30)
    mutations = (
        ("if (before & 1u)", "if (false)"),
        ("if (before != after || (after & 1u))", "if (false)"),
        ("const std::uint32_t rightW = shared->recommendedWidth[1];",
         "const std::uint32_t rightW = shared->recommendedWidth[0];"),
        ("const std::uint32_t rightH = shared->recommendedHeight[1];",
         "const std::uint32_t rightH = shared->recommendedHeight[0];"),
        ("out[0] = out[1] = out[2] = out[3] = 0;", "/* stale eye extents */"),
        ("!leftW || !leftH || !rightW || !rightH", "false"),
        ("size != sizeof(OutRunVR::SharedPoseState)", "false"),
    )
    for original, mutant in mutations:
        assert original in r29, original
        try:
            verify_coherent_eye_extent_pair(r29.replace(original, mutant, 1), api, host, r30)
        except AssertionError:
            pass
        else:
            raise AssertionError("Eye extent seqlock mutant survived: " + original)
    # Resize, recenter, absent host and desktop FOV-only fallback contract.
    def accept(before, after, four, good_header=True):
        return four if before % 2 == 0 and before == after and good_header and all(four) else (0,0,0,0)
    quest=(2496,2688,2496,2688)
    resized=(3000,2800,3000,2800)
    assert accept(12,12,quest) == quest
    assert accept(12,14,(quest[0],quest[1],resized[2],resized[3])) == (0,0,0,0)
    assert accept(13,14,resized) == (0,0,0,0)
    assert accept(12,12,(2496,2688,0,0)) == (0,0,0,0)
    assert accept(12,12,quest,False) == (0,0,0,0)
    print(f"PASS: XR binocular seqlock, reset/FOV fallback, {len(mutations)} negative mutations")
