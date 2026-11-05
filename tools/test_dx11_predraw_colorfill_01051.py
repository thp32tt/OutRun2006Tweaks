#!/usr/bin/env python3
"""Prove native full main ColorFill retires only owned pre-Draw staging."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'src/vr/d3d11/live_game_frame_bridge.cpp'
s=p.read_text(encoding='utf8')
a=s.index('bool preserve_game_color_fill(')
b=s.index('void observe_scene_boundary(',a)
code=s[a:b]
owner=code.index('const bool sameGameBackbuffer =')
open_ticket=code.index('if (sameGameBackbuffer && s.cpuSurfaceReplay.active())',owner)
full=code.index('GameNativeSourceMutation::mirrors_full_color_fill(',open_ticket)
retire=code.index('s.preDrawSurface.discard_if_canonical_full_write(',full)
assert owner<open_ticket<full<retire
assert 's.preDrawSurface.discard();' not in code[owner:retire]
print('01051 native preDraw foreign ColorFill sequence PASS')
