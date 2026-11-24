#!/usr/bin/env python3
"""EXT16-011: PBR pixel UV-gradient TBN must not vary with pixel density.

Run the portable math for valid, mirrored, zero and nearly parallel UV
derivatives. Compile the actual HLSL separately in the Windows CI job.
No game/external model files or proprietary textures are required.
"""
from pathlib import Path
from math import isfinite, sqrt

SHADER = Path(__file__).resolve().parents[1] / "src/vr/game/dino_external_pbr_shader.hpp"


def valid_derivative_basis(dx: tuple[float, float],
                           dy: tuple[float, float]) -> bool:
    # Exact scalar predicate used by the runtime SM3.0 shader.
    det = dx[0] * dy[1] - dx[1] * dy[0]
    gradient_area2 = (dx[0] ** 2 + dx[1] ** 2) * (
        dy[0] ** 2 + dy[1] ** 2)
    return gradient_area2 > 1.e-30 and det * det > gradient_area2 * 1.e-8


def mapped_normal(sample: tuple[float, float, float], strength: float,
                  has_map: bool, mirrored: bool = False) -> tuple[float, float, float]:
    # Orthonormal TBN: T=(1,0,0), B=(0,+/-1,0), N=(0,0,1).
    # sample is already decoded from [0,1] to [-1,1].
    base = (0., 0., 1.)
    if not has_map or strength <= 0.:
        return base
    x, y, z = sample
    candidate = (x * strength, y * strength * (-1. if mirrored else 1.), z)
    length_sq = sum(v * v for v in candidate)
    if length_sq <= 1.e-12:
        return base
    return tuple(v / sqrt(length_sq) for v in candidate)


def main() -> None:
    shader = SHADER.read_text()
    assert "float gradientArea2 = dot(dtdx,dtdx)*dot(dtdy,dtdy);" in shader
    assert "gradientArea2 > 1.e-30" in shader
    assert "det*det > gradientArea2*1.e-8" in shader
    assert "abs(det) > 0.0000001" not in shader
    assert "tangentSq > 1.e-12" in shader
    assert "dot(derivativeB,derivativeB) > 1.e-12" in shader
    assert "T *= rsqrt(tangentSq);" in shader
    assert "handedness = dot(cross(N,T),derivativeB) < 0" in shader
    assert "mapN.xy *= factors.z;" in shader
    strength_gate = shader.index("if (factors.w > 0.5 && factors.z > 0.0 &&")
    sample_pos = shader.index("tex2D(normalMap,input.uv)")
    assert strength_gate < sample_pos
    assert "float3 mappedN = mapN.x*T+mapN.y*B+mapN.z*N;" in shader
    assert "float mappedSq = dot(mappedN,mappedN);" in shader
    assert "if (mappedSq > 1.e-12) N = mappedN * rsqrt(mappedSq);" in shader
    assert "N = normalize(mapN.x*T+mapN.y*B+mapN.z*N);" not in shader
    # Zero strength is a material-level disable, not a negative-Z flip.
    for _car in (*range(15), 28):
        for texel in ((0., 0., -1.), (0., 0., 0.), (.6, .2, .8)):
            assert mapped_normal(texel, 0., True) == (0., 0., 1.)
            assert mapped_normal(texel, 1., False) == (0., 0., 1.)
        assert mapped_normal((0., 0., 0.), 1., True) == (0., 0., 1.)
        assert mapped_normal((1.e-8, 0., 0.), 1., True) == (0., 0., 1.)
        assert mapped_normal((0., 0., 1.), 1., True) == (0., 0., 1.)
        perturbed = mapped_normal((.6, .2, .8), 1., True)
        mirrored = mapped_normal((.6, .2, .8), 1., True, True)
        stronger = mapped_normal((.6, .2, .8), 2., True)
        assert all(isfinite(v) for v in perturbed)
        assert abs(sum(v*v for v in perturbed)-1.) < 1.e-12
        assert perturbed[0] > 0. and perturbed[1] > 0.
        assert mirrored == (perturbed[0], -perturbed[1], perturbed[2])
        assert stronger[0] > perturbed[0]
    assert "tex2D(normalMap,input.uv)" in shader
    assert "tex2D(ormMap,input.uv)" in shader

    cases = (
        ((.01, 0.), (0., .01), True),
        ((1. / 5000., 0.), (0., 1. / 3000.), True),
        ((1.e-7, 0.), (0., 1.e-7), True),
        ((0., .01), (.01, 0.), True),  # mirrored UV basis
        ((.01, .01), (.02, .02), False),  # parallel
        ((.01, 0.), (.02, 1.e-8), False),  # almost parallel
        ((0., 0.), (0., 0.), False),  # missing UV
    )
    # All 16 canonical vehicle materials share this exact shader path.
    for _car in (*range(15), 28):
        for dx, dy, expected in cases:
            assert valid_derivative_basis(dx, dy) is expected
            # Screen-density changes must not flip a valid UV basis.
            # Keep finite float32 gradient energies above the shader's
            # explicit 1e-30 stability floor (not an unlimited scale test).
            for scale in (1., 10., 100.):
                scaled_dx = (dx[0] * scale, dx[1] * scale)
                scaled_dy = (dy[0] * scale, dy[1] * scale)
                assert valid_derivative_basis(scaled_dx, scaled_dy) is expected

    dx, dy = cases[1][:2]
    assert abs(dx[0] * dy[1] - dx[1] * dy[0]) < 1.e-7
    assert valid_derivative_basis(dx, dy)
    print("EXT16_011_PBR_TBN_DERIVATIVE_POSITIVE_NEGATIVE_PASS")


if __name__ == "__main__":
    main()
