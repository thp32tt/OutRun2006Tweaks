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
assert copy.index('s.preDrawSurface.record(') < copy.index('s.surfaceReplayBudget.note_success(')
assert copy.index('CopySubresourceRegion(') < copy.rindex('s.surfaceReplayBudget.note_success(')
assert 's.surfaceReplayCount' not in s
assert s.count('s.surfaceReplayBudget.reset();') == 6
assert 'kMaxBytes - bytes' in h and 'kMaxOperations' in h
assert 'GameNativePreDrawSurface::source_matches_canonical(' in copy
assert 's.cpuSurfaceReplay.reset()' in s
print('01053 canonical full-readback multi-copy continuity and fail-closed budget PASS')
