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


def validate_hud_pair(source: str) -> None:
    """Indexed and non-indexed screen HUD use one traversal; world remains bilateral."""
    pair = source.split("bool R30TransformXyzrhwStereo(", 1)[1].split(
        "template <typename LeftDraw", 1
    )[0]
    fast = pair.split("if (!state.worldEffect)", 1)[1].split(
        "bool leftFull = false;", 1
    )[0]
    for required in (
        "stride < sizeof(float) * 4",
        "bytes > 4u * 1024u * 1024u",
        "!std::isfinite(depthSpan) || depthSpan <= 1.0e-6f",
        "std::memcpy(left.data(), source, bytes);",
        "std::memcpy(right.data(), source, bytes);",
        "R30HudContainScale(state.stereo, hudScaleX, hudScaleY);",
        "hudScaleX * state.eyeScale[0]",
        "hudScaleX * state.eyeScale[1]",
        "for (UINT i = 0; i < vertexCount; ++i)",
        "!std::isfinite(src[2]) || !std::isfinite(src[3])",
        "const float correctedY = hudScaleY * ndcY;",
        "eyeScaleX[eye] * ndcX + state.eyeOffset[eye]",
        "if (!std::isfinite(transformedX))",
        "if (!std::isfinite(transformedY))",
        "dst[0] = transformedX;",
        "dst[1] = transformedY;",
        "return true;",
    ):
        assert required in fast, f"pair-HUD source guard lost: {required}"
    assert fast.count("R30HudContainScale(") == 1
    assert fast.count("for (UINT i = 0; i < vertexCount; ++i)") == 1
    assert fast.index("const float ndcScaleX") < fast.index("for (UINT i")
    assert pair.index("if (!state.worldEffect)") < pair.index("bool leftFull = false;")
    assert "if (leftFull != rightFull)" in pair

    # Both eyes share the indexed coverage fence, sparse copy and vertex scan.
    for required in (
        "(usedMask && usedMask->size() < vertexCount)",
        "if (usedMask && vertexCount >= 64u)",
        "usedMask->begin() + vertexCount",
        "static_cast<std::size_t>(selectedCount) * 4u <= vertexCount",
        "while (cursor < vertexCount && !(*usedMask)[cursor])",
        "while (cursor < vertexCount && (*usedMask)[cursor])",
        "std::memcpy(left.data() + offset,",
        "std::memcpy(right.data() + offset,",
        "if (!sparseCopied)",
        "if (usedMask && !(*usedMask)[i])",
    ):
        assert required in fast, "indexed HUD fused contract: " + required
    assert fast.index("usedMask->size() < vertexCount") < fast.index("left.resize(bytes)")
    assert fast.index("if (usedMask && !(*usedMask)[i])") < fast.index("!std::isfinite(src[2])")

    # Old and paired algebraic order are identical: repeated HUD containment
    # and per-eye vertex traversal are unnecessary, but eye disparity is not.
    import math
    import random
    rng = random.Random(663)
    for _ in range(512):
        width = rng.uniform(100, 5000)
        height = rng.uniform(100, 3000)
        x0, y0 = rng.uniform(-100, 100), rng.uniform(-100, 100)
        x, y = rng.uniform(-200, width + 200), rng.uniform(-200, height + 200)
        hud_x, hud_y = rng.uniform(0.75, 1.5), rng.uniform(0.75, 1.5)
        eye_scales = [rng.uniform(0.7, 1.3) for _ in range(2)]
        eye_offsets = [rng.uniform(-0.3, 0.3) for _ in range(2)]
        ndc_x = (x - x0) * (2.0 / width) - 1.0
        ndc_y = 1.0 - (y - y0) * (2.0 / height)
        for eye in range(2):
            old_x = x0 + ((hud_x * eye_scales[eye] * ndc_x +
                           eye_offsets[eye]) + 1.0) * 0.5 * width
            new_x = x0 + (((hud_x * eye_scales[eye]) * ndc_x +
                           eye_offsets[eye]) + 1.0) * 0.5 * width
            old_y = y0 + (1.0 - hud_y * ndc_y) * 0.5 * height
            new_y = y0 + (1.0 - hud_y * ndc_y) * 0.5 * height
            assert math.isclose(old_x, new_x, rel_tol=0, abs_tol=1e-10)
            assert old_y == new_y

    # Negative indexed mutations must be rejected even if the non-indexed
    # original still passes its numeric regression.
    for before, after in (
        ("(usedMask && usedMask->size() < vertexCount)", "false"),
        ("if (usedMask && !(*usedMask)[i])", "if (false)"),
        ("if (!sparseCopied)", "if (false)"),
        ("std::memcpy(right.data() + offset,", "std::memcpy(left.data() + offset,"),
    ):
        assert fast.count(before) == 1, before
        bad = source.replace(fast, fast.replace(before, after, 1), 1)
        try:
            validate_hud_pair_structure(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError("indexed HUD mutation survived: " + before)

    # Limit destructive mutations to the new HUD fast branch. The guard
    # condition precedes `fast`, and similarly named assignments exist in
    # R30TransformXyzrhwVertices before the paired path.
    fast_branch = pair.split("bool leftFull = false;", 1)[0]
    assert source.count(fast_branch) == 1
    for before, after in (
        ("if (!state.worldEffect)", "if (true)"),
        ("dst[1] = transformedY;", "dst[1] = src[1];"),
        ("hudScaleX * state.eyeScale[1]", "hudScaleX * state.eyeScale[0]"),
        ("eyeScaleX[eye] * ndcX + state.eyeOffset[eye]", "eyeScaleX[eye] * ndcX"),
        ("!std::isfinite(src[2]) || !std::isfinite(src[3])", "!std::isfinite(src[2])"),
        ("bytes > 4u * 1024u * 1024u", "bytes > 8u * 1024u * 1024u"),
    ):
        assert fast_branch.count(before) == 1, before
        bad = source.replace(
            fast_branch, fast_branch.replace(before, after, 1), 1
        )
        try:
            validate_hud_pair_structure(bad)
        except AssertionError:
            continue
        raise AssertionError(f"pair-HUD destructive mutation accepted: {before}")


def validate_hud_pair_structure(source: str) -> None:
    pair = source.split("bool R30TransformXyzrhwStereo(", 1)[1].split(
        "template <typename LeftDraw", 1
    )[0]
    fast_branch = pair.split("bool leftFull = false;", 1)[0]
    for required in (
        "if (!state.worldEffect)",
        "dst[1] = transformedY;",
        "hudScaleX * state.eyeScale[1]",
        "eyeScaleX[eye] * ndcX + state.eyeOffset[eye]",
        "!std::isfinite(src[2]) || !std::isfinite(src[3])",
        "bytes > 4u * 1024u * 1024u",
    ):
        assert required in fast_branch, required
    for required in (
        "(usedMask && usedMask->size() < vertexCount)",
        "if (usedMask && !(*usedMask)[i])",
        "if (!sparseCopied)",
        "std::memcpy(right.data() + offset,",
    ):
        assert required in fast_branch, required


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
    validate_hud_pair(text)
    print(
        "R30 HUD contain draw-invariant fastpath PASS; "
        f"{negative_mutations(text)} destructive mutations rejected"
    )
