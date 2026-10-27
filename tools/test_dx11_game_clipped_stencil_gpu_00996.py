#!/usr/bin/env python3
"""00996 native main TARGET/Z/STENCIL clipped Clear conversion source contract."""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
b = (r / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
h = (r / "src/vr/d3d11/native_game_main_stencil_clear.hpp").read_text()
union = (r / "src/vr/d3d11/native_game_post_draw_clear_batch.hpp").read_text()
hook = (r / "src/vr/d3d9/stereo_renderer.cpp").read_text()
wf = (r / ".github/workflows/dx11-fast-structural.yml").read_text()
target = b.split("bool preserve_game_partial_target_clear(",1)[1].split(
    "bool preserve_game_color_fill(",1)[0]
depth = b.split("bool observe_game_depth_clear(",1)[1].split(
    "void observe_game_clear(",1)[0]
def admissible(t=target, d=depth, header=h, rect_union=union):
    return all((
        "const bool clearStencil = (flags & D3DCLEAR_STENCIL) != 0u;" in t,
        "(flags & D3DCLEAR_TARGET) == 0u" in t,
        "(flags & ~(D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER |" in t,
        "GameNativePostDrawClearBatch::build(" in t,
        "GameNativePostDrawClearBatch::build(" in d,
        "GameNativeSourceMutation::classify_target_clear_rect(" in rect_union,
        "game_native_merge_ordered_overwrite(" in rect_union,
        "used > kMaxSourceRects" in rect_union,
        "gpu_chunk_size(" in rect_union,
        "remaining < kMaxGpuRegions" in rect_union,
        "regions.data() + start, chunk" in t,
        "regions.data() + start, chunk" in d,
        "nativeStencilDepthReady = !clearStencil ||" in t,
        "native_game_partial_depth_ready(" in t,
        "GameNativeMainStencilClear::may_ignore_cropped(" in t,
        "if (!nativeDepthReady || !nativeStencilDepthReady ||" in t,
        "native_game_raster_partial_backbuffer_target_depth_clear(" in t,
        "native_game_raster_partial_backbuffer_color_clear(" in t,
        "if (clearZ && hasClearView)" in t,
        "const bool clippedStencilSafe = partialDepth &&" in d,
        "const bool preDrawStencilSafe = beforeFirstDepth &&" in d,
        "GameNativeMainStencilClear::may_ignore_pre_draw(" in d,
        "GameNativeMainStencilClear::may_ignore_cropped(" in d,
        "if (!wholeStencilSafe && !clippedStencilSafe &&\n                !preDrawStencilSafe) return false;" in d,
        "if (!continuingFullNativeDraw ||" in d,
        "native_game_raster_partial_backbuffer_depth_clear(" in d,
        "sameMainDepthStencil && liveNativeDraw &&" in header,
        "boundedSourceRects && ownedNativeDepthReady;" in header,
        "preserve_game_partial_target_clear(" in hook,
        "observe_game_depth_clear(" in hook,
        "python tools/test_dx11_game_clipped_stencil_gpu_00996.py" in wf,
    ))
assert admissible()
for key, old, new in (
    ("target","nativeStencilDepthReady = !clearStencil ||","nativeStencilDepthReady = true ||"),
    ("target","if (!nativeDepthReady || !nativeStencilDepthReady ||","if (!nativeDepthReady || false ||"),
    ("rect_union","GameNativeSourceMutation::classify_target_clear_rect(","GameNativeSourceMutation::skip_rect_clip("),
    ("rect_union","remaining < kMaxGpuRegions","return remaining"),
    ("target","regions.data() + start, chunk","regions.data(), nativeRegionCount"),
    ("target","native_game_raster_partial_backbuffer_target_depth_clear(","native_game_raster_partial_backbuffer_color_clear_only("),
    ("depth","const bool clippedStencilSafe = partialDepth &&","const bool clippedStencilSafe = true &&"),
    ("depth","if (!wholeStencilSafe && !clippedStencilSafe &&\n                !preDrawStencilSafe) return false;","/* ignore wrong-owner stencil */"),
    ("depth","native_game_raster_partial_backbuffer_depth_clear(","noop_native_depth("),
):
    section = target if key == "target" else (
        depth if key == "depth" else union)
    assert old in section
    assert not admissible(
        t=section.replace(old,new,1) if key == "target" else target,
        d=section.replace(old,new,1) if key == "depth" else depth,
        rect_union=section.replace(old,new,1)
            if key == "rect_union" else union), key
assert not admissible(header=h.replace(
    "sameMainDepthStencil && liveNativeDraw &&",
    "true /* unsafe depth owner */ &&",1))
print("00996 clipped TARGET/Z/STENCIL native main GPU replay: PASS_STATIC")
