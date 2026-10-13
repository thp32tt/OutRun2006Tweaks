#!/usr/bin/env python3
"""DX9Ex main-menu 4:3 sidebars: safe widescreen-only geometry and Reset recovery.

Static destructive controls and numerical 4:3/16:9/21:9/portrait fixtures.
This is not a Quest3/VDXR optical PASS.
"""
from pathlib import Path
from math import isfinite

src = (Path(__file__).resolve().parents[1] / "src/overlay/hooks_overlay.cpp").read_text()

def verify(code: str) -> None:
    create = code.split("void CreateLetterboxVertex()\n{", 1)[1].split("\nclass D3DHooks : public Hook", 1)[0]
    endscene = code.split("static void D3DEndScene(", 1)[1].split("if (overlayInited)", 1)[0]
    required = [
        "LetterboxVertex->Release();",
        "LetterboxVertex = nullptr;",
        "if (!d3ddev || !Game::screen_resolution)",
        "std::isfinite(sourceWidth) &&" if False else "!std::isfinite(sourceWidth)",
        "!std::isfinite(sourceHeight)",
        "sourceWidth < 1.0f || sourceHeight < 1.0f",
        "sourceHeight * (4.0f / 3.0f)",
        "sourceWidth <= contentWidth",
        "!std::isfinite(contentWidth)",
        "(sourceWidth - contentWidth) * 0.5f + 0.5f",
        "borderWidth >= sourceWidth * 0.5f",
        "FAILED(d3ddev->CreateVertexBuffer(",
        "FAILED(candidate->Lock(",
        "candidate->Release();",
        "LetterboxVertex = candidate;",
    ]
    for token in required:
        assert token in create, token
    assert create.index("sourceWidth <= contentWidth") < create.index(
        "IDirect3DVertexBuffer9* candidate")
    assert create.index("FAILED(candidate->Lock(") < create.index(
        "LetterboxVertex = candidate;")
    assert "Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0 && LetterboxVertex" in endscene
    assert "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);" in endscene

verify(src)
for w, h in ((1024,768), (1920,1080), (3440,1440), (2496,2688),
             (1280,1024), (2560,1080)):
    inner = h * (4/3)
    width = ((w - inner)*0.5+0.5) if w > inner else 0
    if w <= inner:
        assert width == 0
    else:
        assert isfinite(width) and 0 < width < w/2
        assert abs(((w+0.5-width)-width)-(inner-0.5)) < 1e-5
# The old code divided and generated negative bars in portrait mode.
assert 2496-(2688*4/3)<0
mutants = (
    ("if (!d3ddev || !Game::screen_resolution)", "if (!d3ddev)"),
    ("sourceWidth <= contentWidth", "sourceWidth < 0"),
    ("FAILED(candidate->Lock(", "SUCCEEDED(candidate->Lock("),
    ("candidate->Release();", "// leak on failed lock"),
    ("Settings::UIScalingMode > 0 && LetterboxVertex",
     "Settings::UIScalingMode > 0"),
)
for old, bad in mutants:
    assert old in src
    try:
        verify(src.replace(old,bad,1))
    except AssertionError:
        pass
    else:
        raise AssertionError("mutant survived: " + old)
print("PASS menu 4:3/16:9/21:9 sidebars, reset, failed allocations, 5 destructive controls")
