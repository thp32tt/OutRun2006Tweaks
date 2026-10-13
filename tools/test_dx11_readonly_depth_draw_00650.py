"""00650: real game D3D9 Z compare with ZWRITEENABLE=false -> native D3D11 read-only DSV."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/live_game_depth_state.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_game_depth_probe.cpp").read_text(encoding="utf-8")


def connected(cpp: str, adm: str) -> bool:
    gate = cpp.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
    draw = cpp.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    common = (
        'GetRenderState(D3DRS_ZWRITEENABLE, &zWrite)',
        'game_native_depth_admission(',
        'output.nativeDepthWrite = admitted.writeEnabled;',
        'depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE',
    )
    submit = (
        'std::array<ComPtr<ID3D11DepthStencilState>, 4> diagnosticDepthStates;',
        'D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO',
        'ds.DepthFunc = output.nativeDepthLessEqual ?',
        'output.nativeDepthWrite ? 2u : 0u',
        'output.nativeDepthLessEqual ? 1u : 0u',
        'ctx->OMSetDepthStencilState(',
        'ctx->OMSetRenderTargets(1, &rtv, s.diagnosticDepthView.Get());',
        'ctx->DrawIndexed(indexCount, 0, 0);',
        'ctx->Draw(static_cast<UINT>(vertices.size()), 0);',
    )
    return (
        all(x in gate for x in common)
        and all(x in cpp for x in submit)
        and all(x in draw for x in (
            'D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO',
            'ctx->OMSetDepthStencilState(',
            'ctx->DrawIndexed(indexCount, 0, 0);',
            'ctx->Draw(static_cast<UINT>(vertices.size()), 0);',
        ))
        and 'zWrite > 1u' in adm
        and 'output = {true, zFunc == 4u, zWrite == 1u};' in adm
        and 'zFunc != 2u && zFunc != 4u' in adm
        and 'validDepthSurface' in adm
    )


assert connected(bridge, header)
for original, broken in (
    ('output.nativeDepthWrite = admitted.writeEnabled;', 'output.nativeDepthWrite = true;'),
    ('D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO', 'D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ALL'),
    ('output.nativeDepthWrite ? 2u : 0u', '0u'),
    ('ctx->OMSetDepthStencilState(', 'ctx->OMSetRenderTargets('),
):
    mutated = bridge.replace(original, broken)
    assert mutated != bridge and not connected(mutated, header), original

mutant = header.replace('zWrite > 1u', 'zWrite != 1u')
assert mutant != header and not connected(bridge, mutant)
mutant = header.replace('zWrite == 1u', 'true')
assert mutant != header and not connected(bridge, mutant)

for token in (
    'game_native_depth_admission(1,0,2,0,0,true,depth)',
    'game_native_depth_admission(1,0,4,0,0,true,depth)',
    '!depth.writeEnabled',
    'game_native_depth_admission(1,2,4,0,0,true,depth)',
):
    assert token in probe, token
assert 'if (!diagnostic_enabled() || !game' in bridge
print("00650 read-only game Z Draw/Indexed D3D11 DSV mapping + original DX9Ex fallback PASS")
