"""CONVERSION-DX11-00648: real D3D9 Z Draw -> isolated D3D11 DSV."""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
cpp = (r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
depth = (r/"src/vr/d3d11/live_game_depth_state.hpp").read_text(encoding="utf-8")
checks = [
    '#include "live_game_depth_state.hpp"',
    'game->GetDepthStencilSurface(gameDepth.GetAddressOf())',
    'game_native_depth_admission(',
    'output.nativeDepthTest = admitted.enabled;',
    'dev->CreateTexture2D(&depthDesc, nullptr,',
    'dev->CreateDepthStencilView(createdDepth.Get(), nullptr,',
    'dev->CreateDepthStencilState(&ds,',
    # The real FVF path now binds a live linear/sRGB RTV on every Draw,
    # preserving the same independent diagnostic DSV when depth is enabled.
    'ID3D11RenderTargetView* gameRtv = output.nativeSrgbWrite',
    '? s.backend.color_rtv_srgb() : s.backend.color_rtv();',
    'ctx->OMSetRenderTargets(1u, &gameRtv,',
    'output.nativeDepthTest ? s.diagnosticDepthView.Get() : nullptr',
    'ctx->ClearDepthStencilView(s.diagnosticDepthView.Get(),',
    'ctx->OMSetDepthStencilState(nullptr, 0);',
    'if (ib) ctx->DrawIndexed(indexCount, 0, 0);',
    'else ctx->Draw(static_cast<UINT>(vertices.size()), 0);',
    's.diagnosticDepthView.Reset(); s.diagnosticDepth.Reset();',
]
assert all(x in cpp for x in checks), [x for x in checks if x not in cpp]
assert 'stencil || depth || !clip' not in cpp
assert 'zEnable != 1u || zWrite > 1u' in depth
assert 'zFunc != 2u && zFunc != 4u' in depth
assert 'depthBiasBits & 0x7fffffffu' in depth
assert 'if (!diagnostic_enabled() || !game' in cpp
# The native device is retired only for the Reset owner; auxiliary menu/video
# devices must not discard an active depth-tested race frame or readback.
reset = cpp.partition('void before_game_reset(IDirect3DDevice9* game) noexcept {')[2]
assert reset, "device-aware game Reset implementation missing"
reset_guard = reset.find('if (!GameNativeFrameBatch::reset_belongs_to_game_source(')
reset_clear = reset.find('s.pending = false;')
reset_shutdown = reset.find('s.backend.shutdown();')
assert 0 <= reset_guard < reset_clear < reset_shutdown, "Reset ownership must precede depth/GPU teardown"
assert 's.previousOutput.valid() ? s.previousOutput.device : 0u' in reset[reset_guard:reset_clear]
assert 'return;' in reset[reset_guard:reset_clear]
assert 's.diagnosticDepthView.Reset(); s.diagnosticDepth.Reset();' in reset[reset_clear:reset_shutdown]
assert 'if (s.frameBatch.first_draw()) {' in cpp
assert 's.backend.begin_frame(env_full_game_opt_in()' in cpp
assert 's.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)' in cpp
assert ': kBackground);' in cpp
print("DX11 00648 real game depth Draw source/fallback regression: PASS")
