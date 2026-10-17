#!/usr/bin/env python3
"""Verify real game Clear->native depth Draw and safe fallback with mutations."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]
c=(p/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
h=(p/"src/vr/d3d9/stereo_renderer.cpp").read_text()
b=(p/"src/vr/d3d11/native_game_frame_batch.hpp").read_text()
wf=(p/".github/workflows/dx11-fast-structural.yml").read_text()
def valid(code,hook,batch):
 a=code.find("bool observe_game_depth_clear(")
 z=code.find("void observe_game_clear(",a)
 sec=code[a:z]
 draw=code[code.find("bool submit("):code.find("bool observe_source_device(")]
 return all((
    a>=0 and z>a,
    "s.frameBatch.submitted == 0u || s.frameBatch.stopped" in sec,
    "constexpr DWORD kDepthStencilFlags = D3DCLEAR_ZBUFFER | D3DCLEAR_STENCIL;" in sec,
    "(flags & ~kDepthStencilFlags) != 0u" in sec,
    "if (clearZ) s.frameBatch.note_full_depth_clear(z);" in sec,
    "GameNativeMainStencilClear::may_ignore(" in sec,
    "targetIdentity.Get() != backbufferIdentity.Get()" in sec,
    "dsDesc.Width != bbDesc.Width" in sec,
    "GameNativeClearCoverage::covers_whole(" in sec,
    "s.frameBatch.note_full_depth_clear(z);" in sec,
    "s.frameBatch.depth_clear_value(output.nativeDepthOrderingMode != 0u)" in draw,
    "s.frameBatch.consume_depth_clear();" in draw,
    "observe_game_depth_clear(" in hook,
    "observe_scene_boundary(device);" in hook,
    "depthClearPending = false;" in batch,
 ))
assert valid(c,h,b)
for old,new in (
 ("s.frameBatch.note_full_depth_clear(z);","s.frameBatch.abort();"),
 ("GameNativeClearCoverage::covers_whole(","GameNativeClearCoverage::skipped("),
 ("s.frameBatch.consume_depth_clear();","/* removed */"),
 ("if (clearZ) s.frameBatch.note_full_depth_clear(z);","/* suppress real Z */"),
 ("(flags & ~kDepthStencilFlags) != 0u","false /* allow TARGET */"),
):
 mutant=c.replace(old,new,1)
 assert mutant!=c and not valid(mutant,h,b), old
assert not valid(c,h.replace("observe_game_depth_clear(","skipped_clear(",1),b)
assert "python tools/test_dx11_depth_only_clear_00732.py" in wf
assert "tools/dx11_depth_only_clear_00732.cpp" in wf
print("00732 real game full Z-only Clear -> native depth Draw/color retention PASS")
