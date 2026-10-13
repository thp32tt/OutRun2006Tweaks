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

# The ImGui F11 shell must share the GPU bars' enablement and rect, instead
# of using a different letterboxing mode or producing negative portrait bars.
overlay = (Path(__file__).resolve().parents[1] / "src/overlay/overlay.cpp").read_text()

def verify_shell_rect(code: str) -> None:
    shell = code.split("Overlay::ContentRect Overlay::content_rect()", 1)[1].split(
        "const std::vector<OverlayWindow*>& Overlay::windows()", 1)[0]
    gate = [
        "!std::isfinite(screen.x)", "!std::isfinite(screen.y)",
        "screen.x <= 0.f || screen.y <= 0.f",
        "Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0",
        "(Settings::UILetterboxing == 2 || !Game::is_in_game())",
        "screen.y * (4.f / 3.f)",
        "std::isfinite(contentWidth) && screen.x > contentWidth",
        "(screen.x - contentWidth) * 0.5f + 0.5f",
        "std::isfinite(candidate) && candidate < screen.x * 0.5f",
        "screen.x - (border * 2.f)",
    ]
    for marker in gate:
        assert marker in shell, marker
    assert shell.index("screen.x <= 0.f") < shell.index("float border = 0.f;")
    assert shell.index("screen.x > contentWidth") < shell.index("border = candidate;")
    # The UI and GPU need exactly the same mode-2 / gameplay decision.
    gpu = src.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    assert "Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0 && LetterboxVertex" in gpu
    assert "Settings::UILetterboxing == 2" in gpu
    assert "!Game::is_in_game()" in gpu

verify_shell_rect(overlay)

def shell_rect(w, h, letterbox, ui_scaling, gameplay):
    if not isfinite(w) or not isfinite(h) or w <= 0 or h <= 0:
        return 0, 0
    enabled = letterbox > 0 and ui_scaling > 0 and (letterbox == 2 or not gameplay)
    content = h * (4/3)
    border = (w - content)*0.5+0.5 if enabled and w > content else 0
    return border, w - 2*border

for w, h in ((1024,768), (1920,1080), (3440,1440), (2496,2688),
             (1280,1024), (2560,1080)):
    for letterbox in (0, 1, 2):
        for ui_scaling in (0, 1):
            for gameplay in (False, True):
                border, inner = shell_rect(w,h,letterbox,ui_scaling,gameplay)
                draw_bars = letterbox > 0 and ui_scaling > 0 and (
                    letterbox == 2 or not gameplay) and w > h*(4/3)
                assert (border > 0) == draw_bars
                assert 0 <= border < w/2 and 0 < inner <= w
                if draw_bars:
                    assert abs(inner - (h*(4/3)-1)) < 1e-4
                else:
                    assert inner == w
for size in ((0,768), (1920,0), (float("nan"),768), (1920,float("inf"))):
    assert shell_rect(*size, 2, 1, False) == (0,0)

for old, bad in (
    ("Settings::UILetterboxing > 0", "Settings::UILetterboxing == 1"),
    ("Settings::UIScalingMode > 0", "Settings::UIScalingMode < 0"),
    ("Settings::UILetterboxing == 2 || !Game::is_in_game()",
     "Settings::UILetterboxing == 1 && !Game::is_in_game()"),
    ("screen.x > contentWidth", "screen.x < contentWidth"),
    ("std::isfinite(candidate) && candidate < screen.x * 0.5f",
     "std::isfinite(candidate)"),
    ("screen.x <= 0.f || screen.y <= 0.f",
     "screen.x < 0.f || screen.y < 0.f"),
):
    assert old in overlay, old
    try:
        verify_shell_rect(overlay.replace(old, bad, 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("F11 content-rect mutant survived: " + old)

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
print("PASS menu/F11 letterbox shared rect, portrait/reset/mode-2, 11 destructive controls")
