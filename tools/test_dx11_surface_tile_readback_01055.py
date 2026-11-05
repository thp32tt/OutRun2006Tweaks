#!/usr/bin/env python3
"""01055: Post-Draw cropped real game RT readback, original D3D9 fallback."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'src/vr/d3d11/live_game_frame_bridge.cpp').read_text(encoding='utf-8')
t=(root/'src/vr/d3d11/native_game_surface_tile_readback.hpp').read_text(encoding='utf-8')
copy=s[s.index('bool preserve_game_surface_copy('):s.index('bool begin_game_surface_cpu_write(')]
assert 'GameNativeSurfaceTileReadback surfaceReplayTile' in s
assert 's.surfaceReplayTile.reset();' in s[s.index('void before_game_reset('):]
assert copy.index('actualIdentity.Get() != backbufferIdentity.Get()') < copy.index('s.surfaceReplayTile.capture(')
assert copy.index('s.frameBatch.publishable(s.pending)') < copy.index('s.surfaceReplayTile.capture(')
assert copy.index('const auto region = preDrawCopy') < copy.index('s.surfaceReplayTile.capture(')
assert 'const bool tileCandidate = !preDrawCopy' in copy
assert 'if (tileCandidate) {' in copy
assert 'tileSucceeded = s.surfaceReplayTile.capture(' in copy
assert 'auto prepareFullReadback = [&]() noexcept -> bool {' in copy
assert 'if (!tileSucceeded && !prepareFullReadback()) return false;' in copy
assert 'if (!tileSucceeded || !prepareFullReadback()) return false;' in copy
assert copy.index('if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))') < copy.index('game->GetRenderTargetData(')
assert copy.index('game->GetRenderTargetData(') < copy.index('if (!tileSucceeded && !prepareFullReadback()) return false;')
assert 'game->GetRenderTargetData(' in copy
assert 'readback->LockRect(' in copy
assert 'readback->UnlockRect()' in copy
assert 'GameNativeSurfaceTilePlan::source_x(region, tileSucceeded)' in copy
assert 'GameNativeSurfaceTilePlan::source_y(region, tileSucceeded)' in copy
assert copy.index('if (preDrawCopy) {') > copy.index('readback->UnlockRect()')
assert 'game->StretchRect(' in t and 'game->GetRenderTargetData(' in t
assert t.index('game->StretchRect(') < t.index('game->GetRenderTargetData(')
assert 'source, &area, gpu_.Get(), nullptr, D3DTEXF_NONE' in t
assert 'game->CreateRenderTarget(' in t
assert 'game->CreateOffscreenPlainSurface(' in t
assert 'void reset() noexcept' in t
assert 's.surfaceReplayBudget.note_success_bytes(' in copy
assert 'if (!s.surfaceReplayBudget.admits(desc.Width,desc.Height))' in copy
assert 's.preDrawSurface.record_consuming(' in copy
print('01055 cropped post-Draw game tile + original full readback fallback PASS')
