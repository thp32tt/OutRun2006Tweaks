#!/usr/bin/env python3
"""01056 prove source tile budget precedes native copy, fallback pays full."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/'src/vr/d3d11/live_game_frame_bridge.cpp').read_text()
budget=(root/'src/vr/d3d11/native_game_surface_replay_budget.hpp').read_text()
body=source[source.index('bool preserve_game_surface_copy('):
            source.index('bool begin_game_surface_cpu_write(')]
def linked(s):
    guards=(
        'const bool tileCandidate = !preDrawCopy',
        'if (!s.surfaceReplayBudget.admits_bytes(plannedReadbackBytes))',
        's.surfaceReplayTile.capture(',
        'if (!tileSucceeded) {',
        'if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))',
        'game->GetRenderTargetData(',
        'context->CopySubresourceRegion(',
        's.surfaceReplayBudget.note_success_bytes(')
    return all(s.find(x)>=0 for x in guards) and all(
        s.index(a)<s.index(b) for a,b in zip(guards,guards[1:])) and (
        'tileSucceeded ? plannedReadbackBytes :' in s)
assert linked(body)
assert 'constexpr bool admits_bytes(std::uint64_t cost)' in budget
assert 'void note_success_bytes(std::uint64_t cost)' in budget
for token in (
    'if (!s.surfaceReplayBudget.admits_bytes(plannedReadbackBytes))',
    'if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))',
    's.surfaceReplayTile.capture(',
    'tileSucceeded ? plannedReadbackBytes :',
    's.surfaceReplayBudget.note_success_bytes('):
    assert not linked(body.replace(token,'/* destructive mutation */',1)),token
print('PASS 01056 real D3D9 source tile vs full fallback budget linkage')
