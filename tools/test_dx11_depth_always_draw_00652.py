"""Live D3D9 ZFUNC ALWAYS native depth-state integration regression: task 00652."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf8")
hdr = (root / "src/vr/d3d11/live_game_depth_state.hpp").read_text(encoding="utf8")
probe = (root / "tools/dx11_game_depth_probe.cpp").read_text(encoding="utf8")

def connected(c: str, h: str, p: str) -> bool:
    admission = c.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    draw = c.split("bool submit(",1)[1].split("void before_game_present(",1)[0]
    return (all(x in admission for x in (
        "game_native_depth_admission(", "output.nativeDepthAlways = admitted.always;",
        "output.nativeDepthWrite = admitted.writeEnabled;",
        "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE"))
        and all(x in draw for x in (
        "if (output.nativeDepthAlways)",
        "s.diagnosticDepthAlwaysStates[output.nativeDepthWrite ? 1u : 0u]",
        "ds.DepthFunc = D3D11_COMPARISON_ALWAYS;",
        "D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO",
        "dev->CreateDepthStencilState(&ds,",
        "ctx->OMSetRenderTargets(1, &rtv, s.diagnosticDepthView.Get());",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
        and "s.diagnosticDepthAlwaysStates[output.nativeDepthWrite ? 1u : 0u].Get(), 0)" in draw
        and c.count("s.diagnosticDepthAlwaysStates[output.nativeDepthWrite ? 1u : 0u]") == 2
        and c.count("for (auto& depthState : s.diagnosticDepthAlwaysStates) depthState.Reset();") == 2
        and "std::array<ComPtr<ID3D11DepthStencilState>, 2> diagnosticDepthAlwaysStates;" in c
        and "bool nativeDepthAlways = false;" in c
        and "output.always = zFunc == 8u;" in h
        and "(zFunc != 2u && zFunc != 4u && zFunc != 8u &&" in h
        and "bool always = false;" in h
        and all(x in p for x in (
        "game_native_depth_admission(1,1,8,0,0,true,depth)",
        "game_native_depth_admission(1,0,8,0,0,true,depth)",
        "!game_native_depth_admission(1,1,8,0,0,false,depth)",
        "depth.enabled && depth.always && depth.writeEnabled",
        "depth.enabled && depth.always && !depth.writeEnabled"))
        and "if (!diagnostic_enabled() || !game" in c)

assert connected(cpp,hdr,probe)
for a,b in (
    ("output.nativeDepthAlways = admitted.always;","output.nativeDepthAlways = false;"),
    ("ds.DepthFunc = D3D11_COMPARISON_ALWAYS;","ds.DepthFunc = D3D11_COMPARISON_LESS;"),
    ("s.diagnosticDepthAlwaysStates[output.nativeDepthWrite ? 1u : 0u].Get(), 0)","s.diagnosticDepthStates[0].Get(), 0)"),
    ("s.diagnosticDepthAlwaysStates[output.nativeDepthWrite ? 1u : 0u]","s.diagnosticDepthAlwaysStates[0u]"),
    ("for (auto& depthState : s.diagnosticDepthAlwaysStates) depthState.Reset();",""),
):
    mutant=cpp.replace(a,b,1)
    assert mutant != cpp and not connected(mutant,hdr,probe), a
for a,b in (
    ("output.always = zFunc == 8u;","output.always = false;"),
    ("(zFunc != 2u && zFunc != 4u && zFunc != 8u &&","(zFunc != 2u && zFunc != 4u && zFunc != 9u &&"),
):
    mutant=hdr.replace(a,b,1)
    assert mutant != hdr and not connected(cpp,mutant,probe), a
print("00652 PASS: live D3D9 ALWAYS Z + read-only/writable native DSV and DX9Ex fallback")
