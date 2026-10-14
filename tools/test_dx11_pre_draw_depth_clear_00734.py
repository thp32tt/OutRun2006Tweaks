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
        "s.clearColor.matches(owner," in observer,
        "backbufferIdentity.Get()))" in observer,
        "s.sourceDrawsThisFrame == 0u" in observer,
        "if ((s.frameBatch.submitted == 0u || s.frameBatch.stopped) &&" in observer,
        "!beforeFirstGameDraw) return false;" in observer,
        "s.frameBatch.submitted != 0u && !continuingFullNativeDraw" in observer,
        "targetIdentity.Get() != backbufferIdentity.Get()" in observer,
        "GameNativeClearCoverage::covers_whole(" in observer,
        "s.frameBatch.note_full_depth_clear(z);" in observer,
        "s.frameBatch.depth_clear_value(output.nativeDepthOrderingMode != 0u)" in draw,
        "s.frameBatch.consume_depth_clear();" in draw,
        "return sameSourceFullColorClear && noSourceDraws && !stopped &&" in h,
        "submitted == 0u && !hasSourceDraw;" in h,
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
    mutated = bridge[:a] + segment.replace(old, new, 1) + bridge[z:]
    assert not linked(mutated, batch, hook), old
assert not linked(bridge, batch.replace(
    "sameSourceFullColorClear && noSourceDraws && !stopped &&",
    "sameSourceFullColorClear && !stopped &&"), hook)
assert not linked(bridge, batch, hook.replace(
    "live_game_frame::observe_game_depth_clear(",
    "live_game_frame::ignored_depth_clear(", 1))
assert "python tools/test_dx11_pre_draw_depth_clear_00734.py" in workflow
assert "tools/dx11_pre_draw_depth_clear_00734.cpp" in workflow
print("00734 game TARGET -> separate full Z -> native first Draw/fallback PASS")
