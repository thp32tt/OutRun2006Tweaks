#!/usr/bin/env python3
"""Reject per-vertex OpenXR eye extent/FOV/HUD aspect work in R30 XYZRHW.

Full reprojection (particles/decals) must remain separate from the unchanged
screen-space HUD stereo equations. This is a source/mutation guard, not a claim
of measured Quest 3 GPU frame-time or image correctness.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r30.cpp"


def validate(source: str) -> None:
    body = source.split("bool R30TransformXyzrhwVertices(", 1)[1].split(
        "bool R30TransformXyzrhwStereo(", 1
    )[0]
    setup = body.split(
        "if (state.worldEffect && state.fullWorldReprojection &&", 1
    )[0]
    affine = body.split("++R30XyzrhwAtomicFallbacks;", 1)[1]

    # Latched stereo/eye extent and HUD configuration do not change per vertex.
    # The legacy code repeated up to eight FOV tan() calls and eye-extent
    # lookups for every vertex in both eye copies.
    for required in (
        "float hudScaleX = 1.0f;",
        "float hudScaleY = 1.0f;",
        "if (!state.worldEffect)\n                R30HudContainScale(state.stereo, hudScaleX, hudScaleY);",
    ):
        assert required in setup, required
    assert "R30HudContainScale(" not in affine, "HUD aspect queried per vertex"

    # Preserve the stereo math, including OpenXR asymmetric eye offsets and
    # *uniform* source-HUD aspect containment. Do not use worldEye scaling for
    # the HUD or change its Z/RHW/depth.
    assert "correctedX =\n                        hudScaleX * state.eyeScale[eye] * ndcX + state.eyeOffset[eye];" in affine
    assert "correctedY = hudScaleY * ndcY;" in affine
    assert "p[0] = transformedX;" in affine
    assert "p[1] = transformedY;" in affine
    assert "p[2] = transformedZ;" not in affine
    assert "p[3] = invEyeW;" not in affine
    assert "state.worldEffect && state.fullWorldReprojection" in body
    assert "if (leftFull != rightFull)" in source.split(
        "bool R30TransformXyzrhwStereo(", 1
    )[1]


def negative_mutations(source: str) -> int:
    negatives = [
        (
            "if (!state.worldEffect)\n                R30HudContainScale(state.stereo, hudScaleX, hudScaleY);",
            "if (state.worldEffect)\n                R30HudContainScale(state.stereo, hudScaleX, hudScaleY);",
        ),
        (
            "R30HudContainScale(state.stereo, hudScaleX, hudScaleY);",
            "(void)state.stereo;",
        ),
        (
            "float hudScaleY = 1.0f;",
            "float hudScaleY = 0.0f;",
        ),
        (
            "hudScaleX * state.eyeScale[eye] * ndcX",
            "state.eyeScale[eye] * ndcX",
        ),
        (
            "correctedY = hudScaleY * ndcY;",
            "correctedY = ndcY;",
        ),
    ]
    count = 0
    for original, incorrect in negatives:
        assert original in source, original
        changed = source.replace(original, incorrect, 1)
        try:
            validate(changed)
        except AssertionError:
            count += 1
        else:
            raise AssertionError(f"Mutation unexpectedly passed: {original}")

    # The original regression (moving the expensive call back into the loop)
    # must be rejected even when it retains numerically identical HUD output.
    original = "if (!state.worldEffect)\n                R30HudContainScale(state.stereo, hudScaleX, hudScaleY);"
    bad = source.replace(original, "if (!state.worldEffect) { /* deferred */ }", 1)
    bad = bad.replace(
        "correctedX =\n                        hudScaleX",
        "R30HudContainScale(state.stereo, hudScaleX, hudScaleY);\n"
        "                    correctedX =\n                        hudScaleX",
        1,
    )
    try:
        validate(bad)
    except AssertionError:
        count += 1
    else:
        raise AssertionError("Per-vertex HUD aspect regression survived")
    return count


if __name__ == "__main__":
    text = SOURCE.read_text(encoding="utf-8")
    validate(text)
    print(
        "R30 HUD contain draw-invariant fastpath PASS; "
        f"{negative_mutations(text)} destructive mutations rejected"
    )
