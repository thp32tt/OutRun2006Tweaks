#!/usr/bin/env python3
"""Portable, read-only per-opaque-material PBR/UV preflight for OVC3/4.

The normal map is sampled only if its opaque mesh material owns it and a
triangle has a usable UV derivative basis. A normal/ORM map attached to some
other material is not evidence of PBR coverage for that body material.
"""
from __future__ import annotations
from collections.abc import Iterable


def uncovered_pbr_materials(version: int, opaque: Iterable[int],
                            normal: Iterable[int], orm: Iterable[int],
                            usable_uv: Iterable[int],
                            invalid_uv: Iterable[int] = (),
                            incomplete_mips: Iterable[int] = ()) -> dict[str, list[int]]:
    """Return failed coverage categories, without claiming visual quality."""
    used = set(opaque)
    n, o, uv = set(normal), set(orm), set(usable_uv)
    return {
        "no_normal": sorted(used - n),
        "no_orm": sorted(used - o),
        "degenerate_uv": sorted(used - uv),
        "partially_degenerate_uv": sorted(used & set(invalid_uv)),
        "incomplete_pbr_mips": sorted(used & set(incomplete_mips)),
        "unsupported_version": sorted(used) if version < 3 else [],
        "no_opaque_materials": [0] if not used else [],
    }


def pbr_opaque_coverage_ok(version: int, opaque: Iterable[int],
                           normal: Iterable[int], orm: Iterable[int],
                           usable_uv: Iterable[int],
                           invalid_uv: Iterable[int] = (),
                           incomplete_mips: Iterable[int] = ()) -> bool:
    return not any(uncovered_pbr_materials(
        version, opaque, normal, orm, usable_uv,
        invalid_uv, incomplete_mips).values())


def triangle_uv_basis(u0: tuple[float, float], u1: tuple[float, float],
                      u2: tuple[float, float]) -> bool:
    # Match the SM3 normal-map shader's 1e-7 TBN determinant threshold.
    a, b = u1[0] - u0[0], u1[1] - u0[1]
    c, d = u2[0] - u0[0], u2[1] - u0[1]
    return abs(a * d - b * c) > 1.0e-7


def triangle_has_pbr_basis(p0: tuple[float, float, float],
                           p1: tuple[float, float, float],
                           p2: tuple[float, float, float],
                           u0: tuple[float, float],
                           u1: tuple[float, float],
                           u2: tuple[float, float]) -> bool:
    # PBR derivative TBN also needs non-degenerate world-space geometry.
    # Match the native geometric normal repair's squared cross threshold.
    ax, ay, az = (p1[i] - p0[i] for i in range(3))
    bx, by, bz = (p2[i] - p0[i] for i in range(3))
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    return ((nx * nx + ny * ny + nz * nz) > 1.e-24 and
            triangle_uv_basis(u0, u1, u2))
