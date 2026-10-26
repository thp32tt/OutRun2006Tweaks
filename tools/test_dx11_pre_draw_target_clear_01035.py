#!/usr/bin/env python3
"""Real Clear hook -> pre-Draw TARGET region recorder -> both D3D11 GPU paths."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hook=(root/"src/vr/d3d9/stereo_renderer.cpp").read_text()
source=(root/"src/vr/d3d11/native_game_source_mutation.hpp").read_text()
start=bridge.index("bool preserve_game_partial_target_clear(")
end=bridge.index("bool preserve_game_color_fill(",start)
region=bridge[start:end]
draw=bridge[bridge.index("game_native_replay_pre_draw_fills("):]
def connected(b,r,h):
    return all((
        "preserve_game_partial_target_clear(" in h,
        "if ((flags & D3DCLEAR_TARGET) && !nativePartialClear)" in h,
        "s.preDrawFills.record_target_clear(" in b,
        "count <= GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects" in b,
        "count > GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects" in b,
        "count > GameNativeSourceMutation::kMaxPartialTargetClearRects" in b,
        "rectCount > kMaxPreDrawTargetClearSourceRects" in r,
        "!GameNativeClearCoverage::covers_whole(" in b,
        "!clearZ && !clearStencil && sameBackbuffer" in b,
        "s.frameBatch.accepts_full(s.sourceDrawsThisFrame)" in b,
        "GameNativeSourceMutation::classify_target_clear_rect(" in r,
        "GameNativePreDrawFills staged = *this;" in r,
        "*this = staged;" in r,
        draw.count("game_native_replay_pre_draw_fills(")>=2,
        "native_game_raster_partial_backbuffer_color_clear(" in draw,
    ))
assert connected(region,source,hook)
for old,new in (
    ("s.preDrawFills.record_target_clear(","s.preDrawFills.reject_clear("),
    ("!clearZ && !clearStencil && sameBackbuffer","sameBackbuffer"),
    ("s.frameBatch.accepts_full(s.sourceDrawsThisFrame)","true"),
    ("!GameNativeClearCoverage::covers_whole(","GameNativeClearCoverage::covers_whole("),
):
    assert old in region
    assert not connected(region.replace(old,new,1),source,hook),old
assert not connected(region,source.replace("*this = staged;","/*partial*/",1),hook)
print("01035 native game pre-Draw TARGET Clear hook/SM3/FVF GPU integration PASS")
