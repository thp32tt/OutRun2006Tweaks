#!/usr/bin/env python3
"""01103 actual-game pre-Draw Z rectangle compaction, native GPU depth parity."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
header=(root/"src/vr/d3d11/native_game_pre_draw_depth.hpp").read_text()
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
combined=(root/"src/vr/d3d11/native_game_pre_draw_combined_clear.hpp").read_text()
assert "kMaxSourceRects=" in header
assert "GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects" in header
assert "n>kMaxSourceRects" in header
assert "std::uint32_t retained=0u;" in header
assert "if(retained>=kCapacity)return false;" in header
# 01106 keeps the immutable 01103 transaction staging but trims a
# superseded outer edge exactly; interior overlaps remain ordered.
assert "Tile prior=staged.tiles[j];" in header
assert "if(!covers(next,prior)) {" in header
assert "(void)game_native_trim_partially_overwritten(prior,next);" in header
assert "staged.tiles[output++]=prior;" in header
assert "if(staged.count==kCapacity)return false;" in header
assert "auto staged=*this;" in header
assert "if(staged.count && staged.tiles[staged.count-1u].z==z &&" in header
start=bridge.index("bool observe_game_depth_clear(")
end=bridge.index("void observe_game_clear(",start)
z=bridge[start:end]
assert "const bool beforeFirstDepth = partialDepth &&" in z
assert "s.frameBatch.depthClearPending" in z
assert "s.clearColor.main_depth_still_bound(" in z
assert "count <= GameNativePreDrawDepth::kMaxSourceRects" in z
assert "GameNativeMainStencilClear::may_ignore_pre_draw(" in z
assert "return s.preDrawDepth.record(owner," in z
p=bridge[bridge.index("bool preserve_game_partial_target_clear("):start]
assert "GameNativePreDrawCombinedClear::record(" in p
assert "count <= GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects" in p
assert "auto stagedColor = colors;" in combined
assert "auto stagedDepth = depths;" in combined
assert combined.index("stagedDepth.record(")<combined.index("colors = stagedColor;")
print("01103 authentic Z-source compaction and combined GPU replay linkage PASS")
