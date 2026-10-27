#!/usr/bin/env python3
"""01102 real game pre-Draw clipped Z|STENCIL native depth replay."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
guard=(root/"src/vr/d3d11/native_game_main_stencil_clear.hpp").read_text()
start=bridge.index("bool observe_game_depth_clear(")
end=bridge.index("void observe_game_clear(",start)
hook=bridge[start:end]
required=[
    "const bool beforeFirstDepth = partialDepth &&",
    "s.frameBatch.depthClearPending",
    "s.frameBatch.can_seed_pre_draw_depth(",
    "s.clearColor.main_depth_still_bound(",
    "const bool preDrawStencilSafe = beforeFirstDepth &&",
    "GameNativeMainStencilClear::may_ignore_pre_draw(",
    "s.frameBatch.leadingEmptySourceDraws ==",
    "!preDrawStencilSafe) return false;",
    "if(beforeFirstDepth)",
    "return s.preDrawDepth.record(owner,",
    "native_game_partial_depth_ready(",
    "s.preDrawDepth.discard();",
]
assert all(x in hook for x in required),[x for x in required if x not in hook]
assert hook.index("const bool beforeFirstDepth") < hook.index(
    "const bool preDrawStencilSafe") < hook.index(
    "return s.preDrawDepth.record(owner,")
assert "!clearStencil &&\n                !continuingFullNativeDraw" not in hook
assert "sameMainDepthStencil && beforeFirstSourceDraw" in guard
for old,unsafe in (
    ("s.frameBatch.depthClearPending","true /* fake original Z seed */"),
    ("s.clearColor.main_depth_still_bound(","true /* foreign depth owner */"),
    ("s.frameBatch.can_seed_pre_draw_depth(","true /* skipped source ordinal */"),
    ("!preDrawStencilSafe) return false;","true /* skip stencil proof */) return false;"),
    ("return s.preDrawDepth.record(owner,","return true /* Z was discarded */; //"),
):
    assert old in hook
    assert unsafe not in hook
print("01102 bounded clipped main Z|STENCIL native D32 and fallback PASS")
