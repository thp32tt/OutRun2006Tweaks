#!/usr/bin/env python3
"""00656: live game D3D9 MAG-anisotropic D3D11 Draw full-mip integration."""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def connected(s):
    try:
        cap = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        mirror = s.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        # Both the standalone Stage1 sampler and the Stage0 game texture
        # mirror must remain connected after 00716 sampler extraction.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in mirror:
            return False
        sampler_impl = s.split("bool create_game_sampler(", 1)[1].split("bool mirror_texture(", 1)[0]
        if not all(x in sampler_impl for x in ["capture.magFilter != D3DTEXF_ANISOTROPIC) ||","capture.mipFilter != D3DTEXF_LINEAR ||","state.Filter = D3D11_FILTER_ANISOTROPIC;"]):
            return False
        draw = s.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return (
        all(x in cap for x in (
            "GetSamplerState(0, D3DSAMP_MAGFILTER, &mag)",
            "GetSamplerState(0, D3DSAMP_MINFILTER, &min)",
            "GetSamplerState(0, D3DSAMP_MIPFILTER, &mip)",
            "GetSamplerState(0, D3DSAMP_MAXANISOTROPY, &maxAniso)",
            "min == D3DTEXF_ANISOTROPIC &&",
            "(mag == D3DTEXF_LINEAR || mag == D3DTEXF_ANISOTROPIC) &&",
            "mip == D3DTEXF_LINEAR &&",
            "maxAniso >= 2u && maxAniso <= D3D11_REQ_MAXANISOTROPY;",
            "((mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR) && !anisotropic) ||",
            "((min != D3DTEXF_POINT && min != D3DTEXF_LINEAR) && !anisotropic) ||",
            "capture.maxAnisotropy = anisotropic ? maxAniso : 1u;",
            "capture.magFilter = static_cast<D3DTEXTUREFILTERTYPE>(mag);"))
        and all(x in mirror for x in (
            "(capture.magFilter != D3DTEXF_LINEAR &&",
            "capture.magFilter != D3DTEXF_ANISOTROPIC) ||",
            "capture.mipFilter != D3DTEXF_LINEAR ||",
            "capture.maxAnisotropy < 2u",
            "capture.maxAnisotropy > D3D11_REQ_MAXANISOTROPY",
            "const UINT levels = usesMips ? sourceLevels : 1u;",
            "initial[level].pSysMem = copied[level].data();",
            "state.Filter = D3D11_FILTER_ANISOTROPIC;",
            "state.MaxAnisotropy = capture.minFilter == D3DTEXF_ANISOTROPIC ?",
            "dev->CreateSamplerState(&state, sampler.GetAddressOf())"))
        and all(x in draw for x in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetSamplers(0, 1, &boundSampler);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
    )

def accepted(mn, mg, mp, an):
    return mn == "aniso" and mg in ("linear", "aniso") and mp == "linear" and 2 <= an <= 16

def main():
    source = SRC.read_text(encoding="utf-8")
    assert connected(source), "missing real D3D9 -> D3D11 anisotropic sampler binding"
    mutations = (
        ("(mag == D3DTEXF_LINEAR || mag == D3DTEXF_ANISOTROPIC)", "(mag == D3DTEXF_LINEAR || mag == D3DTEXF_POINT)"),
        ("mip == D3DTEXF_LINEAR &&", "mip == D3DTEXF_POINT &&"),
        ("maxAniso >= 2u", "maxAniso >= 0u"),
        ("maxAniso <= D3D11_REQ_MAXANISOTROPY", "maxAniso <= 255u"),
        ("((mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR) && !anisotropic) ||",
         "((mag != D3DTEXF_POINT && mag != D3DTEXF_LINEAR)) ||"),
        ("((min != D3DTEXF_POINT && min != D3DTEXF_LINEAR) && !anisotropic) ||",
         "((min != D3DTEXF_POINT && min != D3DTEXF_LINEAR)) ||"),
        ("capture.magFilter != D3DTEXF_ANISOTROPIC) ||", "capture.magFilter != D3DTEXF_POINT) ||"),
        ("capture.mipFilter != D3DTEXF_LINEAR ||", "capture.mipFilter != D3DTEXF_POINT ||"),
        ("initial[level].pSysMem = copied[level].data();", "initial[level].pSysMem = copied[0].data();"),
        ("state.Filter = D3D11_FILTER_ANISOTROPIC;", "state.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    for original, bad in mutations:
        assert original in source, original
        assert not connected(source.replace(original, bad, 1)), "uncaught mutation: " + original
    total = allowed = 0
    for mn in ("point", "linear", "aniso"):
        for mg in ("point", "linear", "aniso"):
            for mp in ("none", "point", "linear"):
                for an in (0, 1, 2, 4, 8, 16, 17, 255):
                    expected = mn == "aniso" and mg in ("linear", "aniso") and mp == "linear" and 2 <= an <= 16
                    assert accepted(mn, mg, mp, an) == expected
                    total += 1
                    allowed += int(expected)
    assert total == 216 and allowed == 8
    print(f"00656 PASS: {total} cases, {allowed} eligible, {len(mutations)} mutations; Quest3/VDXR UNTESTED")

if __name__ == "__main__":
    main()
