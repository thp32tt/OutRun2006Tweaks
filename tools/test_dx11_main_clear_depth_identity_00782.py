#!/usr/bin/env python3
"""DX11 00782 source-hook, main Z identity and partial stencil regression."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]
bridge=(p/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
guard=(p/"src/vr/d3d11/native_game_main_stencil_clear.hpp").read_text()
hook=(p/"src/vr/d3d9/stereo_renderer.cpp").read_text()
workflow=(p/".github/workflows/dx11-fast-structural.yml").read_text()
scope=bridge.split("bool observe_game_depth_clear(",1)[1].split("void observe_game_clear(",1)[0]
def valid(s,g,h):
    return all((
        "const bool coversDepth = GameNativeClearCoverage::covers_whole(" in s,
        "GameNativeMainStencilClear::preserves_clear_coverage(clearZ, coversDepth)" in s,
        "FAILED(depth.As(&depthIdentity)) || !depthIdentity" in s,
        "s.clearColor.main_depth_still_bound(" in s,
        # Full-Z requires the original coverage proof; the newly supported
        # partial-Z branch has independent D32/native/context validation.
        "const bool partialDepth = clearZ && !coversDepth;" in s,
        "if (!sameMainDepthStencil ||" in s,
        "(clearZ && !compatibleCoverage && !partialDepth))" in s,
        "if (partialDepth) {" in s,
        "if (clearStencil || !continuingFullNativeDraw ||" in s,
        "native_game_partial_depth_ready(" in s,
        "sameMainDepthStencil, compatibleCoverage," in s,
        "if (clearZ) s.frameBatch.note_full_depth_clear(z);" in s,
        "return !clearsDepth || coversWholeDepth;" in g,
        "GameNativeMainStencilClear::may_ignore(" in s,
        "live_game_frame::observe_game_depth_clear(" in h,
        "live_game_frame::observe_game_clear(" in h,
        "python tools/test_dx11_main_clear_depth_identity_00782.py" in workflow,
        "tools/dx11_main_clear_depth_identity_00782.cpp" in workflow,
    ))
assert valid(scope,guard,hook)
for old,new in (
    ("if (!sameMainDepthStencil ||", "if (false ||"),
    ("(clearZ && !compatibleCoverage && !partialDepth))", "(false))"),
    ("const bool partialDepth = clearZ && !coversDepth;",
     "const bool partialDepth = true;"),
    ("native_game_partial_depth_ready(", "skip_native_D32_ownership_check("),
    ("FAILED(depth.As(&depthIdentity)) || !depthIdentity","false"),
    ("GameNativeMainStencilClear::preserves_clear_coverage(clearZ, coversDepth)","true"),
    ("if (clearZ) s.frameBatch.note_full_depth_clear(z);","/* discard depth */"),
):
    assert old in scope and not valid(scope.replace(old,new,1),guard,hook),old
assert not valid(scope,guard.replace("return !clearsDepth || coversWholeDepth;","return true;"),hook)
assert not valid(scope,guard,hook.replace("live_game_frame::observe_game_depth_clear(","skip_native_depth_clear(",1))
print("00782 main stencil partial continuity, canonical Z and fallback PASS")
