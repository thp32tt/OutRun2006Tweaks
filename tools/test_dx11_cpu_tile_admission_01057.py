#!/usr/bin/env python3
"""01057 real game partial LockRect ticket is compatible with GPU tile completion."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'src/vr/d3d11/live_game_frame_bridge.cpp').read_text(encoding='utf-8')
h=(root/'src/vr/d3d11/native_game_cpu_tile_admission.hpp').read_text(encoding='utf-8')
copy=s[s.index('bool preserve_game_surface_copy('):s.index('bool begin_game_surface_cpu_write(')]
begin=s[s.index('bool begin_game_surface_cpu_write('):s.index('void finish_game_surface_cpu_write(')]
def linked(b,c,plan):
    try:
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
    except ValueError:
        return False
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

# 01058: a late D3D9 GPU tile LockRect/row-pitch/UnlockRect failure
# must retry exactly once through a *budgeted full-source* readback.
# This is a source-link mutation check, not a game/HMD runtime assertion.
def late_stage_recovery(c):
    try:
        admission=c.index('auto prepareFullReadback = [&]() noexcept -> bool {')
        full_cost=c.index('if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))',admission)
        full_gpu=c.index('game->GetRenderTargetData(',full_cost)
        staging=c.index('auto captureSourcePixels = [&]() noexcept -> bool {',full_gpu)
        tile_failure=c.index('if (!captureSourcePixels()) {',staging)
        retry=c.index('if (!tileSucceeded || !prepareFullReadback()) return false;',tile_failure)
        full_route=c.index('tileSucceeded=false;',retry)
        second=c.index('if (!captureSourcePixels()) return false;',full_route)
        upload=c.index('context->UpdateSubresource(',second)
        charged=c.index('tileSucceeded ? plannedReadbackBytes :',upload)
        return (admission<full_cost<full_gpu<staging<tile_failure<retry<
                full_route<second<upload<charged and
                'FAILED(readback->LockRect(' in c[staging:tile_failure] and
                'return copied && SUCCEEDED(unlocked);' in c[staging:tile_failure])
    except ValueError:
        return False
assert late_stage_recovery(copy)
for expression in [
    'if (!tileSucceeded || !prepareFullReadback()) return false;',
    'tileSucceeded=false;',
    'if (!captureSourcePixels()) return false;',
    'return copied && SUCCEEDED(unlocked);',
    'if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))',
]:
    assert not late_stage_recovery(copy.replace(expression,'/* removed */',1)), expression
print('PASS 01058 late tile staging failure -> full authenticated readback -> native GPU region')

# 01059: read back a genuine full-sized menu/car/race backbuffer through a
# private D3D9 RT if direct readback fails. Internal StretchRect MUST be guarded
# because the hooked R30 observer would otherwise reacquire State::mutex.
# Source-link/mutation validation only, NOT an HMD/game playback claim.
full=(root/'src/vr/d3d11/native_game_surface_full_readback.hpp').read_text(encoding='utf-8')
def game_full_readback_is_integrated(c, f):
    try:
        tile=c.index('const NativeOutputUploadScope internalTileCopyScope{};')
        captured=c.index('tileSucceeded = s.surfaceReplayTile.capture(',tile)
        admitted=c.index('if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))',captured)
        direct=c.index('if (FAILED(game->GetRenderTargetData(',admitted)
        guard=c.index('const NativeOutputUploadScope internalFullCopyScope{};',direct)
        fallback=c.index('s.surfaceReplayFull.capture(',guard)
        return (captured-tile < 180 and direct<guard<fallback and
                fallback-guard < 250 and
                'GameNativeFullSurfaceReadback surfaceReplayFull{};' in s and
                's.surfaceReplayFull.reset();' in s and
                '#include "native_game_surface_full_readback.hpp"' in s and
                'game->StretchRect(' in f and
                'game->GetRenderTargetData(' in f and
                'src.Pool != D3DPOOL_DEFAULT' in f and
                'dst.Pool != D3DPOOL_SYSTEMMEM' in f and
                'owner_ != game' in f and
                'width_ != width' in f and
                'format_ != format' in f)
    except ValueError:
        return False
assert game_full_readback_is_integrated(copy,full)
for token in (
    'const NativeOutputUploadScope internalTileCopyScope{};',
    'const NativeOutputUploadScope internalFullCopyScope{};',
    's.surfaceReplayFull.capture(',
):
    assert not game_full_readback_is_integrated(
        copy.replace(token,'/* MUTATED */',1),full), token
for token in ('game->StretchRect(', 'game->GetRenderTargetData(',
              'src.Pool != D3DPOOL_DEFAULT', 'dst.Pool != D3DPOOL_SYSTEMMEM',
              'owner_ != game', 'format_ != format'):
    assert not game_full_readback_is_integrated(
        copy,full.replace(token,'/* MUTATED */',1)),token
print('PASS 01059 native game full backbuffer staging and nested R30 hook suppression')
