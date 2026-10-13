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
        "g_spriteVertexStream[1] = scaleY * topLeft.y + verticalCenter + 0.5;",
        "g_spriteVertexStream[8] = scaleY * bottomLeft.y + verticalCenter + 0.5;",
        "g_spriteVertexStream[0xF] = scaleY * topRight.y + verticalCenter + 0.5;",
        "g_spriteVertexStream[0x16] = scaleY * bottomRight.y + verticalCenter + 0.5;",
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
    ("g_spriteVertexStream[8] = scaleY * bottomLeft.y + verticalCenter + 0.5;",
     "g_spriteVertexStream[8] = scaleY * bottomLeft.y + 0.5;"),
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
