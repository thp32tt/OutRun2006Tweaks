#!/usr/bin/env python3
"""00765: real R9 RT0 transitions and offscreen Draw ordinals join native output."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
r9 = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def integrated(hook, body):
    rt = hook.split("HRESULT __stdcall SetRenderTargetDestR9(", 1)[1]
    rt = rt.split("HRESULT __stdcall ClearDestR9(", 1)[0]
    normal = body.split("void observe(IDirect3DDevice9* game,", 1)[1]
    normal = normal.split("bool preserve_offscreen_color_only_clear(", 1)[0]
    offscreen = body.split("bool isolated_offscreen_game_draw(", 1)[1].split(
        "bool proven_game_draw_no_target_writes(", 1)[0].split(
        "void observe(IDirect3DDevice9* game,", 1)[0]
    absent = body.split("void observe_unavailable_game_draw(", 1)[1]
    absent = absent.split("void observe_failed_game_draw(", 1)[0]
    return (
        "preserve_game_target_transition(device)" in rt and
        "observe_scene_boundary(device)" in rt and
        'native_game_offscreen_pass.hpp' in body and
        'GameNativeOffscreenPass::preserve_transition(' in body and
        'GetRenderState(D3DRS_ZENABLE, &zEnabled)' in offscreen and
        'GetRenderState(D3DRS_ZWRITEENABLE, &zWriteEnabled)' in offscreen and
        'GameNativeOffscreenPass::no_main_depth_write(' in offscreen and
        'GetRenderState(D3DRS_STENCILENABLE, &stencilEnabled)' in offscreen and
        'GetDeviceCaps(&caps)' in offscreen and
        'GameNativeOffscreenPass::valid_mrt_count(caps.NumSimultaneousRTs)' in offscreen and
        'for (DWORD i = 1u; i < caps.NumSimultaneousRTs; ++i)' in offscreen and
        'GetRenderTarget(i, extra.GetAddressOf())' in offscreen and
        'GameNativeOffscreenPass::source_has_no_main_writes(' in body and
        'isolated_offscreen_game_draw(game, s)' in normal and
        's.frameBatch.absorb_empty_source_draw(' in normal and
        'isolated_offscreen_game_draw(game, s)' in absent and
        's.frameBatch.absorb_empty_source_draw(' in absent
    )
assert integrated(r9, bridge)
assert 'bool preserve_game_target_transition(IDirect3DDevice9* gameDevice)' in header
for original, replacement in (
    ('!outrun::vr::dx11::live_game_frame::preserve_game_target_transition(device)',
     'false /* break RT continuity */'),
    ('GetRenderState(D3DRS_ZENABLE, &zEnabled)', 'GetRenderState(D3DRS_ZWRITEENABLE, &zEnabled)'),
    ('GetRenderState(D3DRS_ZWRITEENABLE, &zWriteEnabled)',
     'GetRenderState(D3DRS_ZENABLE, &zWriteEnabled)'),
    ('GetDeviceCaps(&caps)', 'GetDeviceCaps(nullptr)'),
    ('for (DWORD i = 1u; i < caps.NumSimultaneousRTs; ++i)', 'for (DWORD i = 1u; i <= 3u; ++i)'),
    ('GameNativeOffscreenPass::source_has_no_main_writes(', 'GameNativeOffscreenPass::unsafe_unproven_main_writes('),
):
    h, b = r9, bridge
    if original in h:
        h = h.replace(original, replacement, 1)
    elif original in ('GetDeviceCaps(&caps)',
                      'GetRenderState(D3DRS_ZWRITEENABLE, &zWriteEnabled)'):
        # Other game-state admission also queries caps: damage this exact
        # offscreen source predicate rather than an unrelated earlier caller.
        start = b.index('bool isolated_offscreen_game_draw(')
        end = b.index('void observe(IDirect3DDevice9* game,', start)
        b = b[:start] + b[start:end].replace(original, replacement, 1) + b[end:]
    else:
        b = b.replace(original, replacement, 1)
    assert not integrated(h, b), original
assert 'tools/test_dx11_game_offscreen_pass_00765.py' in workflow
assert 'tools/dx11_game_offscreen_pass_00765.cpp' in workflow
print("00765 real offscreen Draw/DrawIndexed + R9 RT0 + DX9Ex fallback PASS")
