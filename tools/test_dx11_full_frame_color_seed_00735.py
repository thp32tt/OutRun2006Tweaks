#!/usr/bin/env python3
"""DX11 00735: verified game full TARGET Clear -> full native Draw and fail-closed fallback."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
batch=(root/"src/vr/d3d11/native_game_frame_batch.hpp").read_text()
hook=(root/"src/vr/d3d9/stereo_renderer.cpp").read_text()
flow=(root/".github/workflows/dx11-fast-structural.yml").read_text()
color_hdr=(root/"src/vr/d3d11/native_game_clear_color.hpp").read_text()
probe=(root/"tools/dx11_full_frame_color_seed_00735.cpp").read_text()
def retains_verified_offscreen_clear(h: str, p: str) -> bool:
    start = h.find("constexpr bool preserves_offscreen_color_only(")
    end = h.find("// Disable writes to the absent X8 alpha plane",start)
    if start < 0 or end < 0: return False
    method = h[start:end]
    return all(token in method for token in (
        "preserves_offscreen_color_only(",
        "colorOnly && !batchStopped",
        "matches(device, backbuffer)",
        "target != 0u && target != backbuffer",
    )) and all(token in p for token in (
        "color.preserves_offscreen_color_only(game, back, 0x300u, true, batch.stopped)",
        "batch.accepts_full_on_source_target(1u, color.matches(game, back))",
        "batch.scene_boundary();",
        "!batch.publishable_full(true, 1u)",
    ))
assert retains_verified_offscreen_clear(color_hdr,probe), "offscreen menu/race Clear must retain only verified color-only frame"
for broken in (
    color_hdr.replace("colorOnly && !batchStopped", "true", 1),
    color_hdr.replace("target != 0u && target != backbuffer", "true", 1),
    color_hdr.replace("matches(device, backbuffer)", "true", 1),
):
    assert broken != color_hdr and not retains_verified_offscreen_clear(broken,probe)

def linked(b,h,r):
    clear=r[r.index("HRESULT __stdcall ClearDestR9("):r.index("template <typename ActualDraw, typename LegacyDraw>")]
    boundary=b[b.index("void observe_scene_boundary("):b.index("bool observe_game_depth_clear(")]
    obs=b[b.index("void observe(IDirect3DDevice9* game,"):b.index("} // namespace",b.index("void observe(IDirect3DDevice9* game,"))]
    gameclear=b[b.index("void observe_game_clear("):b.index("void observe_unavailable_game_draw(")]
    return all((
        "if (SUCCEEDED(result)) {" in clear,
        "observe_scene_boundary(device)" in clear,
        "observe_game_clear(" in clear,
        "preserve_offscreen_color_only_clear(" in clear,
        "&&\n                        !outrun::vr::dx11::live_game_frame::preserve_offscreen_color_only_clear(" in clear,
        "s.clearColor.record(sourceDevice," in gameclear,
        "if (preserve_offscreen_color_only_clear(game, flags)) return;" in gameclear,
        "flags != D3DCLEAR_TARGET" in b,
        "s.clearColor.preserves_offscreen_color_only(" in b,
        "targetIdentity.Get()" in b,
        "s.frameBatch.reset();" in gameclear,
        "const bool ownsPreDrawColor = env_full_game_opt_in()" in boundary,
        "s.clearColor.valid && s.clearColor.sourceDevice == owner" in boundary,
        "if (!ownsDraw && !ownsPreDrawColor) return;" in boundary,
        "if (ownsPreDrawColor && s.frameBatch.submitted == 0u)" in boundary,
        "s.frameBatch.abort();" in boundary,
        "s.frameBatch.accepts_full_on_source_target(" in obs,
        "const bool sameClearedGameTarget = s.clearColor.matches(" in obs,
        "output.targetIdentity);" in obs,
        "if (fullMode) s.frameBatch.abort();" in obs,
        "s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)" in b,
        "return matchesClearedBackbuffer &&" in h,
        "python tools/test_dx11_full_frame_color_seed_00735.py" in flow,
        "tools/dx11_full_frame_color_seed_00735.cpp" in flow,
    ))
assert linked(bridge,batch,hook),"native game Clear->Draw/Indexed source/color ownership broken"
for token,mut in (
    ("s.clearColor.valid && s.clearColor.sourceDevice == owner","false"),
    ("if (!ownsDraw && !ownsPreDrawColor) return;","if (!ownsDraw) return;"),
    ("if (ownsPreDrawColor && s.frameBatch.submitted == 0u)","if (false)"),
    ("s.frameBatch.accepts_full_on_source_target(","s.frameBatch.accepts_full("),
    ("const bool sameClearedGameTarget = s.clearColor.matches(","const bool sameClearedGameTarget = false && s.clearColor.matches("),
    ("if (preserve_offscreen_color_only_clear(game, flags)) return;",
     "if (false) return;"),
    ("flags != D3DCLEAR_TARGET","flags == D3DCLEAR_TARGET"),
):
    assert token in bridge
    assert not linked(bridge.replace(token,mut,1),batch,hook),token
assert not linked(bridge,batch.replace("return matchesClearedBackbuffer &&","return true &&",1),hook)
assert not linked(bridge.replace("s.clearColor.preserves_offscreen_color_only(",
                               "s.clearColor.matches(",1),batch,hook)
assert not linked(bridge,batch,hook.replace(
    "!outrun::vr::dx11::live_game_frame::preserve_offscreen_color_only_clear(",
    "/* bypassed auxiliary RT0 color clear */ false && (",1))
clear_start=hook.index("HRESULT __stdcall ClearDestR9(")
clear_end=hook.index("template <typename ActualDraw, typename LegacyDraw>",clear_start)
clear_section=hook[clear_start:clear_end]
assert "observe_scene_boundary(device)" in clear_section
mutated_clear=hook[:clear_start]+clear_section.replace(
    "observe_scene_boundary(device)","ignore_scene_boundary(device)",1)+hook[clear_end:]
assert not linked(bridge,batch,mutated_clear)
print("00735 full Clear seed and pre-Draw abort / original game+gamepad fallback PASS")
