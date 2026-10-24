from pathlib import Path
s=Path("src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
h=Path("src/vr/d3d11/native_game_pre_draw_depth.hpp").read_text(encoding="utf-8")
assert "GameNativePreDrawDepth preDrawDepth{};" in s
assert "s.frameBatch.depthClearPending" in s
assert "s.preDrawDepth.record(" in s
assert "s.preDrawDepth.replay_ready(" in s
assert "s.clearColor.main_depth_still_bound(ds)" in s
assert s.count("replay_native_game_pre_draw_depth(s,")==2
assert "native_game_raster_partial_backbuffer_depth_clear(" in s
assert "context1->ClearView(s.diagnosticDepthView.Get(),value,&rect,1u)" in s
assert "auto staged=*this;" in h
assert "if(staged.count==kCapacity)return false;" in h
assert "classify_target_clear_rect" in h
assert "!(z>=0.f&&z<=1.f)" in h
print("01036 live game depth replay source regressions PASS")
