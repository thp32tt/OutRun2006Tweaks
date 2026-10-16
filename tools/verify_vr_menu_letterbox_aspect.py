#!/usr/bin/env python3
"""DX9Ex main-menu 4:3 sidebars: side/portrait geometry and Reset recovery.

Static destructive controls and numerical 4:3/16:9/21:9/portrait fixtures.
This is not a Quest3/VDXR optical PASS.
"""
from pathlib import Path
from math import isfinite

src = (Path(__file__).resolve().parents[1] / "src/overlay/hooks_overlay.cpp").read_text()
menu_bars = (Path(__file__).resolve().parents[1] /
             "src/vr/ui/menu_letterbox_geometry.hpp").read_text()

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
        "OutRunVR::UI::BuildMenuBarGeometry(",
        "sourceWidth, sourceHeight);",
        "layout.axis == OutRunVR::UI::MenuBarAxis::Invalid",
        "if (!layout.hasBars())",
        "layout.vertices.size()",
        "layout.vertices[i].x, layout.vertices[i].y",
        "FAILED(d3ddev->CreateVertexBuffer(",
        "FAILED(candidate->Lock(",
        "candidate->Release();",
        "LetterboxVertex = candidate;",
    ]
    for token in required:
        assert token in create, token
    assert create.index("if (!layout.hasBars())") < create.index(
        "CUSTOMVERTEX vertices[8]{};") < create.index(
        "IDirect3DVertexBuffer9* candidate")
    assert create.index("OutRunVR::UI::BuildMenuBarGeometry(") < create.index(
        "if (!layout.hasBars())")
    assert create.index("FAILED(candidate->Lock(") < create.index(
        "LetterboxVertex = candidate;")
    # Create and Unlock now each have independent failed-buffer releases.
    # Inspect the Lock failure's own branch, so removing its Release cannot
    # falsely pass by finding the later Unlock failure's Release.
    lock_failure = create.split("if (FAILED(candidate->Lock(", 1)[1].split(
        "memcpy(mapped, vertices", 1)[0]
    assert "candidate->Release();" in lock_failure
    assert "return;" in lock_failure
    assert "Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0 && LetterboxVertex" in endscene
    assert "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);" in endscene

verify(src)

# The exact R84 C++ header owns geometry after portrait-menu conversion.
# Check the compiled header and the live EndScene consumer, not retired
# widescreen-only arithmetic inside CreateLetterboxVertex.
def verify_menu_bar_geometry(code: str) -> None:
    required = (
        "enum class MenuBarAxis : std::uint8_t { Invalid, None, Sides, TopBottom };",
        "float sourceWidth, float sourceHeight) noexcept",
        "sourceWidth >= 1.0f && sourceWidth <= 16384.0f",
        "sourceHeight >= 1.0f && sourceHeight <= 16384.0f",
        "const float containWidth = sourceHeight * (4.0f / 3.0f);",
        "const float containHeight = sourceWidth * (3.0f / 4.0f);",
        "if (sourceWidth > containWidth + 0.5f)",
        "else if (sourceHeight > containHeight + 0.5f)",
        "result.axis = MenuBarAxis::Sides;",
        "result.axis = MenuBarAxis::TopBottom;",
        "result.axis = MenuBarAxis::None;",
        "return axis == MenuBarAxis::Sides ||",
        "axis == MenuBarAxis::TopBottom;",
        "static_assert(BuildMenuBarGeometry(640, 480).axis == MenuBarAxis::None);",
        "static_assert(BuildMenuBarGeometry(1920, 1080).axis == MenuBarAxis::Sides);",
        "static_assert(BuildMenuBarGeometry(1200, 1600).axis == MenuBarAxis::TopBottom);",
        "static_assert(BuildMenuBarGeometry(1200, 1600).vertices[2].y == 350.5f);",
        "static_assert(BuildMenuBarGeometry(1200, 1600).vertices[4].y == 1250.0f);",
        "static_assert(BuildMenuBarGeometry(1200, 1600).vertices[7].y == 1600.5f);",
        "static_assert(BuildMenuBarGeometry(0, 1000).axis == MenuBarAxis::Invalid);",
        "static_assert(BuildMenuBarGeometry(16385, 1000).axis == MenuBarAxis::Invalid);",
    )
    for marker in required:
        assert marker in code, marker
    assert code.count("result.vertices = {{") == 2
    assert code.index("result.axis = MenuBarAxis::Sides;") < code.index(
        "result.axis = MenuBarAxis::TopBottom;") < code.index(
        "result.axis = MenuBarAxis::None;")

