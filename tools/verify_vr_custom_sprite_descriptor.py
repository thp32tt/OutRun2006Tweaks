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
        "float scaleY = screenScaleY;",
        "scaleY = min(screenScaleX, screenScaleY);",
        "Game::D3DDevice()->DrawPrimitiveUP",
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
        "Game::D3DDevice()->DrawPrimitiveUP",
    )]
    if ordering != sorted(ordering) or len(set(ordering)) != len(ordering):
        raise AssertionError("Texture/scale guards must precede UV writes and draw")
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
print("DX9Ex custom sprite descriptor/reset invariant: PASS (4 distinct negative mutations)")
