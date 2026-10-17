#!/usr/bin/env python3
"""00781 native whole-main STENCIL Clear, linked rendering and fail-closed D3D9."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
b=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
h=(r/"src/vr/d3d9/stereo_renderer.cpp").read_text()
g=(r/"src/vr/d3d11/native_game_main_stencil_clear.hpp").read_text()
wf=(r/".github/workflows/dx11-fast-structural.yml").read_text()
def valid(bridge,hook,guard):
    main=bridge.split("bool observe_game_depth_clear(",1)[1].split("void observe_game_clear(",1)[0]
    color=bridge.split("void observe_game_clear(",1)[1].split("void observe_unavailable_game_draw(",1)[0]
    raster=bridge.split("bool supported_game_state(",1)[1].split("bool submit(",1)[0]
    return all((
      "const bool clearZ = (flags & D3DCLEAR_ZBUFFER) != 0u;" in main,
      "(flags & ~kDepthStencilFlags) != 0u" in main,
      "(clearZ && !(z >= 0.0f && z <= 1.0f))" in main,
      "GameNativeClearCoverage::covers_whole(" in main,
      "s.clearColor.main_depth_still_bound(" in main,
      "GameNativeMainStencilClear::may_ignore(" in main,
      "if (clearZ) s.frameBatch.note_full_depth_clear(z);" in main,
      "GameNativeMainStencilClear::may_ignore(" in color,
      "mainDepthIdentity != 0u" in color,
      "if ((clearStencil && !ignoreStencil) ||" in color,
      "s.frameBatch.abort(); // failed proof: original D3D9 lives" in color,
      "GetRenderState(D3DRS_STENCILFUNC, &stencilFunc)" in raster,
      "GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)" in raster,
      "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)" in raster,
      "stencil_equivalent_to_disabled(" in raster,
      "!clip || fog || fillMode != D3DFILL_SOLID)" in raster,
      "live_game_frame::observe_game_depth_clear(" in hook,
      "live_game_frame::observe_game_clear(" in hook,
      "nativeFullFrame && originalMainColorSeed &&" in guard,
      "sameMainDepthStencil && fullClearCoverage && nativeBatchOpen;" in guard,
      "python tools/test_dx11_main_stencil_clear_game_frame_00781.py" in wf,
      "tools/dx11_main_stencil_clear_game_frame_00781.cpp" in wf,
    ))
assert valid(b,h,g)
def mutant(which,old,new):
    start="bool observe_game_depth_clear(" if which=="main" else "void observe_game_clear("
    end="void observe_game_clear(" if which=="main" else "void observe_unavailable_game_draw("
    pre,rest=b.split(start,1)
    sec,suf=rest.split(end,1)
    assert old in sec,old
    return pre+start+sec.replace(old,new,1)+end+suf
for scope,old,new in (
 ("main","GameNativeClearCoverage::covers_whole(","GameNativeClearCoverage::skip("),
 ("main","s.clearColor.main_depth_still_bound(","true /* unproven */("),
 ("main","if (clearZ) s.frameBatch.note_full_depth_clear(z);","/* omitted Z */"),
 ("color","mainDepthIdentity != 0u","true /* foreign Z */"),
 ("color","if ((clearStencil && !ignoreStencil) ||","if ((clearStencil && ignoreStencil) ||"),
 ("color","s.frameBatch.abort(); // failed proof: original D3D9 lives","s.frameBatch.reset(); // fail open"),
):
    assert not valid(mutant(scope,old,new),h,g),old
# Losing the new live source-side stencil proof must also fail this Clear
# regression: original D3D9 Draw, not a native scene, wins on conditional Z/S.
assert not valid(b.replace("stencil_equivalent_to_disabled(",
                           "stencil_unconditionally_ignored(",1),h,g)
assert not valid(b,h,g.replace("sameMainDepthStencil && fullClearCoverage && nativeBatchOpen;","true; /* unproved */"))
assert not valid(b,h.replace("live_game_frame::observe_game_depth_clear(","live_game_frame::skip_clear(",1),g)
print("00781 real game main STENCIL, Z|STENCIL, menu-race Draw+Present fallback PASS")
