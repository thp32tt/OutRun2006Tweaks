#!/usr/bin/env python3
"""R30 world-affine stereo single-walk contract and deterministic numeric parity.

This verifies source routing plus a reference per-eye affine transform against a
shared-input two-eye model, including sparse masks and RHW guard boundaries.
Game build and Quest3/VDXR frame timing are separate gates.
"""
from pathlib import Path
import math
import random

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WF = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def verify_source(source):
    # R84's CPU-projected smoke/skid geometry must share ONE finite
    # two-eye origin for full-world and affine fallback. The old float
    # midpoint could overflow even though both xrLocateViews eyes were valid.
    for required in (
        "float headRelativeEyes[2][3]{};",
        "BuildHeadRelativeEyeOffsets(\n                    state.stereo.eyeOffset, headRelativeEyes)",
        "identityOrientation, headRelativeEyes[eye],",
        "const float localX = headRelativeEyes[eye][0];",
        "const float localY = headRelativeEyes[eye][1];",
    ):
        assert required in source, "R84 stereo origin contract lost: " + required
    assert "0.5f * (state.stereo.eyeOffset[0][" not in source
    start = source.index("bool R30TransformWorldAffineStereo(")
    # This helper precedes the shared seeding and per-eye fallback code.
    # Bound its single-walk assertions to the helper itself, not every
    # subsequently declared R30 world/fused routine.
    end = source.index("bool R30SeedWorldXyzrhwBuffers(", start)
    body = source[start:end]
    stereo_start = source.index("bool R30TransformXyzrhwStereo(", end)
    stereo = source[stereo_start:source.index("template <typename LeftDraw", stereo_start)]
    for term in (
        "!state.worldEffect || state.fullWorldReprojection",
        "left.size() != bytes || right.size() != bytes",
        "usedMask && usedMask->size() < vertexCount",
        "const bool sparseAffineTouched = usedMask && touched &&",
        "knownUsedCount == touched->size()",
        "knownUsedCount <= vertexCount / 4u",
        "const UINT affineVisitCount = sparseAffineTouched\n                ? knownUsedCount : vertexCount;",
        "sparseAffineTouched ? (*touched)[visit] : visit",
        "(sparseAffineTouched && !(*usedMask)[i])",
        "if (usedMask && !(*usedMask)[i])",
        "std::isfinite(z)", "std::isfinite(rhw)",
        "const float halfWidth = width * 0.5f;",
        "const float halfHeight = height * 0.5f;",
        "affineScaleX[eye] = state.worldScaleX[eye];",
        "affineScaleY[eye] = state.worldScaleY[eye];",
        "(1.0f - affineScaleX[eye]) * centerX +",
        "state.worldOffsetX[eye] * halfWidth",
        "(1.0f - affineScaleY[eye]) * centerY -",
        "state.worldOffsetY[eye] * halfHeight",
        "affineRhwX[eye] = state.parallaxPerRhwX[eye] * halfWidth;",
        "affineRhwY[eye] = -state.parallaxPerRhwY[eye] * halfHeight;",
        "!std::isfinite(affineBiasX[eye]) ||",
        "rhw > 0.0f && rhw < 1000.0f",
        "for (int eye = 0; eye < 2; ++eye)",
        "affineScaleX[eye] * x + affineBiasX[eye]",
        "affineScaleY[eye] * y + affineBiasY[eye]",
        "transformedX += affineRhwX[eye] * rhw;",
        "transformedY += affineRhwY[eye] * rhw;",
        "if (!std::isfinite(transformedX) ||",
        "eyeData[eye] + offset",
        "dst[0] = transformedX;",
        "dst[1] = transformedY;",
    ):
        assert term in body, "missing affine contract: " + term
    assert body.count("for (UINT visit = 0; visit < affineVisitCount; ++visit)") == 1
    assert "for (UINT i = 0; i < vertexCount; ++i)" not in body
    assert body.index("const float halfWidth") < body.index("for (UINT visit = 0; visit < affineVisitCount; ++visit)")
    assert body.index("affineBiasX[eye]") < body.index("for (UINT visit = 0; visit < affineVisitCount; ++visit)")
    assert body.index("const UINT i = sparseAffineTouched") < body.index("if (i >= vertexCount ||") < body.index("const auto* p =")
    assert "const float ndcX =" not in body and "const float ndcY =" not in body
    assert "dst[2] =" not in body and "dst[3] =" not in body
    assert "R30TryFusedWorldXyzrhwProjection(" in stereo
    guard = "if (!state.fullWorldReprojection)"
    dispatch = "return R30TransformWorldAffineStereo("
    assert stereo.count(guard) == 1 and stereo.count(dispatch) == 1
    assert stereo.index("R30SeedWorldXyzrhwBuffers(") < stereo.index(guard)
    assert stereo.index(guard) < stereo.index("R30TryFusedWorldXyzrhwProjection(")
    assert "if (leftFull != rightFull)" in stereo
    assert "R30TransformXyzrhwVertices(" in stereo
    assert "usedMask, knownUsedCount, touched);" in stereo
    fused_start = source.index("bool R30TryFusedWorldXyzrhwProjection(")
    fused = source[fused_start:stereo_start]
    for guard in (
        "const bool sparseTouched = usedMask && touched &&",
        "knownUsedCount == touched->size()",
        "knownUsedCount <= vertexCount / 4u",
        "sparseTouched ? knownUsedCount : vertexCount",
        "sparseTouched ? (*touched)[visit] : visit",
        "(sparseTouched && !(*usedMask)[i])",
        "if (sparseTouched)",  # fail-closed rollback restores sparse mutations
    ):
        assert guard in fused, "missing fused-world invariant: " + guard


