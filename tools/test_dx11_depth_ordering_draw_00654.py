"""00654: real D3D9 GREATER / GREATEREQUAL game Draw in native D3D11."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
C=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf8")
H=(r/"src/vr/d3d11/live_game_depth_state.hpp").read_text(encoding="utf8")
P=(r/"tools/dx11_game_depth_probe.cpp").read_text(encoding="utf8")

def integrated(c,h,p):
    adm=c.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    draw=c.split("bool submit(",1)[1].split("void before_game_present(",1)[0]
    return (all(s in h for s in (
        "zFunc != 5u && zFunc != 7u) ||",
        "output.orderingMode = (zFunc == 5u || zFunc == 7u) ? zFunc : 0u;",
        "(writeEnabled ? 2u : 0u) + (orderingMode == 7u ? 1u : 0u);"))
      and all(s in adm for s in (
        "game->GetRenderState(D3DRS_ZFUNC, &zFunc)",
        "game_native_depth_admission(",
        "output.nativeDepthOrderingMode = admitted.orderingMode;",
        "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE"))
      and all(s in draw for s in (
        "else if (output.nativeDepthOrderingMode != 0u)",
        "D3D11_COMPARISON_GREATER : D3D11_COMPARISON_GREATER_EQUAL;",
        "D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO",
        "s.frameBatch.depth_clear_value(output.nativeDepthOrderingMode != 0u), 0);",
        "s.frameBatch.consume_depth_clear();",
        "ctx->ClearDepthStencilView(s.diagnosticDepthView.Get(), D3D11_CLEAR_DEPTH,",
        "ctx->OMSetRenderTargets(1, &rtv, s.diagnosticDepthView.Get());",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
      and c.count("else if (output.nativeDepthOrderingMode != 0u)")==2
      and c.count("s.diagnosticDepthOrderingStates[")==2
      and c.count("for (auto& depthState : s.diagnosticDepthOrderingStates) depthState.Reset();")==2
      and "std::array<ComPtr<ID3D11DepthStencilState>, 4> diagnosticDepthOrderingStates;" in c
      and "output.nativeDepthWrite, output.nativeDepthOrderingMode)].Get(), 0);" in draw
      and "if (!diagnostic_enabled() || !game" in c
      and all(s in p for s in (
        "for (unsigned compare : {5u, 7u})",
        "for (unsigned write : {0u, 1u})",
        "depth.orderingMode == compare",
        "!game_native_depth_admission(1,1,7,0,0,false,depth)",
        "!game_native_depth_admission(1,0,5,0x3f800000u,0,true,depth)",
        "for (unsigned unsupported : {1u, 9u})")))
assert integrated(C,H,P)
for old,bad in (
    ("output.nativeDepthOrderingMode = admitted.orderingMode;","output.nativeDepthOrderingMode = 0u;"),
    ("D3D11_COMPARISON_GREATER : D3D11_COMPARISON_GREATER_EQUAL;","D3D11_COMPARISON_GREATER : D3D11_COMPARISON_GREATER;"),
    ("output.nativeDepthWrite, output.nativeDepthOrderingMode)].Get(), 0);","false, output.nativeDepthOrderingMode)].Get(), 0);"),
    ("output.nativeDepthWrite, output.nativeDepthOrderingMode)].Get(), 0);","output.nativeDepthWrite, 5u)].Get(), 0);"),
    ("s.frameBatch.depth_clear_value(output.nativeDepthOrderingMode != 0u)","s.frameBatch.depth_clear_value(false)"),
    ("s.frameBatch.consume_depth_clear();","/* deleted clear consumption */"),
    ("for (auto& depthState : s.diagnosticDepthOrderingStates) depthState.Reset();",""),
    ("else if (output.nativeDepthOrderingMode != 0u)","else if (false)"),
):
    mutant=C.replace(old,bad,1)
    assert mutant!=C and not integrated(mutant,H,P),old
for old,bad in (
    ("zFunc != 5u && zFunc != 7u) ||","zFunc != 5u) ||"),
    ("output.orderingMode = (zFunc == 5u || zFunc == 7u) ? zFunc : 0u;","output.orderingMode = 0u;"),
    ("(writeEnabled ? 2u : 0u) + (orderingMode == 7u ? 1u : 0u);","(orderingMode == 7u ? 1u : 0u);"),
):
    mutant=H.replace(old,bad,1)
    assert mutant!=H and not integrated(C,mutant,P),old
print("00654 PASS: GREATER/GREATEREQUAL four-way native DSV, game Draw, fallback")
