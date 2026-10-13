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
    assert "correctedY = hudScaleY * ndcY - pauseNdcOffset;" in affine
    # Pause offset must stay draw-local and outside the HUD vertex loop.
    assert affine.count("const float pauseNdcOffset =") == 1
    assert "state.worldEffect ? 0.0f :" in affine
    assert "2.0f * R30PauseMenuVerticalFraction();" in affine
    assert affine.index("const float pauseNdcOffset =") < affine.index("for (UINT i = 0; i < vertexCount; ++i)")
    assert "p[0] = transformedX;" in affine
    assert "p[1] = transformedY;" in affine
    assert "p[2] = transformedZ;" not in affine
    assert "p[3] = invEyeW;" not in affine
    assert "state.worldEffect && state.fullWorldReprojection" in body
    assert "if (leftFull != rightFull)" in source.split(
        "bool R30TransformXyzrhwStereo(", 1
    )[1]


def validate_hud_pair_structure(source: str) -> None:
    """Check draw-local binocular HUD affine and existing sparse/failure gates."""
    part = source.split("bool R30TransformXyzrhwStereo(", 1)[1].split(
        "// This is the high-frequency indexed smoke/sand/decal path:", 1
    )[0]
    for required in (
        "if (!state.worldEffect)",
        "stride < sizeof(float) * 4",
        "bytes > 4u * 1024u * 1024u",
        "(usedMask && usedMask->size() < vertexCount)",
        "!std::isfinite(depthSpan) || depthSpan <= 1.0e-6f",
        "if (usedMask && vertexCount >= 64u)",
        "static_cast<std::size_t>(selectedCount) * 4u <= vertexCount",
        "std::memcpy(left.data() + offset,",
        "std::memcpy(right.data() + offset,",
        "if (!sparseCopied)",
        "std::memcpy(left.data(), source, bytes);",
        "std::memcpy(right.data(), source, bytes);",
        "R30HudContainScale(state.stereo, hudScaleX, hudScaleY);",
        "hudScaleX * state.eyeScale[0]",
        "hudScaleX * state.eyeScale[1]",
        "state.eyeOffset[0] * halfWidth",
        "state.eyeOffset[1] * halfWidth",
        "(1.0f - hudScaleY) * (y0 + halfHeight)",
        "if (usedMask && !(*usedMask)[i])",
        "!std::isfinite(src[2]) || !std::isfinite(src[3])",
        "!std::isfinite(transformedLeftX)",
        "!std::isfinite(transformedRightX)",
        "leftDst[0] = transformedLeftX;",
        "leftDst[1] = transformedY;",
        "rightDst[0] = transformedRightX;",
        "rightDst[1] = transformedY;",
    ):
        assert required in part, required
    assert part.count("R30HudContainScale(") == 1
    # The original dense traversal is still selected for unindexed/unknown
    # masks; sparse indexed batches now use their producer-verified touched
    # list. Both routes must share the same one-pass binocular affine math.
    visit = "for (UINT visit = 0; visit < hudVisitCount; ++visit)"
    assert part.count(visit) == 1
    assert "sparseHudTouched ? knownUsedCount : vertexCount" in part
    assert "const UINT i = sparseHudTouched ? (*touched)[visit] : visit;" in part
    assert "if (i >= vertexCount ||" in part
    assert "(sparseHudTouched && !(*usedMask)[i]))" in part
    assert "for (int eye = 0; eye < 2; ++eye)" not in part
    assert part.index("const float eyeBiasX[2]") < part.index(visit)
    assert part.index("const float hudBiasY") < part.index(visit)
    assert "if (leftFull != rightFull)" in source


def validate_hud_pair(source: str) -> None:
    """Exact source, negative mutants and original NDC vs affine float32 parity."""
    import random
    import struct
    validate_hud_pair_structure(source)
    start = source.index("bool R30TransformXyzrhwStereo(")
    end = source.index("// This is the high-frequency indexed smoke/sand/decal path:", start)
    fast = source[start:end]
    negatives = (
        ("hudScaleX * state.eyeScale[1]", "hudScaleX * state.eyeScale[0]"),
        ("state.eyeOffset[1] * halfWidth", "state.eyeOffset[0] * halfWidth"),
        ("rightDst[0] = transformedRightX;", "rightDst[0] = transformedLeftX;"),
        ("rightDst[1] = transformedY;", "rightDst[1] = src[1];"),
        ("if (usedMask && !(*usedMask)[i])", "if (false)"),
        ("!std::isfinite(src[2]) || !std::isfinite(src[3])", "!std::isfinite(src[2])"),
        ("if (!sparseCopied)", "if (false)"),
        ("std::memcpy(right.data() + offset,", "std::memcpy(left.data() + offset,"),
        ("(usedMask && usedMask->size() < vertexCount)", "false"),
    )
    for old, wrong in negatives:
        assert fast.count(old) == 1, old
        bad = source[:start] + fast.replace(old, wrong, 1) + source[end:]
        try:
            validate_hud_pair_structure(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError("HUD affine destructive mutation escaped: " + old)

    def f32(v):
        return struct.unpack("<f", struct.pack("<f", v))[0]

    rng = random.Random(689)
    worst = 0.0
    for _ in range(16000):
        w, h = f32(rng.uniform(640, 5120)), f32(rng.uniform(480, 2880))
        x0, y0 = f32(rng.uniform(-200, 200)), f32(rng.uniform(-200, 200))
        x, y = f32(rng.uniform(-200, 1.5 * w)), f32(rng.uniform(-200, 1.5 * h))
        sx, sy = f32(rng.uniform(.65, 1.4)), f32(rng.uniform(.65, 1.4))
        offsets = [f32(rng.uniform(-.3, .3)), f32(rng.uniform(-.3, .3))]
        scales = [f32(sx * f32(rng.uniform(.6, 1.3))) for _ in range(2)]
        halfw, halfh = f32(w * .5), f32(h * .5)
        nx = f32(f32(f32(x - x0) * f32(2 / w)) - 1)
        ny = f32(1 - f32(f32(y - y0) * f32(2 / h)))
        oldy = f32(y0 + f32(f32(1 - f32(sy * ny)) * halfh))
        newy = f32(f32(sy * y) + f32(f32(1 - sy) * f32(y0 + halfh)))
        worst = max(worst, abs(oldy - newy))
        for i in range(2):
            oldx = f32(x0 + f32(f32(f32(scales[i] * nx + offsets[i]) + 1) * halfw))
            bias = f32(f32(f32(1 - scales[i]) * f32(x0 + halfw)) + f32(offsets[i] * halfw))
            newx = f32(f32(scales[i] * x) + bias)
            worst = max(worst, abs(oldx - newx))
    assert worst < .008, "HUD affine float32 pixel error: " + str(worst)
    print("PASS R30 HUD binocular affine: 16000 float32 cases, 9 negative mutants, max %.6f px" % worst)


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
            "correctedY = hudScaleY * ndcY - pauseNdcOffset;",
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
    validate_hud_pair(text)
    print(
        "R30 HUD contain draw-invariant fastpath PASS; "
        f"{negative_mutations(text)} destructive mutations rejected"
    )
