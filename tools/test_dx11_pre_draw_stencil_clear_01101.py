#!/usr/bin/env python3
"""01101 authentic pre-Draw TARGET|STENCIL and TARGET|Z|STENCIL path."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
helper=(root/"src/vr/d3d11/native_game_main_stencil_clear.hpp").read_text()
start=bridge.index("bool preserve_game_partial_target_clear(")
end=bridge.index("bool preserve_game_color_fill(",start)
hook=bridge[start:end]
must=[
    "if (sameBackbuffer &&",
    "if (clearZ || clearStencil)",
    "GetDepthStencilSurface(",
    "s.clearColor.main_depth_still_bound(",
    "desc.MultiSampleType" if False else "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE",
    "GameNativeMainStencilClear::may_ignore_pre_draw(",
    "s.frameBatch.before_first_native_raster(",
    "if (!canonicalDepth) return false;",
    "if (clearZ) {",
    "s.frameBatch.depthClearPending",
    "GameNativePreDrawCombinedClear::record(",
    "return s.preDrawFills.record_target_clear(",
    "if (count > GameNativePostDrawClearBatch::kMaxSourceRects)"
]
assert all(term in hook for term in must),[x for x in must if x not in hook]
# Post-Draw TARGET|Z/STENCIL still requires exact bounded GPU region
# compaction and canonical D3D9 depth owner before either output view writes.
assert "GameNativePostDrawClearBatch::build(" in hook
assert helper.count("may_ignore_pre_draw(")==1
assert "sameMainDepthStencil && beforeFirstSourceDraw" in helper
assert hook.index("if (!canonicalDepth) return false;") < hook.index(
    "GameNativeMainStencilClear::may_ignore_pre_draw(")
assert hook.index("GameNativeMainStencilClear::may_ignore_pre_draw(") < hook.index(
    "GameNativePreDrawCombinedClear::record(")
for old,new in [
    ("if (!canonicalDepth) return false;","if (false) return false;"),
    ("s.clearColor.main_depth_still_bound(","true /* owner bypass */ && ("),
    ("s.frameBatch.before_first_native_raster(","true /* ordinal bypass */ && ("),
    ("s.frameBatch.depthClearPending","true /* Z seed bypass */"),
]:
    assert old in hook
    assert new not in hook
assert "may_ignore_cropped(" in hook  # old post-Draw fallback retained
print("01101 canonical TARGET/STENCIL first-Draw admission and Z/RT fallback PASS")
