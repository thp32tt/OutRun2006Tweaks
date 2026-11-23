#!/usr/bin/env python3
"""Positive/negative regression: reject orphan and incomplete PBR maps."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "ferrari16"))
from pbr_material_gate import (  # noqa: E402
    uncovered_pbr_materials, pbr_opaque_coverage_ok, triangle_uv_basis)


def main() -> None:
    # Two opaque materials, one tagged glass material (not PBR-required).
    assert pbr_opaque_coverage_ok(4, {0, 1}, {0, 1}, {0, 1}, {0, 1})
    assert pbr_opaque_coverage_ok(4, {0}, {0}, {0}, {0})
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
        "unsupported_version": [], "no_opaque_materials": []}
    assert triangle_uv_basis((0., 0.), (1., 0.), (0., 1.))
    assert triangle_uv_basis((0., 0.), (0., 1.), (1., 0.))  # mirrored UV
    assert not triangle_uv_basis((0., 0.), (0., 0.), (0., 0.))
    assert not triangle_uv_basis((0., 0.), (1e-5, 0.), (0., 1e-5))
    print("FERRARI16_PBR_PER_OPAQUE_MATERIAL_POSITIVE_NEGATIVE_PASS")


if __name__ == "__main__":
    main()
