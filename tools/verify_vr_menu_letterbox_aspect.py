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

# A frontend resize can update the source aspect without the game's
# temporary-resource callbacks. The old vertex buffer must never be reused.
def verify_live_resize(source: str) -> None:
    create = source.split("void CreateLetterboxVertex()\n{", 1)[1].split(
        "\nclass D3DHooks : public Hook", 1)[0]
    endscene = source.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    release = source.split("static void D3DTemporariesRelease(", 1)[1].split(
        "static void D3DTemporariesCreate(", 1)[0]
    for token in ("LetterboxRasterDevice = nullptr;",
                  "LetterboxRasterWidth = 0.0f;",
                  "LetterboxRasterHeight = 0.0f;",
                  "LetterboxRasterDevice = d3ddev;",
                  "LetterboxRasterWidth = sourceWidth;",
                  "LetterboxRasterHeight = sourceHeight;"):
        assert token in create, token
    assert create.index("LetterboxRasterDevice = d3ddev;") < create.index(
        "if (sourceWidth <= contentWidth)")
    for token in ("validSource &&",
                  "currentDevice != LetterboxRasterDevice",
                  "currentSize->x != LetterboxRasterWidth",
                  "currentSize->y != LetterboxRasterHeight",
                  "CreateLetterboxVertex();",
                  "currentDevice == LetterboxRasterDevice",
                  "currentSize->x == LetterboxRasterWidth",
                  "currentSize->y == LetterboxRasterHeight"):
        assert token in endscene, token
    assert endscene.index("CreateLetterboxVertex();") < endscene.index(
        "if (Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0 && LetterboxVertex")
    assert "std::isfinite(currentSize->x)" in endscene
    assert "std::isfinite(currentSize->y)" in endscene
    assert "currentSize->x >= 1.0f && currentSize->y >= 1.0f" in endscene
    for token in ("LetterboxVertex->Release();",
                  "LetterboxRasterDevice = nullptr;",
                  "LetterboxRasterWidth = 0.0f;",
                  "LetterboxRasterHeight = 0.0f;"):
        assert token in release, token

verify_live_resize(src)

def should_rebuild(cached, next_size, enabled=True, menu=True):
    if not enabled or not menu:
        return False
    device, w, h = next_size
    if not device or not isfinite(w) or not isfinite(h) or w < 1 or h < 1:
        return False
    return cached != next_size

for seq in (
        ((1, 3440, 1440), (1, 1024, 768), (1, 1920, 1080)),
        ((1, 1920, 1080), (1, 2496, 2688), (1, 3440, 1440)),
        ((1, 1024, 768), (2, 1024, 768), (2, 2560, 1080))):
    cached = (None, 0, 0)
    for next_size in seq:
        assert should_rebuild(cached, next_size)
        cached = next_size
        assert not should_rebuild(cached, next_size)
        assert not should_rebuild(cached, next_size, menu=False)
    for invalid in ((1, float("nan"), 1440),
                    (1, 3440, float("inf")), (1, 0, 768)):
        assert not should_rebuild(cached, invalid)
assert should_rebuild((1, 3440, 1440), (1, 2496, 2688))
# Switching from widescreen to portrait must retire prior bars rather
# than rendering a stale 21:9 left/right cover.
assert shell_rect(3440, 1440, 1, 1, False)[0] > 0
assert shell_rect(2496, 2688, 1, 1, False)[0] == 0
for good, bad in (
        ("currentSize->x != LetterboxRasterWidth", "currentSize->x == LetterboxRasterWidth"),
        ("currentSize->y != LetterboxRasterHeight", "currentSize->y == LetterboxRasterHeight"),
        ("currentDevice != LetterboxRasterDevice", "currentDevice == LetterboxRasterDevice"),
        ("currentSize->x == LetterboxRasterWidth", "currentSize->x != LetterboxRasterWidth"),
        ("std::isfinite(currentSize->y)", "std::isnan(currentSize->y)"),
        ("LetterboxRasterHeight = 0.0f;", "// stale height on reset"),
):
    assert good in src
    if good == "LetterboxRasterHeight = 0.0f;":
        # The same assignment appears at file scope and in Create() as
        # well as Reset(). Mutate the Reset owner ONLY; changing a global
        # declaration while leaving Reset intact was a false negative.
        reset_at = src.index("static void D3DTemporariesRelease(")
        reset_end = src.index("static void D3DTemporariesCreate(", reset_at)
        reset_body = src[reset_at:reset_end]
        assert reset_body.count(good) == 1
        mutant = (src[:reset_at] +
                  reset_body.replace(good, bad, 1) +
                  src[reset_end:])
    else:
        mutant = src.replace(good, bad, 1)
    try:
        verify_live_resize(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("live-resize contract mutant survived: " + good)
print("PASS live menu 4:3/16:9/21:9/portrait resize, invalid source and 6 destructive mutants")

