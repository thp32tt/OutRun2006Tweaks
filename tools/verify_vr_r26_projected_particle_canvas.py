#!/usr/bin/env python3
"""R26 CPU-projected world particles keep the retail game-screen source canvas."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(
    encoding="utf-8")
GAME = (ROOT / "src/game_addrs.hpp").read_text(encoding="utf-8")

assert "screen_resolution = Module::exe_ptr<D3DXVECTOR2>(0x340C8C);" in GAME

for token in (
    "bool gameProjectedWorldSourceCanvas = false;",
    "float gameProjectedWorldCenterX = 0.0f;",
    "float gameProjectedWorldCenterY = 0.0f;",
    "state.worldEffect && state.rhwDepthEvidence &&",
    "!state.projectedWorldMarker && Game::screen_resolution",
    "state.gameProjectedWorldCenterX = gameCenterX;",
    "state.gameProjectedWorldCenterY = gameCenterY;",
    "VR TRACE WORLD PROJECTED SOURCE:",
    "sourceScaleX = 1.0f / state.gameProjectedWorldCenterX;",
    "sourceScaleY = -1.0f / state.gameProjectedWorldCenterY;",
    "x * sourceScaleX + sourceBiasX",
    "y * sourceScaleY + sourceBiasY",
    "GAME_PROJECTED_WORLD_740C8C_90",
    "const bool unitRhwSource =",
    "std::fabs(rhw - 1.0f) <= 0.02f;",
    "const float zDenominator =",
    "actualNdcZ * bp._34 - bp._33;",
    "screenZViewZ =",
    "(bp._43 - actualNdcZ * bp._44) /",
    "screenZViewZ * bp._34 + bp._44;",
    "usedScreenZOnlyDepth = true;",
    "VR TRACE WORLD SCREENZ REPROJECT:",
):
    assert token in SRC, token

configure = SRC[SRC.index("bool R30ConfigureXyzrhwWorldEffect("):
                SRC.index("UINT R30PrimitiveElementCount(")]
assert configure.index("state.worldEffect && state.rhwDepthEvidence") < configure.index(
    "state.gameProjectedWorldSourceCanvas = true;")
assert "state.logicalUiSourceCanvas = true" not in configure

transform = SRC[SRC.index("bool R30TransformXyzrhwVertices("):
                SRC.index("bool R30TransformXyzrhwStereo(")]
assert transform.count("x * sourceScaleX + sourceBiasX") >= 2
assert transform.count("y * sourceScaleY + sourceBiasY") >= 2
assert "const float transformedX =\n                        x0 + (fullX + 1.0f) * 0.5f * width;" in transform
assert "const float transformedY =\n                        y0 + (1.0f - fullY) * 0.5f * height;" in transform

def game_ndc(x, y, gx, gy):
    return x / gx - 1.0, 1.0 - y / gy

def physical_ndc(x, y, x0, y0, width, height):
    return ((x - x0) / width) * 2.0 - 1.0, 1.0 - ((y - y0) / height) * 2.0

for gx, gy in ((640.0, 480.0), (1920.0, 1080.0), (3440.0, 1440.0)):
    assert game_ndc(gx, gy, gx, gy) == (0.0, 0.0)
    assert game_ndc(0.0, 0.0, gx, gy) == (-1.0, 1.0)
    assert game_ndc(2.0 * gx, 2.0 * gy, gx, gy) == (1.0, -1.0)
    for x, y in ((0.0, 0.0), (gx, gy), (2.0*gx, 2.0*gy),
                 (0.37*gx, 1.62*gy)):
        a = game_ndc(x, y, gx, gy)
        b = physical_ndc(x, y, 0.0, 0.0, 2.0*gx, 2.0*gy)
        assert math.isclose(a[0], b[0], abs_tol=1e-12)
        assert math.isclose(a[1], b[1], abs_tol=1e-12)

def view_z_from_screen_z(ndc_z, m33, m34, m43, m44):
    denom = ndc_z * m34 - m33
    return (m43 - ndc_z * m44) / denom

m33, m34, m43, m44 = 1.00002, 1.0, -0.100002, 0.0
z_nearish = view_z_from_screen_z(0.90, m33, m34, m43, m44)
z_farther = view_z_from_screen_z(0.99, m33, m34, m43, m44)
assert math.isfinite(z_nearish) and math.isfinite(z_farther)
assert abs(z_farther) > abs(z_nearish)
assert not math.isclose(z_nearish, z_farther)

gx, gy = 1920.0, 1080.0
xr_w, xr_h = 2496.0, 2688.0
assert game_ndc(gx, gy, gx, gy) == (0.0, 0.0)
old = physical_ndc(gx, gy, 0.0, 0.0, xr_w, xr_h)
assert abs(old[0]) > 0.1 or abs(old[1]) > 0.1

for good, bad in (
    ("state.worldEffect && state.rhwDepthEvidence &&",
     "state.worldEffect && false &&"),
    ("sourceScaleX = 1.0f / state.gameProjectedWorldCenterX;",
     "sourceScaleX = 2.0f / width;"),
    ("sourceScaleY = -1.0f / state.gameProjectedWorldCenterY;",
     "sourceScaleY = -2.0f / height;"),
    ("!state.projectedWorldMarker && Game::screen_resolution",
     "Game::screen_resolution"),
    ("std::fabs(rhw - 1.0f) <= 0.02f;",
     "false;"),
    ("actualNdcZ * bp._34 - bp._33;",
     "bp._34 - bp._33;"),
    ("screenZViewZ * bp._34 + bp._44;",
     "1.0f / rhw;"),
):
    assert good in SRC
    damaged = SRC.replace(good, bad, 1)
    assert damaged != SRC and damaged.count(good) < SRC.count(good)

print("PASS R26 retail 418CF0 game-screen + RHW=1 screen-Z depth -> world stereo -> physical XR output contract; HMD UNTESTED")
