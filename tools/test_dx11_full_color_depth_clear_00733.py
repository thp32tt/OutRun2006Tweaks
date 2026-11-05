#!/usr/bin/env python3
"""Regression: actual D3D9 color+Z backbuffer Clear feeds D3D11 full game Draw."""
from pathlib import Path
import re
p=Path(__file__).resolve().parents[1]
c=(p/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
h=(p/"src/vr/d3d11/live_game_frame_bridge.hpp").read_text()
r=(p/"src/vr/d3d9/stereo_renderer.cpp").read_text()
helper=(p/"src/vr/d3d11/native_game_full_color_depth.hpp").read_text()
wf=(p/".github/workflows/dx11-fast-structural.yml").read_text()
def valid(cpp,hook,policy):
 start=cpp.index("void observe_game_clear(")
 stop=cpp.index("void observe_unavailable_game_draw(",start)
 s=cpp[start:stop]
 draw=cpp[cpp.index("bool submit("):cpp.index("bool observe_source_device(")]
 return all((
   "D3DCOLOR color, float z) noexcept" in h,
   "D3DCOLOR color, float z) noexcept" in s,
   "live_game_frame::observe_game_clear(" in hook,
   # Verify each exact hooked callee with its own z argument.  Searching for
   # the unqualified argument list can match the *other* Clear call and
   # accidentally accept a dropped Z in observe_game_clear.
   re.search(r"live_game_frame::observe_game_clear\(\s*device,\s*count,\s*rects,\s*flags,\s*color,\s*z\);", hook) is not None,
   re.search(r"live_game_frame::preserve_game_partial_target_clear\(\s*device,\s*count,\s*rects,\s*flags,\s*color,\s*z\);", hook) is not None,
   "if (SUCCEEDED(result)) {" in hook,
   "if (wholeBackbuffer && env_full_game_opt_in())" in s,
   "s.frameBatch.reset();" in s,
   "s.pending = false;" in s,
   "game->GetDepthStencilSurface(" in s,
   "depthDesc.Width == bbDesc.Width" in s,
   "depthDesc.Height == bbDesc.Height" in s,
   "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE" in s,
   "GameNativeFullColorDepthClear::can_mirror(" in s,
   "s.frameBatch.note_full_depth_clear(z);" in s,
   "s.frameBatch.abort();" in s,
   "if ((clearStencil && !ignoreStencil) ||" in s,
   "mainDepthIdentity != 0u" in s,
   0 <= s.find("s.frameBatch.reset();") < s.find("s.frameBatch.note_full_depth_clear(z);"),
   "s.frameBatch.depth_clear_value(output.nativeDepthOrderingMode != 0u)" in draw,
   "s.frameBatch.consume_depth_clear();" in draw,
   "depthCleared && !stencilCleared && depthCompatible &&" in policy,
   "z >= 0.0f && z <= 1.0f" in policy,
   "python tools/test_dx11_full_color_depth_clear_00733.py" in wf,
   "tools/dx11_full_color_depth_clear_00733.cpp" in wf,
 ))
assert valid(c,r,helper)
for old,new in (
 ("s.frameBatch.note_full_depth_clear(z);","s.frameBatch.consume_depth_clear();"),
 ("s.frameBatch.abort(); // failed proof: original D3D9 lives",
   "s.frameBatch.reset(); // fail open"),
 ("if ((clearStencil && !ignoreStencil) ||",
   "if ((clearStencil && ignoreStencil) ||"),
 ("depthDesc.Width == bbDesc.Width","depthDesc.Width != bbDesc.Width"),
 ("GameNativeFullColorDepthClear::can_mirror(","GameNativeFullColorDepthClear::ignored("),
):
 i=c.index("void observe_game_clear(");j=c.index("void observe_unavailable_game_draw(",i)
 s=c[i:j];assert old in s
 assert not valid(c[:i]+s.replace(old,new,1)+c[j:],r,helper),old
for callee in ("observe_game_clear", "preserve_game_partial_target_clear"):
 pattern = (rf"(live_game_frame::{callee}\(\s*device,\s*count,\s*rects,\s*flags,\s*color),\s*z(\s*\);)")
 mutated, count = re.subn(pattern, r"\1\2", r, count=1)
 assert count == 1, f"missing exact {callee} callsite for destructive Z mutation"
 assert not valid(c, mutated, helper), f"Z argument omission escaped: {callee}"
assert not valid(c,r,helper.replace("!stencilCleared","stencilCleared"))
assert not valid(c,r,helper.replace("z >= 0.0f && z <= 1.0f","true"))
print("00733 full-resolution game color+Z Clear native depth/fallback PASS")