def affine(x, y, rhw, view, eye):
    x0, y0, w, h, sx, sy, ox, oy, px, py = view
    nx = (x - x0) * (2.0 / w) - 1.0
    ny = 1.0 - (y - y0) * (2.0 / h)
    cx = sx[eye] * nx + ox[eye]
    cy = sy[eye] * ny + oy[eye]
    if rhw > 0.0 and rhw < 1000.0:
        cx += px[eye] * rhw
        cy += py[eye] * rhw
    return (x0 + (cx + 1.0) * 0.5 * w,
            y0 + (1.0 - cy) * 0.5 * h)


def affine_composed(x, y, rhw, view, eye):
    x0, y0, w, h, sx, sy, ox, oy, px, py = view
    half_w, half_h = w * .5, h * .5
    bias_x = (1 - sx[eye]) * (x0 + half_w) + ox[eye] * half_w
    bias_y = (1 - sy[eye]) * (y0 + half_h) - oy[eye] * half_h
    out_x = sx[eye] * x + bias_x
    out_y = sy[eye] * y + bias_y
    if 0.0 < rhw < 1000.0:
        out_x += px[eye] * half_w * rhw
        out_y -= py[eye] * half_h * rhw
    return out_x, out_y


def verify_math():
    rng = random.Random(686)
    checked = 0
    for n in (1, 8, 64, 257, 1024):
        for density in (0.0, 0.05, 0.25, 1.0):
            mask = [rng.random() < density for _ in range(n)]
            view = (
                rng.randrange(0, 100), rng.randrange(0, 100),
                rng.choice((640, 1280, 3440)), rng.choice((720, 1440)),
                [rng.uniform(.7, 1.3) for _ in range(2)],
                [rng.uniform(.7, 1.3) for _ in range(2)],
                [rng.uniform(-.5, .5) for _ in range(2)],
                [rng.uniform(-.5, .5) for _ in range(2)],
                [rng.uniform(-.002, .002) for _ in range(2)],
                [rng.uniform(-.002, .002) for _ in range(2)],
            )
            pts = [(rng.uniform(0, 3400), rng.uniform(0, 1400),
                    rng.uniform(0, 1), rng.choice((-1.0, 0.0, .000001,
                                                    .5, 5.0, 999.9, 1000.0)),
                    rng.randrange(2**24)) for _ in range(n)]
            # Old left-then-right loop versus new vertex-then-eye loop.
            old = [[None] * n for _ in range(2)]
            new = [[None] * n for _ in range(2)]
            for eye in range(2):
                for i, (x, y, z, rhw, packed) in enumerate(pts):
                    if mask[i]:
                        old[eye][i] = (*affine(x, y, rhw, view, eye), z, rhw, packed)
            for i, (x, y, z, rhw, packed) in enumerate(pts):
                if mask[i]:
                    for eye in range(2):
                        new[eye][i] = (*affine_composed(x, y, rhw, view, eye), z, rhw, packed)
            for eye in range(2):
                for baseline, composed in zip(old[eye], new[eye]):
                    if baseline is None:
                        assert composed is None
                    else:
                        assert baseline[2:] == composed[2:], "Z/RHW/packed changed"
                        assert abs(baseline[0] - composed[0]) < 1e-9
                        assert abs(baseline[1] - composed[1]) < 1e-9
            checked += sum(mask)
    assert checked > 1000
    # Any source NaN/Inf in a selected vertex must fail before either draw.
    for bad in (math.nan, math.inf, -math.inf):
        assert not math.isfinite(bad)
    return checked