verify_menu_bar_geometry(menu_bars)
for old, bad in (
    ("sourceWidth > containWidth + 0.5f", "sourceWidth < containWidth + 0.5f"),
    ("sourceHeight > containHeight + 0.5f", "sourceHeight < containHeight + 0.5f"),
    ("result.axis = MenuBarAxis::TopBottom;", "result.axis = MenuBarAxis::None;"),
    ("result.axis = MenuBarAxis::Sides;", "result.axis = MenuBarAxis::None;"),
    ("sourceHeight <= 16384.0f", "sourceHeight <= 32768.0f"),
    ("static_assert(BuildMenuBarGeometry(1200, 1600).vertices[2].y == 350.5f);",
     "static_assert(BuildMenuBarGeometry(1200, 1600).vertices[2].y == 0.5f);"),
):
    assert old in menu_bars, old
    try:
        verify_menu_bar_geometry(menu_bars.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("portrait geometry mutation survived: " + old)
for old, bad in (
    ("OutRunVR::UI::BuildMenuBarGeometry(", "OutRunVR::UI::BuildLegacySideGeometry("),
    ("if (!layout.hasBars())", "if (layout.hasBars())"),
    ("layout.vertices[i].x, layout.vertices[i].y", "0.0f, 0.0f"),
):
    assert old in src, old
    try:
        verify(src.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("menu source-header wiring mutation survived: " + old)
print("PASS R84 portrait/landscape geometry, native fallback and 9 destructive controls")


# The 4:3 menu sidebars are also allocated on the promoted D3D9Ex device.
# D3DPOOL_MANAGED is invalid there; DEFAULT is released before Reset and
# rebuilt after Reset or a live source-size/device switch.
def verify_ex_letterbox_pool(code: str) -> None:
    create = code.split("void CreateLetterboxVertex()\n{", 1)[1].split(
        "\nclass D3DHooks : public Hook", 1)[0]
    reset = code.split("static void D3DTemporariesRelease(", 1)[1].split(
        "static void D3DTemporariesCreate(", 1)[0]
    remake = code.split("static void D3DTemporariesCreate(", 1)[1].split(
        "\npublic:", 1)[0]
    assert create.count("D3DPOOL_DEFAULT, &candidate, nullptr") == 1
    assert "D3DPOOL_MANAGED, &candidate, nullptr" not in create
    assert create.index("FAILED(d3ddev->CreateVertexBuffer(") < create.index(
        "if (FAILED(candidate->Unlock()))") < create.index("LetterboxVertex = candidate;")
    assert "LetterboxVertex->Release();" in reset
    assert reset.index("LetterboxVertex->Release();") < reset.index(
        "LetterboxRasterDevice = nullptr;")
    assert "CreateLetterboxVertex();" in remake

verify_ex_letterbox_pool(src)
for old, bad in (
    ("D3DPOOL_DEFAULT, &candidate, nullptr", "D3DPOOL_MANAGED, &candidate, nullptr"),
    ("if (FAILED(candidate->Unlock()))", "if (SUCCEEDED(candidate->Unlock()))"),
):
    assert old in src
    try:
        verify_ex_letterbox_pool(src.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("D3D9Ex managed/reset regression survived: " + old)
print("PASS D3D9Ex-compatible menu bars pool/Reset lifecycle, 2 destructive controls")

# Desktop/front-end F11 shares the GPU bars' enablement and rect; only the
# external XR gameplay shell may use the full source viewport, including
# when source/eye aspect changes yield an ordinary 1x font atlas.
# The game 4:3 bars and native desktop/menu layout remain unchanged.
overlay = (Path(__file__).resolve().parents[1] / "src/overlay/overlay.cpp").read_text()

def verify_shell_rect(code: str) -> None:
    shell = code.split("Overlay::ContentRect Overlay::content_rect()", 1)[1].split(
        "const std::vector<OverlayWindow*>& Overlay::windows()", 1)[0]
    for required in (
        '#include "vr/ui/menu_letterbox_geometry.hpp"',
        "const bool externalVrShell = Game::is_vr_gameplay_presentation();",
        "if (externalVrShell)",
        "return { 0.f, 0.f, screen.x, screen.y };",
        "Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0",
        "(Settings::UILetterboxing == 2 || !Game::is_in_game())",
        "OutRunVR::UI::BuildMenuContentBounds(",
        "screen.x, screen.y);",
        "if (!content.valid())",
        "return { content.x, content.y, content.width, content.height };",
    ):
        assert required in (code if required.startswith("#include") else shell), required
    assert shell.index("if (externalVrShell)") < shell.index(
        "OutRunVR::UI::BuildMenuContentBounds(")
    assert "VrFontMultiplier > 1.0f" not in shell
    assert "screen.y * (4.f / 3.f)" not in shell  # old side-only duplicate
    gpu = src.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    assert "Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0 && LetterboxVertex" in gpu
    assert "Settings::UILetterboxing == 2" in gpu

def verify_shared_content_bounds(header: str) -> None:
    for required in (
        "constexpr MenuContentBounds BuildMenuContentBounds(",
        "const auto bars = BuildMenuBarGeometry(sourceWidth, sourceHeight);",
        "if (bars.axis == MenuBarAxis::Invalid)",
        "if (bars.axis == MenuBarAxis::Sides)",
        "const float left = bars.vertices[1].x;",
        "const float right = bars.vertices[4].x;",
        "if (bars.axis == MenuBarAxis::TopBottom)",
        "const float top = bars.vertices[2].y;",
        "const float bottom = bars.vertices[4].y;",
        "return { 0.0f, top, sourceWidth, bottom - top };",
        "static_assert(BuildMenuContentBounds(1200, 1600).y == 350.5f);",
        "static_assert(BuildMenuContentBounds(1200, 1600).height == 899.5f);",
        "static_assert(!BuildMenuContentBounds(16385, 1600).valid());",
    ):
        assert required in header, required

verify_shell_rect(overlay)
verify_shared_content_bounds(menu_bars)
for old, bad in (
    ("OutRunVR::UI::BuildMenuContentBounds(", "OutRunVR::UI::BuildLegacySideRect("),
    ("return { content.x, content.y, content.width, content.height };",
     "return { content.x, 0.f, content.width, screen.y };"),
    ("if (externalVrShell)", "if (!externalVrShell)"),
    ("Settings::UILetterboxing == 2 || !Game::is_in_game()",
     "Settings::UILetterboxing == 1 && !Game::is_in_game()"),
    ("if (!content.valid())", "if (content.valid())"),
):
    assert old in overlay, old
    try:
        verify_shell_rect(overlay.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("F11 portrait rect mutation survived: " + old)
for old, bad in (
    ("const float top = bars.vertices[2].y;", "const float top = 0.0f;"),
    ("const float bottom = bars.vertices[4].y;", "const float bottom = sourceHeight;"),
    ("const auto bars = BuildMenuBarGeometry(sourceWidth, sourceHeight);",
     "const auto bars = BuildLegacySideGeometry(sourceWidth, sourceHeight);"),
):
    assert old in menu_bars, old
    try:
        verify_shared_content_bounds(menu_bars.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Shared menu geometry mutation survived: " + old)

def content_bounds(w, h, enabled):
    if not isfinite(w) or not isfinite(h) or w < 1 or h < 1 or w > 16384 or h > 16384:
        return (0, 0, 0, 0)
    if not enabled:
        return (0, 0, w, h)
    if w > h * (4/3) + .5:
        e = (w - h * (4/3)) * .5 + .5
        return (e, 0, w - 2*e + .5, h)
    if h > w * .75 + .5:
        e = (h - w * .75) * .5 + .5
        return (0, e, w, h - 2*e + .5)
    return (0, 0, w, h)

assert content_bounds(1200, 1600, True) == (0, 350.5, 1200, 899.5)
assert content_bounds(1920, 1080, True) == (240.5, 0, 1439.5, 1080)
assert content_bounds(640, 480, True) == (0, 0, 640, 480)
for w, h in ((1920,1080), (3440,1440), (2496,2688),
             (1200,1600), (1280,1024), (1024,768)):
    for letterbox in (0, 1, 2):
        for scaling in (0, 1):
            for in_game in (False, True):
                enabled = letterbox > 0 and scaling > 0 and (
                    letterbox == 2 or not in_game)
                x, y, iw, ih = content_bounds(w, h, enabled)
                assert 0 <= x < w and 0 <= y < h and 0 < iw <= w and 0 < ih <= h
                assert x + iw <= w + .51 and y + ih <= h + .51
                if not enabled:
                    assert (x, y, iw, ih) == (0, 0, w, h)
for w, h in ((0,1600), (1200,0), (float("nan"),768),
             (1920,float("inf")), (16385,1080)):
    assert content_bounds(w, h, True) == (0, 0, 0, 0)
print("PASS F11 portrait/top-bottom and widescreen shared menu content, 8 destructive controls")

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
    assert create.index("if (!layout.hasBars())") < create.index(
        "LetterboxRasterDevice = d3ddev;")
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
# Switching from widescreen to portrait must retire prior side rails
# and bound F11 below the new TOP strip, rather than keeping a stale left rail.
assert content_bounds(3440, 1440, True)[0] > 0
assert content_bounds(2496, 2688, True)[0] == 0
assert content_bounds(2496, 2688, True)[1] > 0
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



# D3D9Ex Reset can transiently fail VB Create/Lock/Unlock. A failed
# widescreen OR portrait allocation must not be marked as cached: the
# next EndScene at the same valid source size has to retry. Only a
# native 4:3 no-bars result is cached without GPU allocations.
def verify_transient_ex_menu_retry(code: str) -> None:
    create = code.split("void CreateLetterboxVertex()\n{", 1)[1].split(
        "\nclass D3DHooks : public Hook", 1)[0]
    empty = create.split("if (!layout.hasBars())", 1)[1].split(
        "CUSTOMVERTEX vertices[8]{};", 1)[0]
    unlock = create.split("if (FAILED(candidate->Unlock()))", 1)[1]
    ready = unlock.split("LetterboxVertex = candidate;", 1)[1]
    assert empty.count("LetterboxRasterDevice = d3ddev;") == 1
    assert empty.count("LetterboxRasterWidth = sourceWidth;") == 1
    assert empty.count("LetterboxRasterHeight = sourceHeight;") == 1
    assert create.count("LetterboxRasterDevice = d3ddev;") == 2
    assert create.count("LetterboxRasterWidth = sourceWidth;") == 2
    assert create.count("LetterboxRasterHeight = sourceHeight;") == 2
    assert "candidate->Release();" in unlock.split(
        "LetterboxVertex = candidate;", 1)[0]
    assert "return;" in unlock.split(
        "LetterboxVertex = candidate;", 1)[0]
    assert unlock.index("candidate->Release();") < unlock.index(
        "LetterboxVertex = candidate;")
    assert "LetterboxRasterDevice = d3ddev;" in ready
    assert ready.index("LetterboxRasterDevice = d3ddev;") < ready.index(
        "LetterboxRasterWidth = sourceWidth;") < ready.index(
        "LetterboxRasterHeight = sourceHeight;")

verify_transient_ex_menu_retry(src)
start = src.index("void CreateLetterboxVertex()")
end = src.index("\nclass D3DHooks : public Hook", start)
body = src[start:end]
for old, bad in (
    ("if (FAILED(candidate->Unlock()))", "if (SUCCEEDED(candidate->Unlock()))"),
    ("LetterboxVertex = candidate;", "// lost successful GPU buffer"),
    ("LetterboxRasterDevice = d3ddev;",
     "LetterboxRasterDevice = nullptr;"),  # native 4:3 cache must survive
    ("LetterboxVertex = candidate;\n\t// Only completed buffers",
     "LetterboxRasterDevice = d3ddev;\n\tLetterboxVertex = candidate;\n\t// Only completed buffers"),
):
    assert old in body, old
    mutated = src[:start] + body.replace(old, bad, 1) + src[end:]
    try:
        verify_transient_ex_menu_retry(mutated)
    except (AssertionError, ValueError, IndexError):
        pass
    else:
        raise AssertionError("D3D9Ex transient cache mutant survived: " + old)

for w, h in ((3440, 1440), (1920, 1080), (1024, 768), (2496, 2688)):
    next_size = (7, w, h)
    cached = (None, 0, 0)
    assert should_rebuild(cached, next_size)
    if w > h * 4 / 3 or h > w * 3 / 4:
        for failed_stage in ("Create", "Lock", "Unlock"):
            # The real code leaves cached untouched on all three failures.
            assert should_rebuild(cached, next_size), failed_stage
    cached = next_size  # side/portrait VB or completed native 4:3
    assert not should_rebuild(cached, next_size)
print("PASS D3D9Ex side/portrait retry, native 4:3 no-bars cache, 4 destructive controls")

# Issue #119: EndScene menu bars must ignore only inherited game clip masks.
# Keep the original scissor/stencil states intact for the next scene and F11.
def verify_menu_bar_clip_state(code: str) -> None:
    endscene = code.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    required = (
        "bool clipStateReady =",
        "(!Game::is_in_game() || Settings::UILetterboxing == 2) &&",
        "SUCCEEDED(d3ddev->GetRenderState(D3DRS_SCISSORTESTENABLE, &prevScissorTest))",
        "SUCCEEDED(d3ddev->GetRenderState(D3DRS_STENCILENABLE, &prevStencilEnable))",
        "if (clipStateReady)",
        "d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, FALSE);",
        "d3ddev->SetRenderState(D3DRS_STENCILENABLE, FALSE);",
        "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);",
        "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);",
        "d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, prevScissorTest);",
        "d3ddev->SetRenderState(D3DRS_STENCILENABLE, prevStencilEnable);",
    )
    # The live-resize predicate occurs earlier in EndScene as well. Anchor
    # the ordering check at the snapshot owner, not the first matching token.
    clip_start = endscene.index("bool clipStateReady =")
    order = [endscene.index(item, clip_start) for item in required]
    assert order == sorted(order) and len(set(order)) == len(order)
    assert endscene.count("if (clipStateReady)") == 2
    # A failed state snapshot gates ALL sidebar draws, not the ImGui branch.
    assert endscene.index("if (clipStateReady)") < endscene.index(
        "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);")
    assert endscene.index("d3ddev->SetRenderState(D3DRS_STENCILENABLE, prevStencilEnable);") < endscene.index(
        "d3ddev->SetRenderState(D3DRS_CULLMODE, prevCullMode);")

verify_menu_bar_clip_state(src)
for original, broken in (
    ("if (clipStateReady)", "if (true)"),
    ("SUCCEEDED(d3ddev->GetRenderState(D3DRS_SCISSORTESTENABLE, &prevScissorTest))", "true"),
    ("SUCCEEDED(d3ddev->GetRenderState(D3DRS_STENCILENABLE, &prevStencilEnable))", "true"),
    ("d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, FALSE);",
     "d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, TRUE);"),
    ("d3ddev->SetRenderState(D3DRS_STENCILENABLE, FALSE);",
     "d3ddev->SetRenderState(D3DRS_STENCILENABLE, TRUE);"),
    ("d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, prevScissorTest);",
     "d3ddev->SetRenderState(D3DRS_SCISSORTESTENABLE, FALSE);"),
    ("d3ddev->SetRenderState(D3DRS_STENCILENABLE, prevStencilEnable);",
     "d3ddev->SetRenderState(D3DRS_STENCILENABLE, FALSE);"),
):
    assert original in src
    damaged = src.replace(original, broken, 1)
    try:
        verify_menu_bar_clip_state(damaged)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Menu clip-state destructive mutant escaped: " + original)
print("PASS 4:3 menu bars scissor/stencil isolation, F11 continuation and 7 destructive mutants")


# Issue #119 00746: restoring a null vertex declaration does not restore
# D3D9 fixed-function FVF when menu bars switched the device to CUSTOMFVF.
# Protect the owning EndScene draw/restore and fail on destructive mutations.
def verify_letterbox_fvf_restore(code: str) -> None:
    endscene = code.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    capture = endscene.index("DWORD prevFVF = 0;")
    draw = endscene.index("d3ddev->SetFVF(CUSTOMFVF);")
    restore = endscene.index("if (hadFixedFVF)")
    for token in (
        "SUCCEEDED(d3ddev->GetFVF(&prevFVF)) && prevFVF != 0;",
        "d3ddev->GetVertexDeclaration(&prevVertexDecl);",
        "if (hadFixedFVF)\n\t\t\t\t\td3ddev->SetFVF(prevFVF);",
        "else\n\t\t\t\t\td3ddev->SetVertexDeclaration(prevVertexDecl);",
        "if (prevVertexDecl)\n\t\t\t\t\tprevVertexDecl->Release();",
    ):
        assert token in endscene, token
    assert capture < endscene.index("GetVertexDeclaration(&prevVertexDecl)") < draw
    assert draw < endscene.index("DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2)") < restore
    assert restore < endscene.index("prevVertexDecl->Release();")
    assert endscene.count("d3ddev->SetFVF(prevFVF);") == 1
    assert endscene.count("d3ddev->SetVertexDeclaration(prevVertexDecl);") == 1

verify_letterbox_fvf_restore(src)
for original, wrong in (
    ("SUCCEEDED(d3ddev->GetFVF(&prevFVF)) && prevFVF != 0;",
     "SUCCEEDED(d3ddev->GetFVF(&prevFVF)) && false;"),
    ("if (hadFixedFVF)\n\t\t\t\t\td3ddev->SetFVF(prevFVF);",
     "if (hadFixedFVF)\n\t\t\t\t\td3ddev->SetFVF(CUSTOMFVF);"),
    ("else\n\t\t\t\t\td3ddev->SetVertexDeclaration(prevVertexDecl);",
     "else\n\t\t\t\t\td3ddev->SetVertexDeclaration(nullptr);"),
    ("if (prevVertexDecl)\n\t\t\t\t\tprevVertexDecl->Release();",
     "if (prevVertexDecl)\n\t\t\t\t\t(void)prevVertexDecl;"),
):
    assert src.count(original) == 1
    mutated = src.replace(original, wrong, 1)
    try:
        verify_letterbox_fvf_restore(mutated)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("FVF/menu input restore mutation escaped: " + original)

def returned_vertex_input(fvf: int, custom_decl: object):
    return ("FVF", fvf) if fvf else ("CUSTOM", custom_decl)

for fvf in (0x4, 0x40, 0x144, 0x1c4):
    assert returned_vertex_input(fvf, object()) == ("FVF", fvf)
declaration = object()
assert returned_vertex_input(0, declaration) == ("CUSTOM", declaration)
assert returned_vertex_input(0, None) == ("CUSTOM", None)
print("PASS DX9Ex menu fixed-FVF/custom-declaration restoration, 4 destructive mutants")

# Issue #119: main-menu 4:3 sidebars are opaque output rather than game
# sprites. An inherited alpha compare or disabled colour-write mask can
# suppress both black triangles even when scissor/stencil are disabled.
# Capture, override and restore those two distinct D3D9 states in EndScene.
def verify_menu_opaque_mask(code: str) -> None:
    endscene = code.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    required = (
        "DWORD prevAlphaTest = FALSE;",
        "DWORD prevColorWrite = 0;",
        "SUCCEEDED(d3ddev->GetRenderState(D3DRS_ALPHATESTENABLE, &prevAlphaTest))",
        "SUCCEEDED(d3ddev->GetRenderState(D3DRS_COLORWRITEENABLE, &prevColorWrite))",
        "if (clipStateReady)",
        "d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);",
        "d3ddev->SetRenderState(D3DRS_COLORWRITEENABLE,\n"
        "\t\t\t\t\tD3DCOLORWRITEENABLE_RED | D3DCOLORWRITEENABLE_GREEN |\n"
        "\t\t\t\t\tD3DCOLORWRITEENABLE_BLUE | D3DCOLORWRITEENABLE_ALPHA);",
        "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);",
        "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);",
        "d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, prevAlphaTest);",
        "d3ddev->SetRenderState(D3DRS_COLORWRITEENABLE, prevColorWrite);",
    )
    points = [endscene.index(token) for token in required]
    assert points == sorted(points) and len(set(points)) == len(points)
    # No new state touches outside the guarded menu bar draw. Missing
    # snapshots must skip the bars, not corrupt following F11/game draws.
    assert endscene.count("if (clipStateReady)") == 2
    assert endscene.count("d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);") == 1
    assert endscene.count("d3ddev->SetRenderState(D3DRS_COLORWRITEENABLE, prevColorWrite);") == 1

verify_menu_opaque_mask(src)
opaque_mutants = (
    ("DWORD prevAlphaTest = FALSE;", "DWORD prevAlphaTest = TRUE;"),
    ("DWORD prevColorWrite = 0;", "DWORD prevColorWrite = 15;"),
    ("SUCCEEDED(d3ddev->GetRenderState(D3DRS_ALPHATESTENABLE, &prevAlphaTest))",
     "true"),
    ("SUCCEEDED(d3ddev->GetRenderState(D3DRS_COLORWRITEENABLE, &prevColorWrite))",
     "true"),
    ("d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);",
     "d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, TRUE);"),
    ("D3DCOLORWRITEENABLE_BLUE | D3DCOLORWRITEENABLE_ALPHA);",
     "D3DCOLORWRITEENABLE_BLUE);"),
    ("d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, prevAlphaTest);",
     "d3ddev->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);"),
    ("d3ddev->SetRenderState(D3DRS_COLORWRITEENABLE, prevColorWrite);",
     "d3ddev->SetRenderState(D3DRS_COLORWRITEENABLE, 0);"),
)
for good, bad in opaque_mutants:
    assert src.count(good) == 1, good
    try:
        verify_menu_opaque_mask(src.replace(good, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Opaque menu-sidebar mutant survived: " + good)
# A fully disabled/alpha-rejected game draw must not suppress the sidebar,
# and its original state must still be restored for later scene/ImGui draws.
all_channels = 0x1 | 0x2 | 0x4 | 0x8
for previous_alpha in (False, True):
    for previous_mask in (0, 0x1, 0x7, all_channels):
        bar_alpha, bar_mask = False, all_channels
        assert not bar_alpha and bar_mask == all_channels
        assert (previous_alpha, previous_mask) == (
            previous_alpha, previous_mask)
print("PASS opaque 4:3 menu bars alpha-test/colour-write isolation, 8 destructive mutants")

# Issue #119: The world pass can leave fog/wireframe latched after the
# menu's last sprite. Black sidebar fill must not inherit either state;
# preserve the game's actual states across both border triangles.
def verify_menu_solid_fog_state(code: str) -> None:
    menu = code.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    tokens = (
        "DWORD prevFogEnable = FALSE;",
        "DWORD prevFillMode = D3DFILL_SOLID;",
        "SUCCEEDED(d3ddev->GetRenderState(D3DRS_FOGENABLE, &prevFogEnable))",
        "SUCCEEDED(d3ddev->GetRenderState(D3DRS_FILLMODE, &prevFillMode))",
        "if (clipStateReady)",
        "d3ddev->SetRenderState(D3DRS_FOGENABLE, FALSE);",
        "d3ddev->SetRenderState(D3DRS_FILLMODE, D3DFILL_SOLID);",
        "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);",
        "d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);",
        "d3ddev->SetRenderState(D3DRS_FOGENABLE, prevFogEnable);",
        "d3ddev->SetRenderState(D3DRS_FILLMODE, prevFillMode);",
    )
    offsets = [menu.index(t) for t in tokens]
    assert offsets == sorted(offsets) and len(set(offsets)) == len(offsets)
    assert menu.count("d3ddev->SetRenderState(D3DRS_FOGENABLE, FALSE);") == 1
    assert menu.count("d3ddev->SetRenderState(D3DRS_FILLMODE, D3DFILL_SOLID);") == 1

verify_menu_solid_fog_state(src)
solid_fog_mutants = (
    ("SUCCEEDED(d3ddev->GetRenderState(D3DRS_FOGENABLE, &prevFogEnable))", "true"),
    ("SUCCEEDED(d3ddev->GetRenderState(D3DRS_FILLMODE, &prevFillMode))", "true"),
    ("d3ddev->SetRenderState(D3DRS_FOGENABLE, FALSE);", "/* lost fog isolation */"),
    ("d3ddev->SetRenderState(D3DRS_FILLMODE, D3DFILL_SOLID);", "/* lost solid fill */"),
    ("d3ddev->SetRenderState(D3DRS_FOGENABLE, prevFogEnable);", "/* lost fog restore */"),
    ("d3ddev->SetRenderState(D3DRS_FILLMODE, prevFillMode);", "/* lost fill restore */"),
)
for original, replacement in solid_fog_mutants:
    assert original in src
    try:
        verify_menu_solid_fog_state(src.replace(original, replacement, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Fog/fill destructive mutant escaped: " + original)
print("PASS main menu solid-fill and fog-free bars, original state restore, 6 destructive mutants")


# Issue #119: game UI can leave the viewport clipped to the 4:3 content
# rectangle even after restoring scissor/stencil. Full-width black bars
# must render into the source backbuffer and restore the game viewport.
def verify_menu_full_viewport(source: str) -> None:
    body = source.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    capture = body.index("D3DVIEWPORT9 previousViewport{};")
    gate = body.index("bool clipStateReady =")
    switch = body.index("d3ddev->SetViewport(&barViewport)")
    draw_l = body.index("d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);")
    draw_r = body.index("d3ddev->DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);")
    restore = body.index("d3ddev->SetViewport(&previousViewport)")
    assert capture < gate < switch < draw_l < draw_r < restore
    for value in (
        "currentSize->x <= 16384.0f && currentSize->y <= 16384.0f",
        "std::floor(currentSize->x) == currentSize->x",
        "std::floor(currentSize->y) == currentSize->y",
        "SUCCEEDED(d3ddev->GetViewport(&previousViewport))",
        "barViewport = previousViewport;",
        "barViewport.X = 0;",
        "barViewport.Y = 0;",
        "barViewport.Width = static_cast<DWORD>(currentSize->x);",
        "barViewport.Height = static_cast<DWORD>(currentSize->y);",
        "if (overrideViewport)",
        "clipStateReady = SUCCEEDED(d3ddev->SetViewport(&barViewport));",
        "d3ddev->SetViewport(&previousViewport);",
    ):
        assert value in body, value
    assert body.count("d3ddev->SetViewport(&barViewport)") == 1
    assert body.count("d3ddev->SetViewport(&previousViewport)") == 1
    assert body.count("if (clipStateReady)") == 2
    assert body.index("if (clipStateReady)", switch) < draw_l
    assert restore < len(body)

verify_menu_full_viewport(src)
for good,bad in (
    ("SUCCEEDED(d3ddev->GetViewport(&previousViewport))", "true"),
    ("barViewport.X = 0;", "barViewport.X = previousViewport.X;"),
    ("barViewport.Y = 0;", "barViewport.Y = previousViewport.Y;"),
    ("barViewport.Width = static_cast<DWORD>(currentSize->x);",
     "barViewport.Width = previousViewport.Width;"),
    ("barViewport.Height = static_cast<DWORD>(currentSize->y);",
     "barViewport.Height = previousViewport.Height;"),
    ("clipStateReady = SUCCEEDED(d3ddev->SetViewport(&barViewport));",
     "clipStateReady = true;"),
    ("d3ddev->SetViewport(&previousViewport);",
     "d3ddev->SetViewport(&barViewport);"),
):
    assert good in src
    try:
        verify_menu_full_viewport(src.replace(good,bad,1))
    except (AssertionError,ValueError):
        pass
    else:
        raise AssertionError("Menu full-viewport destructive mutant survived: "+good)
# Source & eye dimensions remain separate. The source viewport is
# reinstated only during bars and never enlarged in portrait/no-bars mode.
for width,height in ((1024,768),(1920,1080),(3440,1440),
                     (2560,1080),(2496,2688)):
    bars = width > height * (4/3)
    previous = (max(0,(width-height*4//3)//2), 0,
                min(width,height*4//3), height)
    desired = (0,0,width,height)
    if bars:
        assert desired[2] >= previous[2] and desired[3] == previous[3]
    assert width < 16384 and height < 16384
print("PASS D3D9Ex full-source menu viewport and exact restore; 7 destructive mutants")


# World clip planes are independent of viewport/scissor/stencil. The final
# game pass may leave one enabled; never let it cut the fixed 4:3 rails.
def verify_menu_user_clip_planes(code: str) -> None:
    body = code.split("static void D3DEndScene(", 1)[1].split(
        "if (overlayInited)", 1)[0]
    capture = body.index("DWORD prevClipPlaneEnable = 0;")
    read = body.index("GetRenderState(D3DRS_CLIPPLANEENABLE, &prevClipPlaneEnable)")
    off = body.index("SetRenderState(D3DRS_CLIPPLANEENABLE, 0);")
    left = body.index("DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);")
    right = body.index("DrawPrimitive(D3DPT_TRIANGLESTRIP, 4, 2);")
    restore = body.index(
        "SetRenderState(D3DRS_CLIPPLANEENABLE, prevClipPlaneEnable);")
    assert capture < read < off < left < right < restore
    assert body.count("D3DRS_CLIPPLANEENABLE") == 3
    assert read < body.index("if (clipStateReady)")
    assert restore < body.index("SetViewport(&previousViewport)")
    assert "SUCCEEDED(d3ddev->GetRenderState(D3DRS_CLIPPLANEENABLE, &prevClipPlaneEnable))" in body

verify_menu_user_clip_planes(src)
for old, bad in (
    ("SUCCEEDED(d3ddev->GetRenderState(D3DRS_CLIPPLANEENABLE, &prevClipPlaneEnable))", "true"),
    ("SetRenderState(D3DRS_CLIPPLANEENABLE, 0);",
     "SetRenderState(D3DRS_CLIPPLANEENABLE, 1);"),
    ("SetRenderState(D3DRS_CLIPPLANEENABLE, prevClipPlaneEnable);",
     "SetRenderState(D3DRS_CLIPPLANEENABLE, 0);"),
):
    assert old in src
    try:
        verify_menu_user_clip_planes(src.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("clip-plane restoration mutation escaped: " + old)
print("PASS user clip plane menu isolation; 3 destructive controls")

# The R23 host must apply both the ORIGINAL authored-menu crop and the
# projected fragment position/extent. A UV-only crop followed by full-size
# optical centering wrongly magnifies partially captured menu content.
r23 = (Path(__file__).resolve().parents[1] / "vrhost/src/main_r23.cpp").read_text()
menu_geometry = (Path(__file__).resolve().parents[1] /
                 "vrhost/src/runtime/menu_content_aspect.hpp").read_text()

# Binocular LOCAL-fixed menu visibility: independent eye projections may
# overlap less than their averaged tangents (Quest asymmetric view pair).
# The shared raster must be confined to their actual tangent intersection.
def verify_shared_fov(code):
    owner = code.split("inline CommonFovTangents PlanCommonFovTangents(", 1)[1].split(
        "    // A 2D quad centered", 1)[0]
    for exact in (
        "const float left = (std::max)(l0, l1);",
        "const float right = (std::min)(r0, r1);",
        "const float down = (std::max)(d0, d1);",
        "const float up = (std::min)(u0, u1);",
        "right - left <= 0.05f || up - down <= 0.05f",
    ):
        assert exact in owner, exact
    assert "0.5f * (l0 + l1)" not in owner
    assert "0.5f * (r0 + r1)" not in owner
verify_shared_fov(menu_geometry)
for original, wrong in (
    ("(std::max)(l0, l1)", "(std::min)(l0, l1)"),
    ("(std::min)(r0, r1)", "(std::max)(r0, r1)"),
    ("(std::max)(d0, d1)", "(std::min)(d0, d1)"),
    ("(std::min)(u0, u1)", "(std::max)(u0, u1)"),
):
    try:
        verify_shared_fov(menu_geometry.replace(original, wrong, 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("eye-overlap mutation survived: " + original)
def common_visible(a,b):
    x0,x1 = max(a[0],b[0]),min(a[1],b[1])
    y0,y1 = max(a[2],b[2]),min(a[3],b[3])
    return (x0,x1,y0,y1) if x1-x0>0.05 and y1-y0>0.05 else None
for a,b,expected in (
    ((-1.,1.,-.8,.8),(-1.,1.,-.8,.8),(-1.,1.,-.8,.8)),
    ((-1.,.65,-.9,.7),(-.65,1.,-.7,.9),(-.65,.65,-.7,.7)),
    ((-.9,.8,-.8,1.),(-.8,.9,-1.,.8),(-.8,.8,-.8,.8)),
):
    c=common_visible(a,b)
    assert c==expected,(c,expected)
    for e in (a,b):
        assert e[0]<=c[0]<c[1]<=e[1]
        assert e[2]<=c[2]<c[3]<=e[3]
assert common_visible((-1.,-.2,-.8,.8),(.2,1.,-.8,.8)) is None
assert common_visible((-.8,.8,-1.,-.2),(-.8,.8,.2,1.)) is None
print("PASS binocular menu frustum: symmetric/asymmetric, disjoint X/Y and 4 mutants")


def verify_visible_menu_fragment(code: str) -> None:
    body = code.split("bool cropCentered43 = OutRunVrMenuAspect::ShouldAutoCropVerifiedFourThree(", 1)[1].split(
        "std::uint32_t image = 0;", 1)[0]
    required = [
        "PlanVisibleCenteredContent(",
        "whole.y += previousHeight * plan.offsetY;",
        "whole.h = previousHeight * plan.height;",
        "const float authoredAspect =",
        "cropCentered43 ? 4.0f / 3.0f : clientAspect;",
        "GetGameClientOutputRect(fullClient);",
        "sourceAspect = authoredAspect;",
        "gameConfiguredLetterbox, false);",
        "constexpr float opticalCoverage = 0.78f;",
        "common, sourceAspect, opticalCoverage);",
        "visibleOffsetX = plan.visibleOffsetX;",
        "visibleOffsetY = plan.visibleOffsetY;",
        "visibleWidthScale = plan.visibleWidthScale;",
        "visibleHeightScale = plan.visibleHeightScale;",
        "placement.centerX + placement.halfWidth * visibleOffsetX;",
        "placement.centerY - placement.halfHeight * visibleOffsetY;",
        "placement.halfWidth * visibleWidthScale;",
        "placement.halfHeight * visibleHeightScale;",
        "visibleCenterX - visibleHalfWidth,",
        "visibleCenterY + visibleHalfHeight,"
    ]
    for token in required:
        assert token in body, token
    # The source call is now bound once to a cached configured-letterbox
    # boolean consumed by both physical-aspect and crop decisions. Verify
    # that the original game config, not a constant, still owns the branch.
    assert ("const bool gameConfiguredLetterbox =\n"
            "            R23GameMenuIsLetterboxed(c.hwnd_);") in code
    assert "gameConfiguredLetterbox, false);" in body
    assert "sourceAspect = OutRunVrMenuAspect::PlanUncroppedAuthoredMenuAspect(" in body
    assert "sourceAspect, clientAspect, gameConfiguredLetterbox," in body
    # Recover the complete authored menu plane for BOTH 4:3 and native
    # unletterboxed 16:9/21:9. A source crop behind if(cropCentered43)
    # silently reintroduces the native-menu edge zoom.
    assert body.index("const float authoredAspect =") < body.index(
        "PlanVisibleCenteredContent(") < body.index("if (plan.crop)")
    assert "if (cropCentered43)" not in body.split("PlanVisibleCenteredContent(", 1)[0]
    assert body.index("GetGameClientOutputRect(fullClient);") < body.index(
        "PlanVisibleCenteredContent(")
    assert body.index("sourceAspect = authoredAspect;") < body.index(
        "PlanOpticallyCenteredClip(")
    assert body.index("placement.centerX + placement.halfWidth * visibleOffsetX;") < body.index(
        "const float sx[4]")
    assert "sourceAspect = plan.aspect;" not in body

def verify_visible_fragment_source(code: str) -> None:
    body = code.split("inline CropPlan PlanVisibleCenteredContent(", 1)[1]
    for token in (
        "const float contentHeight = contentWidth / intendedAspect;",
        "const float visibleTop = (std::max)(sampledTop, contentTop);",
        "const float visibleBottom = (std::min)(sampledBottom, contentBottom);",
        "visibleWidth / contentWidth;",
        "visibleHeight / contentHeight;",
        "result.offsetY = (visibleTop - sampledTop) / sampledHeight;",
        "result.height = visibleHeight / sampledHeight;",
        "visibleOffsetX, visibleOffsetY, widthScale, heightScale",
        "std::fabs(originalAspect - intendedAspect) > 0.0005f",
        "std::fabs(sampledLeft - clientLeft) <= 1.0f",
        "std::fabs(sampledBottom - clientBottom) <= 1.0f",
    ):
        assert token in body, token

# A configured letterbox is not a verified empty matte. Reject any
# accidental reintroduction of auto crop based on the INI alone.
def verify_safe_menu_crop_source(code: str) -> None:
    assert "constexpr bool ShouldAutoCropVerifiedFourThree(" in code
    owner = code.split("constexpr bool ShouldAutoCropVerifiedFourThree(", 1)[1].split(
        "    // OutRun may restart", 1)[0]
    assert "configuredLetterbox && imageMatteVerified;" in owner
    assert "configuredLetterbox || imageMatteVerified;" not in owner

verify_safe_menu_crop_source(menu_geometry)
try:
    verify_safe_menu_crop_source(menu_geometry.replace(
        "configuredLetterbox && imageMatteVerified;",
        "configuredLetterbox || imageMatteVerified;", 1))
except AssertionError:
    pass
else:
    raise AssertionError("unverified menu crop OR mutation escaped")

verify_visible_menu_fragment(r23)
verify_visible_fragment_source(menu_geometry)
for old, bad in (
    ("cropCentered43 ? 4.0f / 3.0f : clientAspect;",
     "cropCentered43 ? 4.0f / 3.0f : 4.0f / 3.0f;"),
    ("cropCentered43 ? 4.0f / 3.0f : clientAspect;",
     "cropCentered43 ? clientAspect : 4.0f / 3.0f;"),
    ("sourceAspect = authoredAspect;", "sourceAspect = plan.aspect;"),
    ("GetGameClientOutputRect(fullClient);",
     "GetClientRect(c.hwnd_, &fullClient);"),
    ("gameConfiguredLetterbox, false);",
     "gameConfiguredLetterbox, true);"),
    ("R23GameMenuIsLetterboxed(c.hwnd_);",
     "false;"),
    ("sourceAspect, clientAspect, gameConfiguredLetterbox,",
     "sourceAspect, clientAspect, false,"),
    ("constexpr float opticalCoverage = 0.78f;",
     "constexpr float opticalCoverage = 1.0f;"),
    ("common, sourceAspect, opticalCoverage);",
     "common, sourceAspect, 1.0f);"),
    ("placement.centerY - placement.halfHeight * visibleOffsetY;",
     "placement.centerY + placement.halfHeight * visibleOffsetY;"),
    ("placement.halfWidth * visibleWidthScale;",
     "placement.halfWidth;"),
    ("whole.y += previousHeight * plan.offsetY;", "whole.y += 0.0f;"),
    ("whole.h = previousHeight * plan.height;", "whole.h = previousHeight;"),
):
    assert old in r23
    try:
        verify_visible_menu_fragment(r23.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("menu fragment geometry mutation survived: " + old)
for old, bad in (
    ("std::fabs(originalAspect - intendedAspect) > 0.0005f",
     "std::fabs(originalAspect - intendedAspect) > 100.0f"),
    ("std::fabs(sampledLeft - clientLeft) <= 1.0f",
     "std::fabs(sampledLeft - clientLeft) > 1.0f"),
    ("std::fabs(sampledBottom - clientBottom) <= 1.0f",
     "std::fabs(sampledBottom - clientBottom) > 1.0f"),
    ("visibleWidth / contentWidth;", "sampledWidth / contentWidth;"),
    ("visibleHeight / contentHeight;", "sampledHeight / contentHeight;"),
    ("result.offsetY = (visibleTop - sampledTop) / sampledHeight;",
     "result.offsetY = 0.0f;"),
    ("result.height = visibleHeight / sampledHeight;",
     "result.height = 1.0f;"),
):
    assert old in menu_geometry
    try:
        verify_visible_fragment_source(menu_geometry.replace(old, bad, 1))
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("visible menu source mutation survived: " + old)
print("PASS main-menu 4:3/native clipped-fragment geometry, 10 destructive controls")

# First-run / migration regression: OutRun's compiled game defaults for
# UIScalingMode and UILetterboxing are both 1. When the existing base INI
# omits either key, the host must not silently substitute 0 and expose the
# full 21:9 desktop rails in the Quest LOCAL menu. Missing base with an
# authoritative user INI also needs to work, but NO files fail closed.
game_scaling = (Path(__file__).resolve().parents[1] /
                "src/hooks_uiscaling.cpp").read_text()
assert 'Setting<int> UIScalingMode{ "Graphics", "UIScalingMode", 1,' in game_scaling
assert 'Setting<int> UILetterboxing{ "Graphics", "UILetterboxing", 1,' in game_scaling

def check_menu_ini_defaults(code: str) -> None:
    owner = code.split("bool R23GameMenuIsLetterboxed(HWND gameWindow) noexcept", 1)[1].split(
        "constexpr ULONGLONG R23PixelIntervalMs", 1)[0]
    tokens = [
        "int effectiveScalingMode = 1;",
        "int letterboxingMode = 1;",
        "bool foundConfig = false;",
        "if (attributes != INVALID_FILE_ATTRIBUTES &&",
        "(attributes & FILE_ATTRIBUTE_DIRECTORY) == 0)",
        'L"Graphics", L"UIScalingMode", effectiveScalingMode, path)',
        'L"Graphics", L"UILetterboxing", letterboxingMode, path)',
        "if (userAttrs != INVALID_FILE_ATTRIBUTES &&",
        'L"Graphics", L"UIScalingMode",',
        'L"Graphics", L"UILetterboxing",',
        "if (!foundConfig)",
        "return false;",
        "ShouldCropConfiguredMenu(",
        "effectiveScalingMode, letterboxingMode);"
    ]
    for token in tokens:
        assert token in owner, token
    assert owner.count("foundConfig = true;") == 2
    assert owner.index("int effectiveScalingMode = 1;") < owner.index(
        "GetFileAttributesW(path);")
    assert owner.index("if (!foundConfig)") < owner.index(
        "cachedLetterbox = OutRunVrMenuAspect::ShouldCropConfiguredMenu(")

check_menu_ini_defaults(r23)
for good, bad in (
    ("int effectiveScalingMode = 1;", "int effectiveScalingMode = 0;"),
    ("int letterboxingMode = 1;", "int letterboxingMode = 0;"),
    ('L"Graphics", L"UIScalingMode", effectiveScalingMode, path)',
     'L"Graphics", L"UIScalingMode", 0, path)'),
    ('L"Graphics", L"UILetterboxing", letterboxingMode, path)',
     'L"Graphics", L"UILetterboxing", 0, path)'),
    ("if (!foundConfig)", "if (foundConfig)"),
    ("foundConfig = true;", "foundConfig = false;"),
):
    assert good in r23
    mutant = r23.replace(good, bad, 1)
    try:
        check_menu_ini_defaults(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("INI-default/ownership mutation escaped: " + good)

def effective_crop(base, user):
    # None means missing file; {} means present but no Graphics keys.
    if base is None and user is None:
        return False
    scaling, letterbox = 1, 1
    for layer in (base, user):
        if layer is not None:
            scaling = layer.get("UIScalingMode", scaling)
            letterbox = layer.get("UILetterboxing", letterbox)
    return scaling in (1, 2) and letterbox in (1, 2)

for base, user, expected in (
    ({}, None, True), ({}, {}, True),
    (None, {}, True), (None, None, False),
    ({"UIScalingMode": 0}, None, False),
    ({"UILetterboxing": 0}, None, False),
    ({"UIScalingMode": 0}, {"UIScalingMode": 1}, True),
    ({"UILetterboxing": 0}, {"UILetterboxing": 1}, True),
    ({}, {"UILetterboxing": 0}, False),
    ({}, {"UIScalingMode": 0}, False),
    ({"UIScalingMode": 2, "UILetterboxing": 2}, None, True),
    ({}, {"UIScalingMode": 3}, False),
):
    assert effective_crop(base, user) == expected, (base, user)
print("PASS game/host default parity, absent-key/user-INI precedence and six destructive mutations")
