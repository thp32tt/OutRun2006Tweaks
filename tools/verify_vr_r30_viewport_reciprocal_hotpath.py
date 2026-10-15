#!/usr/bin/env python3
"""DX9Ex XYZRHW draw-local viewport reciprocals, stereo/fallback guards and float32 parity."""
from pathlib import Path
import random
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def body_for(source: str) -> str:
    # This guard owns the original single-eye vertex fallback only. The
    # 00684 fused-binocular path is verified independently, and including
    # it here adds a third valid viewport-NDC expression to a two-use gate.
    return source.split("bool R30TransformXyzrhwVertices(", 1)[1].split(
        "bool R30TryFusedWorldXyzrhwProjection(", 1)[0]


def valid(code: str) -> bool:
    try:
        guard = code.index("if (width <= 0.0f || height <= 0.0f ||")
        scale_x = code.index("const float ndcScaleX = 2.0f / width;")
        scale_y = code.index("const float ndcScaleY = 2.0f / height;")
        full = code.index("if (state.worldEffect && state.fullWorldReprojection &&\n                allowFullReprojection)")
        rollback = code.index("for (UINT i = 0; i < modifiedVertexEnd; ++i)", full)
        second = code.index("            for (UINT i = 0; i < vertexCount; ++i)", rollback)
        x = "const float ndcX = (x - x0) * ndcScaleX - 1.0f;"
        y = "const float ndcY = 1.0f - (y - y0) * ndcScaleY;"
        return (
            guard < scale_x < scale_y < full < second
            and code.count(x) == 2 and code.count(y) == 2
            and x in code[full:rollback] and y in code[full:rollback]
            and x in code[second:] and y in code[second:]
            and "((x - x0) / width)" not in code
            and "((y - y0) / height)" not in code
            and "depthSpan <= 1.0e-6f" in code[guard:scale_x]
            and "else if (!R30SeedWorldXyzrhwBuffers(" in code
            and "if (preseeded)" in code
            and "if (!restored)" in code
            and "state.inverseBaseProjection.m[row][col]" in code
            and "state.eyeTail[eye].m[row][col]" in code
            and "clipEye[3] <= 1.0e-6f" in code
            and "if (fullDrawOk && selectedVertices != 0)" in code
            and code.count("else if (!R30SeedWorldXyzrhwBuffers(") == 1
            and "std::memcpy(outputVertex(i), sourceVertex(i)," in code[rollback:second]
            and "4u * sizeof(float));" in code[rollback:second]
            and "state.parallaxPerRhwX[eye] * rhw" in code)
    except ValueError:
        return False


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def float32_viewport_parity() -> None:
    rng = random.Random(645)
    max_error = 0.0
    for _ in range(8000):
        width = f32(rng.uniform(320, 4096))
        height = f32(rng.uniform(240, 2160))
        x0 = f32(rng.uniform(-250, 2000))
        y0 = f32(rng.uniform(-250, 1200))
        x = f32(x0 + rng.uniform(-0.25, 1.25) * width)
        y = f32(y0 + rng.uniform(-0.25, 1.25) * height)
        for origin, coord, extent, sign in (
                (x0, x, width, 1), (y0, y, height, -1)):
            delta = f32(coord - origin)
            old = f32(f32(f32(delta / extent) * 2.0) - 1.0) if sign == 1 else (
                f32(1.0 - f32(f32(delta / extent) * 2.0)))
            scale = f32(2.0 / extent)
            new = f32(f32(delta * scale) - 1.0) if sign == 1 else (
                f32(1.0 - f32(delta * scale)))
            # Convert NDC difference back to pixels; the reciprocal hoist
            # only tolerates subpixel float-roundoff, not a changed eye scale.
            error = abs(new - old) * extent * 0.5
            max_error = max(max_error, error)
            assert error < 0.005, (extent, coord, old, new, error)
    print(f"PASS viewport float32 parity: 16000 axis cases, max {max_error:.6f} pixel")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    code = body_for(source)
    assert workflow.count("tools/verify_vr_r30_viewport_reciprocal_hotpath.py") == 2
    assert valid(code), "draw-local reciprocal / stereo projection / fallback contract lost"
    mutations = (
        ("const float ndcScaleX = 2.0f / width;", "const float ndcScaleX = 2.0f / height;"),
        ("const float ndcScaleY = 2.0f / height;", "const float ndcScaleY = 2.0f / width;"),
        ("* ndcScaleX - 1.0f;", "/ width - 1.0f;"),
        ("* ndcScaleY;", "* ndcScaleX;"),
        ("width <= 0.0f || height <= 0.0f", "false"),
        ("if (!restored)", "if (false)"),
        ("state.eyeTail[eye].m[row][col]", "state.eyeProjection[eye].m[row][col]"),
        ("state.parallaxPerRhwX[eye] * rhw", "0.0f"),
        ("clipEye[3] <= 1.0e-6f", "false"),
    )
    for n, (before, after) in enumerate(mutations, 1):
        assert before in code, f"mutation {n} absent"
        damaged = code.replace(before, after, 1)
        assert not valid(damaged), f"mutation {n} escaped"
    stereo = source.split("bool R30TransformXyzrhwStereo(", 1)[1].split(
        "template <typename LeftDraw", 1)[0]
    assert "if (leftFull != rightFull)" in stereo
    assert "state, 0, left, usedMask, false, ignored, false)" in stereo
    assert "state, 1, right, usedMask, false, ignored, false)" in stereo
    float32_viewport_parity()
    print(f"PASS R30 XYZRHW viewport reciprocal hotpath: {len(mutations)} negative mutations")


if __name__ == "__main__":
    main()
