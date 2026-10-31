"""00653: real game ZFUNC EQUAL / NOTEQUAL through D3D11 DSV and Draw."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf8")
HDR = (ROOT/"src/vr/d3d11/live_game_depth_state.hpp").read_text(encoding="utf8")
PROBE = (ROOT/"tools/dx11_game_depth_probe.cpp").read_text(encoding="utf8")

def connected(c: str, h: str, p: str) -> bool:
    admit = c.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    draw = c.split("bool submit(",1)[1].split("void before_game_present(",1)[0]
    sm3=c.split("bool submit_live_sm3_game_draw(",1)[1].split(
        "// Reuse geometric growth buffers",1)[0]
    slot = """game_native_depth_equality_slot(
                    output.nativeDepthWrite, output.nativeDepthEqualityMode)"""
    return (all(s in h for s in (
        "zFunc != 3u && zFunc != 6u &&",
        "output.equalityMode = (zFunc == 3u || zFunc == 6u) ? zFunc : 0u;",
        "(writeEnabled ? 2u : 0u) + (equalityMode == 6u ? 1u : 0u);",
    )) and all(s in admit for s in (
        "game->GetRenderState(D3DRS_ZFUNC, &zFunc)",
        "game_native_depth_admission(",
        "output.nativeDepthEqualityMode = admitted.equalityMode;",
        "depthDesc.MultiSampleType == D3DMULTISAMPLE_NONE",
    )) and all(s in draw for s in (
        "if (output.nativeDepthAlways)",
        "else if (output.nativeDepthEqualityMode != 0u)",
        "s.diagnosticDepthEqualityStates[",
        "ds.DepthFunc = output.nativeDepthEqualityMode == D3DCMP_EQUAL ?",
        "D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_NOT_EQUAL;",
        "ds.DepthWriteMask = output.nativeDepthWrite ?",
        "D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO",
        "dev->CreateDepthStencilState(&ds,",
        "ID3D11RenderTargetView* gameRtv = output.nativeSrgbWrite",
        "? s.backend.color_rtv_srgb() : s.backend.color_rtv();",
        "ctx->OMSetRenderTargets(1u, &gameRtv,",
        "output.nativeDepthTest ? s.diagnosticDepthView.Get() : nullptr",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    )) and draw.count(slot) == 1
    and c.count("s.diagnosticDepthEqualityStates[") == 3
    and sm3.count("s.diagnosticDepthEqualityStates[") == 1
    and all(s in sm3 for s in (
        "else if (liveDepth.equalityMode != 0u)",
        "game_native_depth_equality_slot(",
        "D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_NOT_EQUAL;",
        "D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO",
        "context->OMSetDepthStencilState(liveDepthState, 0u)",
        "liveBatch.succeeded(liveDepth.enabled, reverseDepth)",
    ))
    and draw.count("else if (output.nativeDepthEqualityMode != 0u)") == 2
    and c.count("for (auto& depthState : s.diagnosticDepthEqualityStates) depthState.Reset();") == 2
    and "std::array<ComPtr<ID3D11DepthStencilState>, 4> diagnosticDepthEqualityStates;" in c
    and "output.nativeDepthWrite, output.nativeDepthEqualityMode)].Get(), 0);" in draw
    and "if (!diagnostic_enabled() || !game" in c
    and all(s in p for s in (
        "for (unsigned compare : {3u, 6u})",
        "for (unsigned write : {0u, 1u})",
        "depth.equalityMode == compare",
        "!game_native_depth_admission(1,1,3,0,0,false,depth)",
        "!game_native_depth_admission(1,0,6,1,0,true,depth)",
        "for (unsigned unsupported : {1u, 9u})",
    )))

assert connected(CPP, HDR, PROBE)
for original, broken in (
    ("output.nativeDepthEqualityMode = admitted.equalityMode;", "output.nativeDepthEqualityMode = 0u;"),
    ("D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_NOT_EQUAL;", "D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_EQUAL;"),
    ("output.nativeDepthWrite, output.nativeDepthEqualityMode)].Get(), 0);",
     "false, output.nativeDepthEqualityMode)].Get(), 0);"),
    ("output.nativeDepthWrite, output.nativeDepthEqualityMode)].Get(), 0);",
     "output.nativeDepthWrite, 3u)].Get(), 0);"),
    ("for (auto& depthState : s.diagnosticDepthEqualityStates) depthState.Reset();", ""),
    ("else if (output.nativeDepthEqualityMode != 0u)", "else if (false)"),
):
    mutant = CPP.replace(original, broken, 1)
    assert mutant != CPP and not connected(mutant, HDR, PROBE), original
for original, broken in (
    ("zFunc != 3u && zFunc != 6u &&", "zFunc != 3u &&"),
    ("output.equalityMode = (zFunc == 3u || zFunc == 6u) ? zFunc : 0u;",
     "output.equalityMode = 0u;"),
    ("(writeEnabled ? 2u : 0u) + (equalityMode == 6u ? 1u : 0u);",
     "(equalityMode == 6u ? 1u : 0u);"),
):
    mutant = HDR.replace(original, broken, 1)
    assert mutant != HDR and not connected(CPP, mutant, PROBE), original
# Live programmable SM3 draws must retain the exact native comparison and
# write-mask contract alongside fixed-function Draw/DrawIndexed.
for old,bad in (
    ("else if (liveDepth.equalityMode != 0u)", "else if (false)"),
    ("D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_NOT_EQUAL;",
     "D3D11_COMPARISON_EQUAL : D3D11_COMPARISON_EQUAL;"),
):
    mutant=CPP.replace(old,bad)
    assert mutant != CPP and not connected(mutant,HDR,PROBE),old

print("00653 PASS: D3D9 EQUAL/NOTEQUAL zwrite-aware native DSV + original D3D9 fallback")
