#!/usr/bin/env python3
"""Verify real D3D9 source replay has bounded burst continuity at both APIs."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'src/vr/d3d11/live_game_frame_bridge.cpp').read_text(encoding='utf-8')
h=(root/'src/vr/d3d11/native_game_surface_replay_budget.hpp').read_text(encoding='utf-8')
copy=s[s.index('bool preserve_game_surface_copy('):s.index('bool begin_game_surface_cpu_write(')]
write=s[s.index('bool begin_game_surface_cpu_write('):s.index('void finish_game_surface_cpu_write(')]
assert 'GameNativeSurfaceReplayBudget surfaceReplayBudget' in s
assert 's.surfaceReplayBudget.admits(desc.Width, desc.Height)' in copy
assert '!s.surfaceReplayBudget.admits(desc.Width, desc.Height)' in write
assert copy.count('s.surfaceReplayBudget.note_success(desc.Width, desc.Height);') == 2
assert copy.index('GetRenderTargetData(') < copy.index('s.surfaceReplayBudget.note_success(')
assert copy.index('s.preDrawSurface.record_consuming(') < copy.index('s.surfaceReplayBudget.note_success(')
assert copy.index('CopySubresourceRegion(') < copy.rindex('s.surfaceReplayBudget.note_success(')
assert 's.surfaceReplayCount' not in s
assert s.count('s.surfaceReplayBudget.reset();') == 6
assert 'kMaxBytes - bytes' in h and 'kMaxOperations' in h
assert 'GameNativePreDrawSurface::source_matches_canonical(' in copy
assert 's.cpuSurfaceReplay.reset()' in s
pre=(root/'src/vr/d3d11/native_game_pre_draw_surface.hpp').read_text(encoding='utf-8')
# 01054 authentic D3D9 GetRenderTargetData writes mutable full-frame bytes.
# The existing live-game bridge now resolves the new in-place overload.
pre_draw=copy[copy.index('if (preDrawCopy) {'):copy.index('auto* device = s.backend.device();')]
assert 's.preDrawSurface.record_consuming(owner,' in pre_draw
assert 's.surfaceReplayPixels)) return false;' in pre_draw
assert 'record_consuming(std::uintptr_t device' in pre
assert '&source == &pixels' in pre
assert 'pixels.swap(source);' in pre
assert pre.count('[[nodiscard]] bool record(') == 1
# The original mutable 01049 probe modifies its source vector AFTER record():
# using a consuming overload by default segfaults on an emptied vector.
assert '[[nodiscard]] bool record_consuming(' in pre
assert 'const std::vector<std::uint8_t>& source) noexcept' in pre
assert pre.index('pixels.swap(source);') < pre.index('const std::vector<std::uint8_t>& source')
assert pre_draw.index('s.preDrawSurface.record_consuming(') < pre_draw.index('s.surfaceReplayBudget.note_success(')
assert pre_draw.index('s.preDrawFills.discard()') < pre_draw.index('s.cpuSurfaceReplay.reset()')
print('01054 native first Draw source allocation rotation and fallback PASS')
print('01053 canonical full-readback multi-copy continuity and fail-closed budget PASS')