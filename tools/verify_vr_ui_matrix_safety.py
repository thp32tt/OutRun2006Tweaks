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
print("DX9Ex UI matrix optional inputs and finite-scale: PASS (3 negative controls)")
