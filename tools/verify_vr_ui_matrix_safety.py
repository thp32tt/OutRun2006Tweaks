#!/usr/bin/env python3
"""Single-pass DX9Ex UI matrix safety invariant, with 3 distinct mutants."""
from pathlib import Path

text = (Path(__file__).resolve().parents[1] / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")


def require_safe(source: str) -> None:
    start = source.index("static int __stdcall D3DXMatrixTransformation2D_dest(")
    end = source.index("static inline SafetyHookMid draw_sprite_custom_matrix_hk", start)
    s = source[start:end]
    required = (
        "pScaling && pTranslation &&",
        "Game::screen_scale && Game::screen_resolution",
        "std::isfinite(sx) && std::isfinite(sy)",
        "sx > 1.0e-6f && sy > 1.0e-6f",
        "std::isfinite(pScaling->x)",
        "std::isfinite(pTranslation->y)",
        "std::isfinite(xScale) && std::isfinite(yScale)",
        "std::isfinite(centeredX) && std::isfinite(centeredY)",
        "std::isfinite(Game::screen_resolution->y)",
        "std::isfinite(Game::original_resolution.y)",
        "Game::original_resolution.y * scale) / 2",
    )
    for needle in required:
        if needle not in s:
            raise AssertionError(f"Missing UI matrix guard: {needle}")
    order = [
        "pScaling && pTranslation &&",
        "Game::screen_scale && Game::screen_resolution",
        "sx > 1.0e-6f && sy > 1.0e-6f",
        "pScaling->x / sx",
        "std::isfinite(centeredX) && std::isfinite(centeredY)",
        "pScaling->x = xScale;",
        "D3DXMatrixTransformation2D.stdcall<int>",
    ]
    indices = [s.index(k) for k in order]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise AssertionError("Null/finite/zero-scale checks must precede divide and writes")
    if s.count("pScaling->x = xScale;") != 1 or s.count("pTranslation->y = centeredY;") != 1:
        raise AssertionError("Non-atomic or duplicated UI transform mutation")


require_safe(text)


def require_portrait_center(code):
    sprite = code.split("static void __cdecl draw_sprite_custom_matrix_mid(", 1)[1].split(
        "// Adjust positions of sprites in 3d space", 1)[0]
    for token in (
        "!std::isfinite(Game::screen_resolution->y)",
        "!std::isfinite(Game::original_resolution.y)",
        "const float verticalCenter =",
        "Game::original_resolution.y * scaleY) / 2",
        "quad[1] = scaleY * topLeft.y + verticalCenter + 0.5;",
        "quad[8] = scaleY * bottomLeft.y + verticalCenter + 0.5;",
        "quad[0xF] = scaleY * topRight.y + verticalCenter + 0.5;",
        "quad[0x16] = scaleY * bottomRight.y + verticalCenter + 0.5;",
    ):
        if token not in sprite:
            raise AssertionError(token)


require_portrait_center(text)
for w, h, margin in ((2496, 2688, 408), (3440, 1440, 0),
                     (1920, 1440, 0)):
    s = min(w / 640, h / 480)
    assert abs((h - 480 * s) / 2 - margin) < 1e-5

mutants = (
    ("pScaling && pTranslation &&", "pScaling || pTranslation ||"),
    ("sx > 1.0e-6f && sy > 1.0e-6f", "sx >= 0.0f && sy >= 0.0f"),
    ("std::isfinite(centeredX) && std::isfinite(centeredY)",
     "std::isfinite(centeredX) || std::isfinite(centeredY)"),
)
for good, bad in mutants:
    mutant = text.replace(good, bad, 1)
    if mutant == text:
        raise AssertionError("No-op negative mutation: " + good)
    try:
        require_safe(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("Escaped regression: " + bad)
for old, bad in (
    ("Game::original_resolution.y * scale) / 2",
     "Game::original_resolution.y * scale) * 0"),
    ("Game::original_resolution.y * scaleY) / 2",
     "Game::original_resolution.y * scaleY) * 0"),
    ("quad[8] = scaleY * bottomLeft.y + verticalCenter + 0.5;",
     "quad[8] = scaleY * bottomLeft.y + 0.5;"),
):
    assert old in text
    broken = text.replace(old, bad, 1)
    try:
        require_safe(broken)
        require_portrait_center(broken)
    except AssertionError:
        pass
    else:
        raise AssertionError("Portrait Y regression not detected")
print("DX9Ex UI matrix and portrait containment PASS (6 negative controls)")

# Original multi-sprite GUI vertex streams have three independently hooked
# stride layouts: one already-scaled X/Y pair at the start of every vertex.
# Ensure the main/car-selection screen preserves its authored XY ratio, not
# just X centre placement (which stretched Y on portrait XR render targets).
def require_multi_sprite_native_aspect(source: str) -> None:
    group = source.split("static void CenterMultiSpriteQuad(", 1)[1].split(
        "static void SpriteSpacingEnable(", 1)[0]
    for needle in (
        "if (sx == sy && originalWidth * sx == width &&",
        "originalHeight * sy == height)",
        "vertices[i * stride]",
        "vertices[i * stride + 1]",
        "transformedX[i] = CenterMultiSpriteAxis(",
        "x, sx, contain, width, originalWidth);",
        "transformedY[i] = CenterMultiSpriteAxis(",
        "y, sy, contain, height, originalHeight);",
        "vertices[i * stride] = transformedX[i];",
        "vertices[i * stride + 1] = transformedY[i];",
        "if (!std::isfinite(transformedX[i]) ||",
        "!std::isfinite(transformedY[i]))",
        "mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade",
        "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.ecx), 9);",
        "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.esp + 0x80), 11);",
        "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.edx), 13);",
    ):
        if needle not in group:
            raise AssertionError("multi-sprite XY aspect: " + needle)
    # All four corners must be checked before any output vertex is touched.
    assert group.index("if (!std::isfinite(transformedX[i]) ||") < group.index(
        "vertices[i * stride] = transformedX[i];"
    )
    # Every stride owner must independently protect the same two UI modes;
    # finding one surviving guard must not hide mutation of another hook.
    assert group.count("mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade") == 3
    assert group.count("CenterMultiSpriteQuad(reinterpret_cast<float*>") == 3


require_multi_sprite_native_aspect(text)

def axis(pixel, axis_scale, contain, extent, authored_extent):
    return pixel / axis_scale * contain + (extent - authored_extent * contain) / 2.0

# Width/height-independent containment for full native 640x480 4:3 quads.
# 16:9 and 21:9 remain unchanged in Y, while 2496x2688 must letterbox Y
# rather than stretch an authored rectangle to the portrait eye height.
for width, height in ((1280, 960), (1920, 1080),
                      (2560, 1080), (2496, 2688)):
    sx, sy = width / 640, height / 480
    contain = min(sx, sy)
    x0 = axis(0, sx, contain, width, 640)
    x1 = axis(width, sx, contain, width, 640)
    y0 = axis(0, sy, contain, height, 480)
    y1 = axis(height, sy, contain, height, 480)
    assert abs((x1-x0)/(y1-y0) - 640/480) < 1e-6
    assert abs((x0+x1)/2 - width/2) < 1e-6
    assert abs((y0+y1)/2 - height/2) < 1e-6
assert axis(0, 5.6, 3.9, 2688, 480) == 408
assert axis(2688, 5.6, 3.9, 2688, 480) == 2280

for good, bad in (
    ("if (sx == sy && originalWidth * sx == width &&",
     "if (sx == sy && originalWidth * sx != width &&"),
    ("originalHeight * sy == height)",
     "originalHeight * sy != height)"),
    ("vertices[i * stride + 1] = transformedY[i];",
     "vertices[i * stride + 1] = vertices[i * stride + 1];"),
    ("y, sy, contain, height, originalHeight);",
     "y, sx, contain, height, originalHeight);"),
    ("CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.ecx), 9);",
     "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.ecx), 11);"),
    ("CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.esp + 0x80), 11);",
     "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.esp + 0x80), 9);"),
    ("CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.edx), 13);",
     "CenterMultiSpriteQuad(reinterpret_cast<float*>(ctx.edx), 9);"),
    ("mode == ScalingMode::KeepCentered || mode == ScalingMode::OnlineArcade",
     "mode == ScalingMode::Vanilla || mode == ScalingMode::OnlineArcade"),
    ("!std::isfinite(transformedY[i]))",
     "false)"),
):
    assert good in text, "mutation source anchor missing: " + good
    before, group = text.split("static void CenterMultiSpriteQuad(", 1)
    mutant = before + "static void CenterMultiSpriteQuad(" + group.replace(good, bad, 1)
    try:
        require_multi_sprite_native_aspect(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("undetected multi-sprite XY regression: " + bad)

# Zero-work path must cover exact native 4:3 and proportional 16:9 sources
# with a uniform authored coordinate scale; any rounded/anisotropic target
# still requires geometry normalization.
def exact_native_identity(sx, sy, src_width, src_height, width, height):
    return sx == sy and src_width * sx == width and src_height * sy == height

assert exact_native_identity(2.0, 2.0, 640, 480, 1280, 960)
assert exact_native_identity(1.0, 1.0, 640, 480, 640, 480)
assert not exact_native_identity(3.0, 2.25, 640, 480, 1920, 1080)
assert not exact_native_identity(3.9, 5.6, 640, 480, 2496, 2688)
assert not exact_native_identity(2.0, 2.0, 640, 480, 1280, 961)
assert not exact_native_identity(2.0, 2.0, 640, 480, 1279, 960)

print("DX9Ex menu multi-sprite native XY aspect PASS (9 negative controls, native fastpath)")


# The custom-matrix/menu path must never submit a half-mutated global quad
# when a device reset or malformed sprite matrix yields a bad vertex.
def require_atomic_custom_matrix(source: str) -> None:
    body = source.split("static void __cdecl draw_sprite_custom_matrix_mid(", 1)[1].split(
        "// Adjust positions of sprites in 3d space", 1)[0]
    for required in (
        "std::array<float, 28> quad{};",
        "if (!device)",
        "FAILED(descHr) || v25.Width == 0 || v25.Height == 0",
        "const std::size_t base = i * 7;",
        "!std::isfinite(quad[base])",
        "!std::isfinite(quad[base + 1]) ||",
        "!std::isfinite(quad[base + 2])",
        "!std::isfinite(quad[base + 5])",
        "!std::isfinite(quad[base + 6]))",
        "std::copy(quad.begin(), quad.end(), g_spriteVertexStream);",
        "device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2u, g_spriteVertexStream, 0x1Cu);",
    ):
        if required not in body:
            raise AssertionError("custom matrix atomic quad missing: " + required)
    assert "g_spriteVertexStream[" not in body
    assert body.index("FAILED(descHr)") < body.index("std::array<float, 28> quad{};")
    assert body.index("const std::size_t base = i * 7;") < body.index(
        "std::copy(quad.begin(), quad.end(), g_spriteVertexStream);")
    assert body.index("std::copy(quad.begin(), quad.end(), g_spriteVertexStream);") < body.index(
        "device->DrawPrimitiveUP(")
    assert body.count("quad[") >= 28

require_atomic_custom_matrix(text)
for good, bad in (
    ("std::copy(quad.begin(), quad.end(), g_spriteVertexStream);",
     "std::copy(quad.begin(), quad.begin(), g_spriteVertexStream);"),
    ("!std::isfinite(quad[base + 1])",
     "!std::isfinite(quad[base + 1]) && false"),
    ("!std::isfinite(quad[base + 6])",
     "!std::isfinite(quad[base + 6]) && false"),
    ("std::array<float, 28> quad{};",
     "std::array<float, 27> quad{};"),
):
    assert good in text
    try:
        require_atomic_custom_matrix(text.replace(good, bad, 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("unsafe custom matrix mutation escaped: " + bad)
print("DX9Ex custom matrix complete quad publishing PASS (4 negative controls)")
