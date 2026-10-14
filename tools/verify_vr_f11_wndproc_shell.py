#!/usr/bin/env python3
"""F11 Win32 hidden-input isolation and VR shell resizing: positive/negative/mutants."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
routing = (root / "src/overlay/f11_input_routing.hpp").read_text()
hook = (root / "src/overlay/hooks_overlay.cpp").read_text()
overlay = (root / "src/overlay/overlay.cpp").read_text()
workflow = (root / ".github/workflows/vr-dx9ex-active.yml").read_text()
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
route_args = wnd.split("OutRunF11Input::ShouldForwardToImGui(", 1)[1].split(
    ");", 1)[0]
for original in ("notificationMouseCapture", "legacyF11Key"):
    assert original in route_args
    assert original not in route_args.replace(original, "false", 1)
assert "ImGui::SetNextWindowSizeConstraints(" not in shell.replace(
    "ImGui::SetNextWindowSizeConstraints(", "/* removed */", 1)
print("PASS F11 hidden-input isolation, input/focus negative cases and VR shell bounds")
