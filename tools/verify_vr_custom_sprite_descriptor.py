#!/usr/bin/env python3
"""Bounded HUD custom sprite texture descriptor/reset admissibility, 4 faults.

The source contract verifies only the exact custom-matrix midhook. It does
not classify any HUD sprite, perturb good-path transforms or loop 1000x.
"""
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")


def check(s: str) -> None:
    first = s.index("static void __cdecl draw_sprite_custom_matrix_mid(")
    last = s.index("static inline SafetyHookInline Calc3D2D_hk", first)
    mid = s[first:last]
    markers = [
        "!g_spriteVertexStream || !a1 || !a1->d3dtexture_ptr_C",
        "!Game::screen_scale",
        "std::isfinite(screenScaleX)",
        "std::isfinite(screenScaleY)",
        "screenScaleX <= 0.0f || screenScaleY <= 0.0f",
        "!Game::screen_resolution",
        "D3DSURFACE_DESC v25{};",
        "const HRESULT descHr =",
        "a1->d3dtexture_ptr_C->GetLevelDesc(0, &v25);",
        "FAILED(descHr) || v25.Width == 0 || v25.Height == 0",
        "0.50999999 / (double)v25.Width",
        "0.50999999 / (double)v25.Height",
        "const auto quadMap = precontained",
        ": OutRunVrMenuQuad::BuildPixelMap(",
        "precontained = contained && frontEnd &&",
        "OutRunVrMenuQuad::ContainedMatrices.Contains(",
        "? OutRunVrMenuQuad::PixelMap{1.f, 1.f, 0.f, 0.f, true}",
        "if (!quadMap.valid)",
        "quad[1] = OutRunVrMenuQuad::ProjectY(quadMap, topLeft.y);",
        "quad[8] = OutRunVrMenuQuad::ProjectY(quadMap, bottomLeft.y);",
        "quad[0xF] = OutRunVrMenuQuad::ProjectY(quadMap, topRight.y);",
        "quad[0x16] = OutRunVrMenuQuad::ProjectY(quadMap, bottomRight.y);",
        "quad[0] = OutRunVrMenuQuad::ProjectX(quadMap, topLeft.x);",
        "quad[7] = OutRunVrMenuQuad::ProjectX(quadMap, bottomLeft.x);",
        "quad[0xE] = OutRunVrMenuQuad::ProjectX(quadMap, topRight.x);",
        "quad[0x15] = OutRunVrMenuQuad::ProjectX(quadMap, bottomRight.x);",
        "auto* device = Game::D3DDevice();",
        "if (!device)",
        "std::copy(quad.begin(), quad.end(), g_spriteVertexStream);",
        "device->DrawPrimitiveUP",
    ]
    for marker in markers:
        if marker not in mid:
            raise AssertionError(f"Custom sprite texture guard missing: {marker}")
    ordering = [mid.index(m) for m in (
        "!g_spriteVertexStream || !a1 || !a1->d3dtexture_ptr_C",
        "std::isfinite(screenScaleX)",
        "a1->d3dtexture_ptr_C->GetLevelDesc(0, &v25);",
        "FAILED(descHr) || v25.Width == 0 || v25.Height == 0",
        "0.50999999 / (double)v25.Width",
        "device->DrawPrimitiveUP",
    )]
    if ordering != sorted(ordering) or len(set(ordering)) != len(ordering):
        raise AssertionError("Texture/scale guards must precede UV writes and draw")
    if mid.index("if (!device)") >= mid.index("device->DrawPrimitiveUP") or \
            mid.index("std::copy(quad.begin(), quad.end(), g_spriteVertexStream);") >= mid.index("device->DrawPrimitiveUP"):
        raise AssertionError("Device guard and complete quad publication must precede DrawPrimitiveUP")
    if not (mid.index("FAILED(descHr) || v25.Width == 0 || v25.Height == 0") <
            mid.index("const auto quadMap = precontained") <
            mid.index("if (!quadMap.valid)") <
            mid.index("quad[1] = OutRunVrMenuQuad::ProjectY(") <
            mid.index("std::copy(quad.begin(), quad.end(), g_spriteVertexStream);")):
        raise AssertionError("Descriptor and viewport map must be validated before publishing quad")
    if mid.index("OutRunVrMenuQuad::ContainedMatrices.Contains(") >= mid.index("const auto quadMap = precontained") or \
       mid.index(": OutRunVrMenuQuad::BuildPixelMap(") >= mid.index("if (!quadMap.valid)"):
        raise AssertionError("Unproven native quad must retain physical viewport mapping")
    if mid.count("D3DSURFACE_DESC v25{};") != 1 or mid.count("GetLevelDesc(0, &v25)") != 1:
        raise AssertionError("Uninitialized or duplicate texture descriptor query")
    if "float scaleY = Game::screen_scale->y;" in mid:
        raise AssertionError("Unlatched resolution scale in custom matrix draw")


check(source)
mutants = [
    ("!g_spriteVertexStream || !a1 || !a1->d3dtexture_ptr_C",
     "!g_spriteVertexStream || !a1 && !a1->d3dtexture_ptr_C"),
    ("screenScaleX <= 0.0f || screenScaleY <= 0.0f",
     "screenScaleX < 0.0f && screenScaleY < 0.0f"),
    ("FAILED(descHr) || v25.Width == 0 || v25.Height == 0",
     "FAILED(descHr) && v25.Width == 0 && v25.Height == 0"),
    ("D3DSURFACE_DESC v25{};", "D3DSURFACE_DESC v25;"),
    ("if (!quadMap.valid)", "if (quadMap.valid)"),
    ("quad[0x16] = OutRunVrMenuQuad::ProjectY(quadMap, bottomRight.y);",
     "quad[0x16] = bottomRight.y + 0.5f;"),
    ("precontained = contained && frontEnd &&",
     "precontained = true &&"),
    (": OutRunVrMenuQuad::BuildPixelMap(",
     ": OutRunVrMenuQuad::PixelMap{1.f,1.f,0.f,0.f,true}("),
    ("? OutRunVrMenuQuad::PixelMap{1.f, 1.f, 0.f, 0.f, true}",
     "? OutRunVrMenuQuad::PixelMap{0.5f, 1.f, 0.f, 0.f, true}"),
]
for good, bad in mutants:
    corrupt = source.replace(good, bad, 1)
    if corrupt == source:
        raise AssertionError(f"Negative mutation was a no-op: {good}")
    try:
        check(corrupt)
    except AssertionError:
        pass
    else:
        raise AssertionError(f"Unsafe sprite path escaped verifier: {bad}")
print("DX9Ex custom sprite descriptor/reset invariant: PASS (9 distinct negative mutations)")
