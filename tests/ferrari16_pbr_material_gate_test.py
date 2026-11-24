#!/usr/bin/env python3
"""Positive/negative regression: reject orphan and incomplete PBR maps."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "ferrari16"))
from pbr_material_gate import (  # noqa: E402
    uncovered_pbr_materials, pbr_opaque_coverage_ok,
    triangle_has_pbr_basis, triangle_uv_basis, triangle_source_tangent_collapsed)


def main() -> None:
    # Two opaque materials, one tagged glass material (not PBR-required).
    assert pbr_opaque_coverage_ok(4, {0, 1}, {0, 1}, {0, 1}, {0, 1})
    assert pbr_opaque_coverage_ok(4, {0}, {0}, {0}, {0})
    # A valid UV triangle on material 0 must NOT mask bad UV triangles
    # or stripped DDS mip levels on that same material.
    assert not pbr_opaque_coverage_ok(4, {0}, {0}, {0}, {0}, {0})
    assert not pbr_opaque_coverage_ok(4, {0}, {0}, {0}, {0}, (), {0})
    assert pbr_opaque_coverage_ok(4, {0}, {0}, {0}, {0}, {1}, {1})
    assert pbr_opaque_coverage_ok(4, {0}, {0, 2}, {0, 2}, {0})
    # Previously, file-wide normal_maps>0 and orm_maps>0 both passed even if
    # the only normal/ORM maps were orphaned or on different materials.
    assert not pbr_opaque_coverage_ok(4, {0}, {1}, {1}, {0})
    assert not pbr_opaque_coverage_ok(4, {0}, {0}, {1}, {0})
    assert not pbr_opaque_coverage_ok(4, {0, 1}, {0}, {0, 1}, {0, 1})
    assert not pbr_opaque_coverage_ok(4, {0}, {0}, {0}, set())
    assert not pbr_opaque_coverage_ok(2, {0}, {0}, {0}, {0})
    assert not pbr_opaque_coverage_ok(4, set(), {0}, {0}, {0})
    assert uncovered_pbr_materials(4, {0, 1}, {0}, {1}, {1}) == {
        "no_normal": [1], "no_orm": [0], "degenerate_uv": [0],
        "disabled_normal_strength": [],
        "partially_degenerate_uv": [], "incomplete_pbr_mips": [],
        "unsupported_version": [], "no_opaque_materials": []}
    # A disabled normal map attached to a used opaque material is not
    # functional coverage; an unused or glass-only material is exempt.
    assert not pbr_opaque_coverage_ok(
        4, {0, 1}, {0, 1}, {0, 1}, {0, 1}, disabled_normal_strength={1})
    assert pbr_opaque_coverage_ok(
        4, {0}, {0, 1}, {0}, {0}, disabled_normal_strength={1})
    assert uncovered_pbr_materials(
        4, {0, 1}, {0}, {0, 1}, {0, 1},
        disabled_normal_strength={0, 1})["disabled_normal_strength"] == [0]
    assert triangle_uv_basis((0., 0.), (1., 0.), (0., 1.))
    assert triangle_uv_basis((0., 0.), (0., 1.), (1., 0.))  # mirrored UV
    assert not triangle_uv_basis((0., 0.), (0., 0.), (0., 0.))
    assert not triangle_uv_basis((0., 0.), (1e-5, 0.), (0., 1e-5))
    assert triangle_has_pbr_basis((0, 0, 0), (1, 0, 0), (0, 1, 0),
                                  (0, 0), (1, 0), (0, 1))
    assert not triangle_has_pbr_basis((0, 0, 0), (1, 0, 0), (2, 0, 0),
                                      (0, 0), (1, 0), (0, 1))
    assert not triangle_has_pbr_basis((0, 0, 0), (1, 0, 0), (0, 1, 0),
                                      (0, 0), (0, 0), (0, 0))
    positions = ((0., 0., 0.), (1., 0., 0.), (0., 1., 0.))
    for uvs, tangent in (
            (((0., 0.), (1., 0.), (0., 1.)), (1., 0., 0.)),
            (((0., 0.), (-1., 0.), (0., 1.)), (1., 0., 0.)),
            (((0., 0.), (0., 1.), (1., 0.)), (0., 1., 0.))):
        assert triangle_source_tangent_collapsed(positions, uvs, (tangent,)*3)
        assert triangle_source_tangent_collapsed(
            positions, uvs, (tuple(-2*x for x in tangent),)*3)
        assert not triangle_source_tangent_collapsed(
            positions, uvs, ((0., 0., 1.),)*3)
        assert not triangle_source_tangent_collapsed(
            positions, uvs, ((0., 0., 0.),)*3)
        assert not triangle_source_tangent_collapsed(
            positions, uvs, (tangent, (0., 0., 1.), tangent))
        assert not triangle_source_tangent_collapsed(
            positions, uvs, (tangent, tuple(-x for x in tangent), tangent))
    print("FERRARI16_PBR_PER_OPAQUE_MATERIAL_POSITIVE_NEGATIVE_PASS")


if __name__ == "__main__":
    main()
