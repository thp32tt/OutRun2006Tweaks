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
    target = r.split("constexpr bool record_target_clear(", 1)[1]
    return all((
        "preserve_game_partial_target_clear(" in h,
        "if ((flags & D3DCLEAR_TARGET) && !nativePartialClear)" in h,
        "s.preDrawFills.record_target_clear(" in b,
        "count <= GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects" in b,
        "count > GameNativePreDrawFills::kMaxPreDrawTargetClearSourceRects" in b,
        # The post-Draw original D3D9 rect intake was widened to 128 only
        # when an exact union fits the unchanged 32 native GPU regions.
        "count > GameNativePostDrawClearBatch::kMaxSourceRects" in b,
        "GameNativePostDrawClearBatch::build(" in b,
        "rectCount > kMaxPreDrawTargetClearSourceRects" in r,
        "!GameNativeClearCoverage::covers_whole(" in b,
        "if (sameBackbuffer &&" in b,
        "if (clearZ)" in b,
        "GameNativePreDrawCombinedClear::record(" in b,
        "s.frameBatch.accepts_full(s.sourceDrawsThisFrame)" in b,
        "GameNativeSourceMutation::classify_target_clear_rect(" in r,
        "GameNativePreDrawFills staged = *this;" in r,
        "*this = staged;" in target,
        draw.count("game_native_replay_pre_draw_fills(")>=2,
        "native_game_raster_partial_backbuffer_color_clear(" in draw,
    ))
assert connected(region,source,hook)
for old,new in (
    ("s.preDrawFills.record_target_clear(","s.preDrawFills.reject_clear("),
    ("if (sameBackbuffer &&","if (false && sameBackbuffer &&"),
    ("s.frameBatch.accepts_full(s.sourceDrawsThisFrame)","true"),
    ("!GameNativeClearCoverage::covers_whole(","GameNativeClearCoverage::covers_whole("),
):
    assert old in region
    assert not connected(region.replace(old,new,1),source,hook),old
# 01104 added an independent ColorFill transaction before TARGET Clear.
# Mutate only the TARGET recorder; a ColorFill commit cannot mask its loss.
head, target = source.split("constexpr bool record_target_clear(", 1)
assert "*this = staged;" in target
mutated = head + "constexpr bool record_target_clear(" + target.replace(
    "*this = staged;", "/*partial*/", 1)
assert not connected(region, mutated, hook)
print("01035 native game pre-Draw TARGET Clear hook/SM3/FVF GPU integration PASS")