def verify_float32_parity():
    # Model the single-precision arithmetic used by the game, including
    # source position, viewport, eye coefficients and RHW boundaries.
    import struct
    f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]
    rng = random.Random(691)
    maximum_error = 0.0
    for _ in range(12000):
        x0, y0 = f32(rng.randrange(0, 320)), f32(rng.randrange(0, 240))
        w = f32(rng.choice((320, 640, 1280, 3440, 4096)))
        h = f32(rng.choice((240, 720, 1440, 2160)))
        x = f32(x0 + rng.uniform(-.25, 1.25) * w)
        y = f32(y0 + rng.uniform(-.25, 1.25) * h)
        sx = f32(rng.uniform(.7, 1.3)); sy = f32(rng.uniform(.7, 1.3))
        ox = f32(rng.uniform(-.5, .5)); oy = f32(rng.uniform(-.5, .5))
        px = f32(rng.uniform(-.002, .002)); py = f32(rng.uniform(-.002, .002))
        rhw = f32(rng.choice((-1., 0., .000001, .5, 10., 999.9, 1000.)))
        nx = f32(f32(x - x0) * f32(2. / w) - 1.)
        ny = f32(1. - f32(f32(y - y0) * f32(2. / h)))
        cx = f32(f32(sx * nx) + ox)
        cy = f32(f32(sy * ny) + oy)
        if 0. < rhw < 1000.:
            cx = f32(cx + f32(px * rhw))
            cy = f32(cy + f32(py * rhw))
        old_x = f32(x0 + f32(f32(cx + 1.) * f32(.5) * w))
        old_y = f32(y0 + f32(f32(1. - cy) * f32(.5) * h))
        half_w, half_h = f32(w * .5), f32(h * .5)
        bx = f32(f32(f32(1. - sx) * f32(x0 + half_w)) + f32(ox * half_w))
        by = f32(f32(f32(1. - sy) * f32(y0 + half_h)) - f32(oy * half_h))
        new_x = f32(f32(sx * x) + bx)
        new_y = f32(f32(sy * y) + by)
        if 0. < rhw < 1000.:
            new_x = f32(new_x + f32(f32(px * half_w) * rhw))
            new_y = f32(new_y - f32(f32(py * half_h) * rhw))
        maximum_error = max(maximum_error,
                            abs(old_x - new_x), abs(old_y - new_y))
        assert abs(old_x - new_x) < .005
        assert abs(old_y - new_y) < .005
    return maximum_error


