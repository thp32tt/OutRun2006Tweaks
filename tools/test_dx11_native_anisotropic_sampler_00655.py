#!/usr/bin/env python3
"""00655: game D3D9 anisotropic filtering to native DX11 Draw/DrawIndexed.

Only MIN=ANISOTROPIC, MAG/MIP=LINEAR, max anisotropy 2..16.
Original game rendering/input remain D3D9; real HMD validation is separate.
"""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"


def connected(s: str) -> bool:
    try:
        cap = s.split("struct TextureCapture {", 1)[1].split("struct OutputCapture {", 1)[0]
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        mirror = s.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        # Both the standalone Stage1 sampler and the Stage0 game texture
        # mirror must remain connected after 00716 sampler extraction.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in mirror:
            return False
        sampler_impl = s.split("bool create_game_sampler(", 1)[1].split("bool mirror_texture(", 1)[0]
        if not all(x in sampler_impl for x in ["capture.maxAnisotropy < 2u","capture.maxAnisotropy > D3D11_REQ_MAXANISOTROPY","state.Filter = D3D11_FILTER_ANISOTROPIC;"]):
            return False
        draw = s.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return (
        all(x in cap for x in (
            "DWORD maxAnisotropy = 1u;",
            "D3DTEXTUREFILTERTYPE minFilter = D3DTEXF_POINT;"))
        and all(x in gate for x in (
            "GetSamplerState(0, D3DSAMP_MINFILTER, &min)",
            "GetSamplerState(0, D3DSAMP_MAGFILTER, &mag)",
            "GetSamplerState(0, D3DSAMP_MIPFILTER, &mip)",
            "GetSamplerState(0, D3DSAMP_MAXANISOTROPY, &maxAniso)",
            "min == D3DTEXF_ANISOTROPIC &&",
            "(mag == D3DTEXF_LINEAR || mag == D3DTEXF_ANISOTROPIC) &&",
            "mip == D3DTEXF_LINEAR &&",
            "maxAniso >= 2u && maxAniso <= D3D11_REQ_MAXANISOTROPY;",
            "((min != D3DTEXF_POINT && min != D3DTEXF_LINEAR) && !anisotropic) ||",
            "capture.maxAnisotropy = anisotropic ? maxAniso : 1u;",
            "capture.minFilter = static_cast<D3DTEXTUREFILTERTYPE>(min);"))
        and all(x in mirror for x in (
            "capture.maxAnisotropy < 2u",
            "capture.maxAnisotropy > D3D11_REQ_MAXANISOTROPY",
            "capture.magFilter != D3DTEXF_LINEAR",
            "capture.mipFilter != D3DTEXF_LINEAR",
            "const UINT levels = usesMips ? sourceLevels : 1u;",
            "capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
            "initial[level].pSysMem = copied[level].data();",
            "if (capture.minFilter == D3DTEXF_ANISOTROPIC)",
            "state.Filter = D3D11_FILTER_ANISOTROPIC;",
            "state.MaxAnisotropy = capture.minFilter == D3DTEXF_ANISOTROPIC ?",
            "capture.maxAnisotropy : 1u;",
            "dev->CreateSamplerState(&state, sampler.GetAddressOf())"))
        and all(x in draw for x in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetSamplers(0, 1, &boundSampler);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")))


def admitted(mn: str, mg: str, mp: str, n: int) -> bool:
    return mn == "aniso" and mg == "linear" and mp == "linear" and 2 <= n <= 16


def main() -> None:
    src = SRC.read_text(encoding="utf-8")
    assert connected(src), "game anisotropic sampler not bound to native Draw"
    mutations = (
        ("D3DSAMP_MAXANISOTROPY, &maxAniso", "D3DSAMP_MAXANISOTROPY, &min"),
        ("maxAniso >= 2u", "maxAniso >= 0u"),
        ("maxAniso <= D3D11_REQ_MAXANISOTROPY", "maxAniso <= 255u"),
        ("(mag == D3DTEXF_LINEAR || mag == D3DTEXF_ANISOTROPIC)", "(mag == D3DTEXF_POINT || mag == D3DTEXF_ANISOTROPIC)"),
        ("((min != D3DTEXF_POINT && min != D3DTEXF_LINEAR) && !anisotropic) ||", "((min != D3DTEXF_POINT && min != D3DTEXF_LINEAR)) ||"),
        ("capture.maxAnisotropy = anisotropic ? maxAniso : 1u;", "capture.maxAnisotropy = 1u;"),
        ("capture.maxAnisotropy < 2u", "capture.maxAnisotropy < 0u"),
        ("capture.maxAnisotropy > D3D11_REQ_MAXANISOTROPY", "capture.maxAnisotropy > 255u"),
        ("state.Filter = D3D11_FILTER_ANISOTROPIC;", "state.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;"),
        ("capture.maxAnisotropy : 1u;", "1u : 1u;"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    for original, damaged in mutations:
        assert original in src, original
        assert not connected(src.replace(original, damaged, 1)), "uncaught mutation: " + original
    cases = 0
    for mn in ("point", "linear", "aniso"):
        for mg in ("point", "linear", "aniso"):
            for mp in ("none", "point", "linear"):
                for ma in (0, 1, 2, 4, 8, 16, 17, 255):
                    expected = mn == "aniso" and mg == "linear" and mp == "linear" and 2 <= ma <= 16
                    assert admitted(mn, mg, mp, ma) == expected
                    cases += 1
    print(f"00655 PASS: {cases} combinations, {len(mutations)} negative mutations; game/HMD/gamepad UNTESTED")


if __name__ == "__main__":
    main()
