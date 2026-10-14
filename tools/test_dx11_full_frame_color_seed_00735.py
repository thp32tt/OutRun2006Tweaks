#!/usr/bin/env python3
"""DX11 00735: verified game full TARGET Clear -> full native Draw and fail-closed fallback."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
batch=(root/"src/vr/d3d11/native_game_frame_batch.hpp").read_text()
hook=(root/"src/vr/d3d9/stereo_renderer.cpp").read_text()
flow=(root/".github/workflows/dx11-fast-structural.yml").read_text()
def linked(b,h,r):
    clear=r[r.index("HRESULT __stdcall ClearDestR9("):r.index("template <typename ActualDraw, typename LegacyDraw>")]
    boundary=b[b.index("void observe_scene_boundary("):b.index("bool observe_game_depth_clear(")]
    obs=b[b.index("void observe(IDirect3DDevice9* game,"):b.index("} // namespace",b.index("void observe(IDirect3DDevice9* game,"))]
    gameclear=b[b.index("void observe_game_clear("):b.index("void observe_unavailable_game_draw(")]
    return all((
        "if (SUCCEEDED(result)) {" in clear,
        "observe_scene_boundary(device)" in clear,
        "observe_game_clear(" in clear,
        "s.clearColor.record(sourceDevice," in gameclear,
        "s.frameBatch.reset();" in gameclear,
        "const bool ownsPreDrawColor = env_full_game_opt_in()" in boundary,
        "s.clearColor.valid && s.clearColor.sourceDevice == owner" in boundary,
        "if (!ownsDraw && !ownsPreDrawColor) return;" in boundary,
        "if (ownsPreDrawColor && s.frameBatch.submitted == 0u)" in boundary,
        "s.frameBatch.abort();" in boundary,
        "s.frameBatch.accepts_full_seeded(" in obs,
        "s.clearColor.matches(reinterpret_cast<std::uintptr_t>(game)," in obs,
        "output.targetIdentity))" in obs,
        "if (fullMode) s.frameBatch.abort();" in obs,
        "s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)" in b,
        "return accepts_full(ordinal) && (submitted != 0u || sameSourceFullClear);" in h,
        "python tools/test_dx11_full_frame_color_seed_00735.py" in flow,
        "tools/dx11_full_frame_color_seed_00735.cpp" in flow,
    ))
assert linked(bridge,batch,hook),"native game Clear->Draw/Indexed source/color ownership broken"
for token,mut in (
    ("s.clearColor.valid && s.clearColor.sourceDevice == owner","false"),
    ("if (!ownsDraw && !ownsPreDrawColor) return;","if (!ownsDraw) return;"),
    ("if (ownsPreDrawColor && s.frameBatch.submitted == 0u)","if (false)"),
    ("s.frameBatch.accepts_full_seeded(","s.frameBatch.accepts_full("),
    ("s.clearColor.matches(reinterpret_cast<std::uintptr_t>(game),","s.clearColor.matches(0u,"),
):
    assert token in bridge
    assert not linked(bridge.replace(token,mut,1),batch,hook),token
assert not linked(bridge,batch.replace("return accepts_full(ordinal) && (submitted != 0u || sameSourceFullClear);","return accepts_full(ordinal);"),hook)
clear_start=hook.index("HRESULT __stdcall ClearDestR9(")
clear_end=hook.index("template <typename ActualDraw, typename LegacyDraw>",clear_start)
clear_section=hook[clear_start:clear_end]
assert "observe_scene_boundary(device)" in clear_section
mutated_clear=hook[:clear_start]+clear_section.replace(
    "observe_scene_boundary(device)","ignore_scene_boundary(device)",1)+hook[clear_end:]
assert not linked(bridge,batch,mutated_clear)
print("00735 full Clear seed and pre-Draw abort / original game+gamepad fallback PASS")
