#!/usr/bin/env python3
"""01052 real D3D9 cold-start/Reset pre-Draw source -> native first Draw route."""
from pathlib import Path
s=(Path(__file__).resolve().parents[1] /
   'src/vr/d3d11/live_game_frame_bridge.cpp').read_text(encoding='utf-8')
begin=s.index('bool preserve_game_surface_copy(')
end=s.index('bool begin_game_surface_cpu_write(',begin)
copy=s[begin:end]
canonical=copy.index('backbuffer->GetDesc(&canonicalDesc)')
check=copy.index('GameNativePreDrawSurface::source_matches_canonical(',canonical)
predraw=copy.index('const bool preDrawCopy =',check)
postdraw=copy.index('const bool postDrawCopy =',predraw)
extent=copy.index('GameNativePreDrawSurface::capture_extent_allowed(',postdraw)
snapshot=copy.index('s.preDrawSurface.record_consuming(',extent)
assert canonical < check < predraw < postdraw < extent < snapshot
assert 'desc.Width != s.nativeWidth || desc.Height != s.nativeHeight' not in copy[:predraw]
assert 's.preDrawFills.discard(); // snapshot includes all earlier fills' in copy[snapshot:]
assert 'ScopedNativeGameGpuTransferInputs' in copy[copy.index('auto* device = s.backend.device()',snapshot):]
assert 'if (completingCpuWrite) s.cpuSurfaceReplay.reset();' in copy
assert s.count('replay_native_game_pre_draw_surface(s,') >= 2 # SM3 and FVF
assert 'if (!s.preDrawSurface.matches(owner,target,w,h,fmt))' not in s # explicit validation below
assert '!s.preDrawSurface.matches(owner,target,w,h,fmt)' in s
assert 'void observe_game_surface_mutation(' in s
print('01052 cold/Reset source and post-Draw fallback structural contract PASS')