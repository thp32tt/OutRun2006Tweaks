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
    'ctx->OMSetRenderTargets(1, &rtv, s.diagnosticDepthView.Get());',
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
assert 'void before_game_reset() noexcept' in cpp
assert 'if (s.frameBatch.first_draw()) {' in cpp
assert 's.backend.begin_frame(env_full_game_opt_in()' in cpp
assert 's.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)' in cpp
assert ': kBackground);' in cpp
print("DX11 00648 real game depth Draw source/fallback regression: PASS")
