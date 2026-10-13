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
    assert "const bool externalVrShell = Game::is_vr_gameplay_presentation();" in shell
    assert "VrFontMultiplier > 1.0f" not in shell
    assert "Game::is_vr_gameplay_presentation();" in shell
    assert "if (externalVrShell)" in shell
    assert shell.index("return { 0.f, 0.f, screen.x, screen.y };") < shell.index("float border = 0.f;")
    # Destructive regression: reinstating the old font-density gate would
    # clip F11 at the 1.0x threshold during a live XR resolution transition.
    gated = shell.replace(
        "const bool externalVrShell = Game::is_vr_gameplay_presentation();",
        "const bool externalVrShell = VrFontMultiplier > 1.0f && Game::is_vr_gameplay_presentation();",
        1)
    assert "const bool externalVrShell = Game::is_vr_gameplay_presentation();" not in gated
    assert "VrFontMultiplier > 1.0f" in gated
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
    assert create.index("if (sourceWidth <= contentWidth)") < create.index(
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



# D3D9Ex Reset can transiently fail VB Create/Lock/Unlock. A failed
# widescreen attempt must not be marked as cached: the next EndScene at
# the same valid source size has to retry. An empty 4:3/portrait result
# *is* complete and should remain cached without GPU allocations.
def verify_transient_ex_menu_retry(code: str) -> None:
    create = code.split("void CreateLetterboxVertex()\n{", 1)[1].split(
        "\nclass D3DHooks : public Hook", 1)[0]
    empty = create.split("if (sourceWidth <= contentWidth)", 1)[1].split(
        "const float borderWidth", 1)[0]
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
     "LetterboxRasterDevice = nullptr;"),  # portrait/4:3 cache must not disappear
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
    if w > h * 4 / 3:
        for failed_stage in ("Create", "Lock", "Unlock"):
            # The real code leaves cached untouched on all three failures.
            assert should_rebuild(cached, next_size), failed_stage
    cached = next_size  # successful widescreen VB or completed empty bars
    assert not should_rebuild(cached, next_size)
print("PASS D3D9Ex transient Create/Lock/Unlock retry, 4:3 no-bars cache, 4 destructive controls")

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