def main():
    source = CPP.read_text(encoding="utf-8")
    wf = WF.read_text(encoding="utf-8")
    assert wf.count("tools/verify_vr_r30_world_affine_dual_eye.py") == 2
    verify_source(source)
    mutations = (
        ("if (!state.fullWorldReprojection)", "if (state.fullWorldReprojection)"),
        ("if (usedMask && !(*usedMask)[i])", "if (false)"),
        ("knownUsedCount == touched->size()", "knownUsedCount != touched->size()"),
        ("knownUsedCount <= vertexCount / 4u", "knownUsedCount <= vertexCount"),
        ("const UINT affineVisitCount = sparseAffineTouched\n                ? knownUsedCount : vertexCount;", "const UINT affineVisitCount = vertexCount;"),
        ("sparseAffineTouched ? (*touched)[visit] : visit", "visit"),
        ("(sparseAffineTouched && !(*usedMask)[i])", "false"),
        ("std::isfinite(z)", "true"),
        ("std::isfinite(rhw)", "true"),
        ("rhw > 0.0f && rhw < 1000.0f", "rhw >= 0.0f && rhw <= 1000.0f"),
        ("transformedX += affineRhwX[eye] * rhw;", "transformedX += 0.0f;"),
        ("transformedY += affineRhwY[eye] * rhw;", "transformedY += 0.0f;"),
        ("affineScaleX[eye] = state.worldScaleX[eye];", "affineScaleX[eye] = 1.0f;"),
        ("affineScaleY[eye] = state.worldScaleY[eye];", "affineScaleY[eye] = 1.0f;"),
        ("state.worldOffsetX[eye] * halfWidth", "0.0f * halfWidth"),
        ("state.worldOffsetY[eye] * halfHeight", "0.0f * halfHeight"),
        ("!std::isfinite(affineBiasX[eye]) ||", "false ||"),
        ("dst[0] = transformedX;", "dst[0] = x;"),
        ("dst[1] = transformedY;", "dst[1] = y;"),
    )
    for good, bad in mutations:
        assert good in source, good
        # Mutate the new affine helper (or its explicit dispatch), not an
        # older independent-eye/fused function with identical expressions.
        start = source.index("bool R30TransformWorldAffineStereo(")
        at = source.index(good, start)
        altered = source[:at] + bad + source[at + len(good):]
        try:
            verify_source(altered)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("undetected destructive mutation: " + good)
    # A deterministic moderate-sparse producer spans the full VB yet
    # references only one quarter of its slots in shuffled draw order.
    mask = [i % 4 == 0 for i in range(4096)]
    touched = [i for i, selected in enumerate(mask) if selected]
    random.Random(721).shuffle(touched)
    fast_visits = touched if len(touched) <= len(mask) // 4 else range(len(mask))
    assert len(fast_visits) == 1024 and set(fast_visits) == set(touched)
    assert len(fast_visits) < len(mask), "no moderate sparse CPU-work reduction"
    # Mismatched or corrupted lists must not silently authorize a sparse read.
    assert len(touched[:-1]) != sum(mask)
    assert any(i >= len(mask) for i in touched[:-1] + [len(mask)])
    # The fused perspective path must reject loss of the producer density
    # boundary too, independent of the separate affine helper.
    fused_begin = source.index("bool R30TryFusedWorldXyzrhwProjection(")
    fused_end = source.index("bool R30TransformXyzrhwStereo(", fused_begin)
    fused_body = source[fused_begin:fused_end]
    for old, new in (
        ("knownUsedCount <= vertexCount / 4u", "knownUsedCount <= vertexCount"),
        ("sparseTouched ? knownUsedCount : vertexCount", "vertexCount"),
        ("(sparseTouched && !(*usedMask)[i])", "false"),
    ):
        assert fused_body.count(old) == 1
        damaged = source[:fused_begin] + fused_body.replace(old, new, 1) + source[fused_end:]
        try:
            verify_source(damaged)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("undetected fused-world sparse mutation: " + old)
    checked = verify_math()
    error = verify_float32_parity()
    print(f"PASS R30 draw-local world affine coefficients, {len(mutations)} negative mutations, {checked} referenced vertices, 12000 float32 pairs, max delta {error:.6f}px")


if __name__ == "__main__":
    main()
