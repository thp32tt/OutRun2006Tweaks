from pathlib import Path
bridge=Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
helper=Path("src/vr/d3d11/native_game_pre_draw_combined_clear.hpp").read_text(encoding="utf-8")
assert '#include "native_game_pre_draw_combined_clear.hpp"' in bridge
start=bridge.index("bool preserve_game_partial_target_clear(")
end=bridge.index("void observe_game_clear(",start)
hook=bridge[start:end]
assert "if (!clearStencil && sameBackbuffer &&" in hook
assert "s.frameBatch.depthClearPending" in hook
assert "s.clearColor.main_depth_still_bound(" in hook
assert "depthDesc.MultiSampleType != D3DMULTISAMPLE_NONE" in hook
assert "GameNativePreDrawCombinedClear::record(" in hook
assert "s.preDrawFills, s.preDrawDepth, owner, mainRt" in hook
assert "return s.preDrawFills.record_target_clear(" in hook
assert "if (count > GameNativeSourceMutation::kMaxPartialTargetClearRects)" in hook
assert "auto stagedColor = colors;" in helper
assert "auto stagedDepth = depths;" in helper
assert helper.index("stagedDepth.record(")<helper.index("colors = stagedColor;")
assert helper.index("colors = stagedColor;")<helper.index("depths = stagedDepth;")
assert "replay_native_game_pre_draw_depth(s,ctx," in bridge
assert "replay_native_game_pre_draw_depth(s,context," in bridge
print("01100 paired pre-Draw color/depth source and fallback regression PASS")
