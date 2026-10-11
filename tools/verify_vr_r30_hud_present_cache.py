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
        "R30HudContain.valid = false;",
        "R30HudContain.valid = true;",
        "R30HudAspectCompensation(stereo)",
        "scaleX = userScale;",
        "scaleY = userScale / sourceOverTarget;",
        "scaleX = userScale * sourceOverTarget;",
        "scaleY = userScale;",
    ):
        assert required in body, required
    assert body.index("R30HudContain.valid = false;") < body.index(
        "R30HudAspectCompensation(stereo)") < body.index(
        "R30HudContain.valid = true;")
    assert source.count("R30HudContainScale(state.stereo, hudScaleX, hudScaleY)") == 1


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
