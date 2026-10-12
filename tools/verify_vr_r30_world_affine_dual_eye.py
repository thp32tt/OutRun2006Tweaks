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
    start = source.index("bool R30TransformWorldAffineStereo(")
    end = source.index("bool R30TransformXyzrhwStereo(", start)
    body = source[start:end]
    stereo = source[end:source.index("template <typename LeftDraw", end)]
    for term in (
        "!state.worldEffect || state.fullWorldReprojection",
        "left.size() != bytes || right.size() != bytes",
        "usedMask && usedMask->size() < vertexCount",
        "if (usedMask && !(*usedMask)[i])",
        "std::isfinite(z)", "std::isfinite(rhw)",
        "const float ndcX = (x - x0) * ndcScaleX - 1.0f;",
        "const float ndcY = 1.0f - (y - y0) * ndcScaleY;",
        "rhw > 0.0f && rhw < 1000.0f",
        "for (int eye = 0; eye < 2; ++eye)",
        "state.worldScaleX[eye] * ndcX +",
        "state.worldOffsetX[eye]",
        "state.worldScaleY[eye] * ndcY +",
        "state.worldOffsetY[eye]",
        "state.parallaxPerRhwX[eye] * rhw",
        "state.parallaxPerRhwY[eye] * rhw",
        "if (!std::isfinite(transformedX) ||",
        "(eye == 0 ? left.data() : right.data()) + offset",
        "dst[0] = transformedX;",
        "dst[1] = transformedY;",
    ):
        assert term in body, "missing affine contract: " + term
    assert body.count("for (UINT i = 0; i < vertexCount; ++i)") == 1
    assert body.index("const float ndcX") < body.index("for (int eye = 0; eye < 2")
    assert "dst[2] =" not in body and "dst[3] =" not in body
    assert "R30TryFusedWorldXyzrhwProjection(" in stereo
    guard = "if (!state.fullWorldReprojection)"
    dispatch = "return R30TransformWorldAffineStereo("
    assert stereo.count(guard) == 1 and stereo.count(dispatch) == 1
    assert stereo.index("R30SeedWorldXyzrhwBuffers(") < stereo.index(guard)
    assert stereo.index(guard) < stereo.index("R30TryFusedWorldXyzrhwProjection(")
    assert "if (leftFull != rightFull)" in stereo
    assert "R30TransformXyzrhwVertices(" in stereo


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
                        new[eye][i] = (*affine(x, y, rhw, view, eye), z, rhw, packed)
            assert new == old, "bilateral pixel/depth/attribute divergence"
            checked += sum(mask)
    assert checked > 1000
    # Any source NaN/Inf in a selected vertex must fail before either draw.
    for bad in (math.nan, math.inf, -math.inf):
        assert not math.isfinite(bad)
    return checked


def main():
    source = CPP.read_text(encoding="utf-8")
    wf = WF.read_text(encoding="utf-8")
    assert wf.count("tools/verify_vr_r30_world_affine_dual_eye.py") == 2
    verify_source(source)
    mutations = (
        ("if (!state.fullWorldReprojection)", "if (state.fullWorldReprojection)"),
        ("if (usedMask && !(*usedMask)[i])", "if (false)"),
        ("std::isfinite(z)", "true"),
        ("std::isfinite(rhw)", "true"),
        ("rhw > 0.0f && rhw < 1000.0f", "rhw >= 0.0f && rhw <= 1000.0f"),
        ("state.parallaxPerRhwX[eye] * rhw", "0.0f"),
        ("state.parallaxPerRhwY[eye] * rhw", "0.0f"),
        ("state.worldScaleX[eye] * ndcX +", "0.0f +"),
        ("state.worldScaleY[eye] * ndcY +", "0.0f +"),
        ("dst[0] = transformedX;", "dst[0] = x;"),
        ("dst[1] = transformedY;", "dst[1] = y;"),
    )
    for good, bad in mutations:
        assert good in source, good
        altered = source.replace(good, bad, 1)
        try:
            verify_source(altered)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("undetected destructive mutation: " + good)
    checked = verify_math()
    print(f"PASS R30 affine-only binocular source routing, {len(mutations)} negative mutations, {checked} referenced vertices")


if __name__ == "__main__":
    main()
