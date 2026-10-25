#!/usr/bin/env python3
"""01057 real game partial LockRect ticket is compatible with GPU tile completion."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'src/vr/d3d11/live_game_frame_bridge.cpp').read_text(encoding='utf-8')
h=(root/'src/vr/d3d11/native_game_cpu_tile_admission.hpp').read_text(encoding='utf-8')
copy=s[s.index('bool preserve_game_surface_copy('):s.index('bool begin_game_surface_cpu_write(')]
begin=s[s.index('bool begin_game_surface_cpu_write('):s.index('void finish_game_surface_cpu_write(')]
def linked(b,c,plan):
    start=b.index('const bool preDrawWrite =')
    post=b.index('const bool postDrawWrite =',start)
    cost=b.index('GameNativeCpuTileAdmission::planned_bytes(',post)
    check=b.index('!s.surfaceReplayBudget.admits_bytes(plannedReadbackBytes)',cost)
    ticket=b.index('s.cpuSurfaceReplay.begin(owner,',check)
    complete=c.index('const bool tileCandidate = !preDrawCopy')
    copy_cost=c.index('GameNativeCpuTileAdmission::planned_bytes(',complete)
    full_fallback=c.index('if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))',copy_cost)
    gpu=c.index('context->CopySubresourceRegion(',full_fallback)
    charged=c.rindex('s.surfaceReplayBudget.note_success_bytes(')
    return (start<post<cost<check<ticket and
            'preDrawWrite || !postDrawWrite' in b[cost:check] and
            complete<copy_cost<full_fallback<gpu<charged and
            'tileSucceeded ? plannedReadbackBytes :' in c and
            'GameNativeSurfaceTilePlan::eligible(' in plan and
            'GameNativeSurfaceReplayBudget::full_readback_bytes(' in plan)
assert linked(begin,copy,h)
for item,where in [
    ('preDrawWrite || !postDrawWrite','begin'),
    ('!s.surfaceReplayBudget.admits_bytes(plannedReadbackBytes)','begin'),
    ('GameNativeCpuTileAdmission::planned_bytes(','copy'),
    ('if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))','copy'),
    ('tileSucceeded ? plannedReadbackBytes :','copy'),
    ('GameNativeSurfaceTilePlan::eligible(','header'),
]:
    b,c,p=begin,copy,h
    if where=='begin': b=b.replace(item,'/* removed */',1)
    if where=='copy': c=c.replace(item,'/* removed */',1)
    if where=='header': p=p.replace(item,'/* removed */',1)
    assert not linked(b,c,p), item
print('PASS 01057 partial game CPU/GDI tile budget and complete fallback')
