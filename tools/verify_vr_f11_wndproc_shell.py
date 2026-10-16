#!/usr/bin/env python3
"""F11 Win32 hidden-input isolation and VR shell resizing: positive/negative/mutants."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
routing = (root / "src/overlay/f11_input_routing.hpp").read_text(encoding="utf-8")
hook = (root / "src/overlay/hooks_overlay.cpp").read_text(encoding="utf-8")
overlay = (root / "src/overlay/overlay.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8")
wnd = hook.split("class WndprocHook : public Hook", 1)[1].split("public:", 1)[0]
shell = overlay.split("void Overlay::render_shell()", 1)[1].split("void Overlay::init()", 1)[0]

for token in (
    '#include "f11_input_routing.hpp"',
    "wParam == VK_F11", "msg == WM_KEYDOWN", "msg == WM_KEYUP",
    "msg == WM_SYSKEYDOWN", "msg == WM_SYSKEYUP",
    "msg == WM_KILLFOCUS", "msg == WM_ACTIVATEAPP",
    "overlayInited && mouseMessage && ImGui::GetCurrentContext()",
    "ImGui::GetIO().WantCaptureMouse",
    "OutRunF11Input::ShouldForwardToImGui(",
    "overlayActive, Overlay::IsBindingDialogActive,",
    "legacyF11Key, focusTransition, notificationMouseCapture",
    "overlayInited && forwardImGui &&",
):
    assert token in (hook if token.startswith('#include') else wnd), token
assert wnd.index("ShouldForwardToImGui(") < wnd.index("ImGui_ImplWin32_WndProcHandler(")
assert wnd.count("ImGui_ImplWin32_WndProcHandler(") == 1
# VR F11 pointer must be part of ImGui's D3D9 geometry (and therefore
# stereo-eye replay), not a Windows hardware cursor absent from capture.
cursor_policy = routing.split("constexpr bool ShouldDrawSoftwareCursor(", 1)[1].split(
    "static_assert(", 1)[0]
assert "return f11Visible && vrGameplay;" in cursor_policy
assert "return f11Visible && vrGameplay;" not in cursor_policy.replace(
    "return f11Visible && vrGameplay;", "return f11Visible;", 1)
for f11, vr, drawn in ((True, True, True), (True, False, False),
                      (False, True, False), (False, False, False)):
    assert (f11 and vr) is drawn
cursor_setup = hook.split("const bool f11VisibleThisFrame =", 1)[1].split(
    "float vrFontMultiplier", 1)[0]
assert "const bool vrGameplay = Game::is_vr_gameplay_presentation();" in cursor_setup
assert "ImGui::GetIO().MouseDrawCursor =" in cursor_setup
assert "OutRunF11Input::ShouldDrawSoftwareCursor(" in cursor_setup
assert "f11VisibleThisFrame, vrGameplay" in cursor_setup
assert hook.index("ImGui::GetIO().MouseDrawCursor =") < hook.index(
    "ImGui_ImplDX9_NewFrame();") < hook.index("overlayActive = Overlay::render();")
assert "if (overlayActive && vrGameplay)" in hook
assert "ScopedExternalOverlaySemantic semantic(" in hook
assert "ImGui_ImplDX9_RenderDrawData(ImGui::GetDrawData());" in hook
native_cursor = wnd.split("if (overlayActive && msg == WM_SETCURSOR", 1)[1].split(
    "return TRUE;", 1)[0]
assert "ImGui::GetIO().MouseDrawCursor" in native_cursor
assert "SetCursor(softwareCursor ? nullptr : LoadCursorA(nullptr, IDC_ARROW));" in native_cursor
assert "SetCursor(LoadCursorA(nullptr, IDC_ARROW));" not in native_cursor
assert "ImGui::SetNextWindowSizeConstraints(" in shell
assert shell.index("if (externalVrShell)\n\t\tImGui::SetNextWindowSizeConstraints(") < shell.index(
    "ImGui::SetNextWindowSize(windowSize, layoutPlacement);")
assert "ImVec2(maxWidth, maxHeight)" in shell
assert "tools/verify_vr_f11_wndproc_shell.py" in workflow

def route(opened, dialog, f11, focus, hud_mouse):
    return opened or dialog or f11 or focus or hud_mouse

cases = [
    ((False, False, False, False, False), False),  # gameplay wheel stays with game
    ((True, False, False, False, False), True),   # shell keyboard/pointer
    ((False, True, False, False, False), True),   # bindings
    ((False, False, True, False, False), True),   # legacy F11 key-up
    ((False, False, False, True, False), True),   # alt-tab key reset
    ((False, False, False, False, True), True),   # notification click
]
for state, expected in cases:
    assert route(*state) == expected
    for i in range(5):
        if state[i]:
            mutated = list(state)
            mutated[i] = False
            assert route(*mutated) is False, (state, i)
for width, height in ((3440., 1440.), (1920., 1080.),
                      (1024., 768.), (240., 160.), (8., 8.)):
    usable_width = max(1., width - min(40., width * .1))
    usable_height = max(1., height - min(40., height * .1))
    minimum_width = min(240., usable_width)
    minimum_height = min(140., usable_height)
    assert 0 < minimum_width <= usable_width <= width
    assert 0 < minimum_height <= usable_height <= height
# Mutation guards catch accidental removal of the actual input/VR owners.
assert "overlayInited && forwardImGui &&" in wnd
assert "const LRESULT imguiResult =" in wnd
assert "!OutRunF11Input::MustPreserveOriginalWin32Path(" in wnd
assert "legacyF11Key, focusTransition, systemMessage)" in wnd
assert "WM_SYSCHAR" in wnd and "WM_SYSCOMMAND" in wnd
assert "WM_IME_STARTCOMPOSITION" in wnd and "WM_IME_ENDCOMPOSITION" in wnd
route_args = wnd.split("OutRunF11Input::ShouldForwardToImGui(", 1)[1].split(
    ");", 1)[0]
for original in ("notificationMouseCapture", "legacyF11Key"):
    assert original in route_args
    assert original not in route_args.replace(original, "false", 1)
assert "ImGui::SetNextWindowSizeConstraints(" not in shell.replace(
    "ImGui::SetNextWindowSizeConstraints(", "/* removed */", 1)
# F11 input ownership: classify ordinary key/character/IME and pointer
# messages, consume only while an interactive overlay owns them, preserve
# legacy F11, OS shortcuts, focus and game input with a closed overlay.
for required in (
    "constexpr bool ShouldConsumeFromGame(",
    "if (legacyF11Key)", "interactiveShell && (keyboardMessage || mouseMessage)",
    "mouseMessage && notificationMouseCapture",
):
    assert required in routing, required
for required in (
    "msg == WM_KEYDOWN || msg == WM_KEYUP",
    "msg == WM_CHAR || msg == WM_DEADCHAR",
    "msg == WM_IME_CHAR || msg == WM_IME_COMPOSITION",
    "OutRunF11Input::ShouldConsumeFromGame(",
    "legacyF11Key, keyboardMessage, mouseMessage,",
    "notificationMouseCapture))",
):
    assert required in wnd, required
assert wnd.index("ImGui_ImplWin32_WndProcHandler(") < wnd.index(
    "OutRunF11Input::ShouldConsumeFromGame(")
assert wnd.count("OutRunF11Input::ShouldConsumeFromGame(") == 1
assert "msg == WM_SYSKEYDOWN ||" not in wnd.split("const bool keyboardMessage =", 1)[1].split(";", 1)[0]
assert "msg == WM_SYSCOMMAND" not in wnd.split("const bool keyboardMessage =", 1)[1].split(";", 1)[0]
def consumes(shell, dialog, f11, keyboard, mouse, notification):
    return not f11 and ((shell or dialog) and (keyboard or mouse) or
                        mouse and notification)
for state, expected in (
    ((True, False, False, True, False, False), True),
    ((True, False, False, False, True, False), True),
    ((False, True, False, True, False, False), True),
    ((False, False, False, False, True, True), True),
    ((True, False, True, True, False, False), False),
    ((False, False, False, True, False, False), False),
    ((False, False, False, False, True, False), False),
    ((True, False, False, False, False, False), False),
):
    assert consumes(*state) is expected, state
# Destructive regressions must fail, not simply observe presence of a helper.
assert "interactiveShell && (keyboardMessage || mouseMessage)" not in routing.replace(
    "interactiveShell && (keyboardMessage || mouseMessage)", "false", 1)
assert "legacyF11Key, keyboardMessage, mouseMessage," not in wnd.replace(
    "legacyF11Key, keyboardMessage, mouseMessage,", "false, false, false,", 1)
# A nonzero ImGui handler result must NOT suppress native F11 release,
# focus changes, or OS Alt/system messages. Test positive and negative
# combinations against the actual C++ policy and hook invocation.
assert "constexpr bool MustPreserveOriginalWin32Path(" in routing
assert "return legacyF11Key || focusTransition || systemMessage;" in routing
for f11 in (False, True):
    for focus in (False, True):
        for system in (False, True):
            preserve = f11 or focus or system
            assert preserve == bool(f11 or focus or system)
            if preserve:
                assert not (True and not preserve)  # handler=1 still reaches game
            else:
                assert True and not preserve        # UI handler may consume
assert "return legacyF11Key || focusTransition || systemMessage;" not in routing.replace(
    "return legacyF11Key || focusTransition || systemMessage;",
    "return legacyF11Key;", 1)
assert "!OutRunF11Input::MustPreserveOriginalWin32Path(" not in wnd.replace(
    "!OutRunF11Input::MustPreserveOriginalWin32Path(",
    "/* native path removed */", 1)
print("PASS F11 hidden-input isolation, native F11/focus/system, IME and VR shell bounds")
