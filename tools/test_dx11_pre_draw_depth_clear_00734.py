#!/usr/bin/env python3
"""00734: real successful TARGET then separate Z Clear before first native Draw."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
batch = (root / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
hook = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def linked(b, h, r):
    start = b.index("bool observe_game_depth_clear(")
    end = b.index("void observe_game_clear(", start)
    observer = b[start:end]
    pre_seed = observer.split("s.frameBatch.can_seed_pre_draw_depth(",1)[1].split(");",1)[0]
    color = b[b.index("void observe_game_clear("):b.index("void observe_unavailable_game_draw(")]
    draw = b[b.index("bool submit("):b.index("bool observe_source_device(")]
    entry = r[r.index("HRESULT __stdcall ClearDestR9("):r.index(
        "template <typename ActualDraw, typename LegacyDraw>")]
    return all((
        "if (SUCCEEDED(result)) {" in entry,
        "live_game_frame::observe_game_depth_clear(" in entry,
        "live_game_frame::observe_game_clear(" in entry,
        "s.clearColor.record(sourceDevice," in color,
        "s.frameBatch.reset();" in color,
        "const bool beforeFirstGameDraw = !s.pending &&" in observer,
        "s.frameBatch.can_seed_pre_draw_depth(" in observer,
        "s.clearColor.matches(owner," in pre_seed,
        "backbufferIdentity.Get()))" in pre_seed,
        "s.sourceDrawsThisFrame == 0u" in pre_seed,
        "if ((s.frameBatch.submitted == 0u || s.frameBatch.stopped) &&" in observer,
        "!beforeFirstGameDraw) return false;" in observer,
        "s.frameBatch.submitted != 0u && !continuingFullNativeDraw" in observer,
        "targetIdentity.Get() != backbufferIdentity.Get()" in observer,
        "GameNativeClearCoverage::covers_whole(" in observer,
        "s.frameBatch.note_full_depth_clear(z);" in observer,
        "s.frameBatch.depth_clear_value(output.nativeDepthOrderingMode != 0u)" in draw,
        "s.frameBatch.consume_depth_clear();" in draw,
        "return sameSourceFullColorClear &&" in h,
        "((noSourceDraws && !hasSourceDraw) ||" in h,
        "(!noSourceDraws && onlyLeadingEmpty)) && !stopped &&" in h,
        "submitted == 0u && !depthReady;" in h,
    ))

assert linked(bridge, batch, hook), "TARGET -> separate full Z -> real Draw disconnected"
for old, new in (
    ("s.clearColor.matches(owner,", "s.clearColor.matches(0u,"),
    ("s.sourceDrawsThisFrame == 0u", "true"),
    ("const bool beforeFirstGameDraw = !s.pending &&",
     "const bool beforeFirstGameDraw = s.pending &&"),
    ("!beforeFirstGameDraw) return false;", "beforeFirstGameDraw) return false;"),
    ("s.frameBatch.note_full_depth_clear(z);", "s.frameBatch.consume_depth_clear();"),
):
    a = bridge.index("bool observe_game_depth_clear(")
    z = bridge.index("void observe_game_clear(", a)
    segment = bridge[a:z]
    assert old in segment, old
    # Main STENCIL safety also probes this owner's color identity earlier.
    # Mutate this test's exact pre-first-Draw Z seed, not the stencil gate.
    if old == "s.clearColor.matches(owner,":
        anchor = segment.index("s.frameBatch.can_seed_pre_draw_depth(")
        segment = segment[:anchor] + segment[anchor:].replace(old, new, 1)
    else:
        segment = segment.replace(old, new, 1)
    mutated = bridge[:a] + segment + bridge[z:]
    assert not linked(mutated, batch, hook), old
assert "(!noSourceDraws && onlyLeadingEmpty)) && !stopped &&" in batch
assert not linked(bridge, batch.replace(
    "(!noSourceDraws && onlyLeadingEmpty)) && !stopped &&",
    "(!noSourceDraws && false)) && !stopped &&"), hook)
assert not linked(bridge, batch, hook.replace(
    "live_game_frame::observe_game_depth_clear(",
    "live_game_frame::ignored_depth_clear(", 1))
assert "python tools/test_dx11_pre_draw_depth_clear_00734.py" in workflow
assert "tools/dx11_pre_draw_depth_clear_00734.cpp" in workflow
print("00734 game TARGET -> separate full Z -> native first Draw/fallback PASS")
