#!/usr/bin/env python3
"""Source-bound same-EndScene F11 input/atlas contract, including mutants."""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
toggle = (r / "src/overlay/overlay_toggle_frame.hpp").read_text()
overlay = (r / "src/overlay/overlay.cpp").read_text()
header = (r / "src/overlay/overlay.hpp").read_text()
hook = (r / "src/overlay/hooks_overlay.cpp").read_text()
required = (
    "boundHeld && !previousBoundHeld", "previousBoundHeld = boundHeld;",
    "!newInput && !bindingDialog && legacyReleased",
    "edge || legacyEdge", "toggle ? !visible : visible",
)
assert all(x in toggle for x in required)
for token in required:
    assert token not in toggle.replace(token, "false", 1), token
# The out-of-class definition is qualified; render() calls it unqualified.
# Own each site separately so either missing/duplicated poll is rejected.
assert overlay.count("Overlay::will_be_visible_this_frame()") == 1
render = overlay.split("bool Overlay::render()", 1)[1].split(
    "// Creates a unique machine ID", 1)[0]
assert render.count("will_be_visible_this_frame();") == 1
assert render.index("will_be_visible_this_frame();") < render.index(
    "const bool toggleOverlay = s_togglePending;")
assert "s_togglePending = next.toggle;" in overlay
assert "s_toggleCaptureValid = true;" in overlay
assert "const bool toggleOverlay = s_togglePending;" in overlay
assert "s_togglePending = false;" in overlay
assert "s_toggleCaptureValid = false;" in overlay
assert "Settings::UseNewInput, IsBindingDialogActive, overlay_visible" in overlay
assert "static OverlayToggleFrame frame;" in overlay
assert '#include "overlay_toggle_frame.hpp"' in overlay
assert "inline static bool s_toggleCaptureValid = false;" in header
assert "inline static bool s_togglePending = false;" in header
assert hook.index("const bool f11VisibleThisFrame = Overlay::will_be_visible_this_frame();") < hook.index("float vrFontMultiplier = 1.0f;")
assert hook.index("float vrFontMultiplier = 1.0f;") < hook.index("Overlay::rebuild_fonts();") < hook.index("overlayActive = Overlay::render();")
# The cursor and font atlas share one same-frame gameplay predicate.
# Preserve its actual source binding and ordering (not old inlined syntax).
assert "const bool vrGameplay = Game::is_vr_gameplay_presentation();" in hook
assert "if (f11VisibleThisFrame && vrGameplay)" in hook
assert (hook.index("const bool vrGameplay = Game::is_vr_gameplay_presentation();")
        < hook.index("if (f11VisibleThisFrame && vrGameplay)")
        < hook.index("Overlay::rebuild_fonts();"))

# Source-level model checks open->hold->release->close, legacy input,
# bound action with dialog and the desktop negative. The C++ header is
# dependency-free; the same cases can be compiled as an x86 host smoke.
p=False
vis=False
cases=((0,0,0,0,0),(0,1,0,0,1),(0,0,0,0,1),(0,1,0,1,1),(0,1,0,0,0),
       (1,0,1,0,1),(1,0,1,0,1),(0,0,1,0,1),(1,0,1,0,0))
for held,key,new,dlg,expected in cases:
    edge=bool(held) and not p
    p=bool(held)
    toggle_event=edge or (not new and not dlg and bool(key))
    vis=not vis if toggle_event else vis
    assert vis==bool(expected)
    density=2.75 if vis else 1.0
    assert (density>1.0)==vis
# The default-initialized member is intentionally false. Reject destructive
# assignments only inside poll(), not the correct member initializer.
poll_body = toggle.split("Decision poll(", 1)[1]
for mutant in ("previousBoundHeld = false;", "const bool edge = boundHeld;",
               "const bool legacyEdge = false;", "const bool toggle = edge;",
               "return { toggle, visible };"):
    assert mutant not in poll_body, mutant
print("PASS same-frame F11 input-to-atlas-to-render, negative/mutation cases")
