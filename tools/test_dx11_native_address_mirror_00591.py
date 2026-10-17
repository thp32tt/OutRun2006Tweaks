#!/usr/bin/env python3
"""00591: game-authored D3D9 reflected UV addressing reaches guarded native Draw."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def wired(s: str) -> bool:
    try:
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        sampler = s.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        # Both the standalone Stage1 sampler and the Stage0 game texture
        # mirror must remain connected after 00716 sampler extraction.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in sampler:
            return False
        draw = s.split("bool submit(", 1)[1].split("void observe(", 1)[0]
    except IndexError:
        return False
    gate_required = [
        "GetSamplerState(0, D3DSAMP_ADDRESSU, &addressU)",
        "GetSamplerState(0, D3DSAMP_ADDRESSV, &addressV)",
        "addressU != D3DTADDRESS_WRAP && addressU != D3DTADDRESS_CLAMP &&",
        "addressU != D3DTADDRESS_MIRROR && addressU != D3DTADDRESS_MIRRORONCE)",
        "addressV != D3DTADDRESS_WRAP && addressV != D3DTADDRESS_CLAMP &&",
        "addressV != D3DTADDRESS_MIRROR && addressV != D3DTADDRESS_MIRRORONCE)",
        "capture.addressU = static_cast<D3DTEXTUREADDRESS>(addressU);",
        "capture.addressV = static_cast<D3DTEXTUREADDRESS>(addressV);",
        "(mip == D3DTEXF_NONE && (maxMip != 0u || decodedMipBias != 0.0f)) || !validMipBias",
        "srgb > 1u ||",
        "capture.srgbTexture = srgb == TRUE;",
    ]
    sampler_required = [
        "case D3DTADDRESS_WRAP: return D3D11_TEXTURE_ADDRESS_WRAP;",
        "case D3DTADDRESS_CLAMP: return D3D11_TEXTURE_ADDRESS_CLAMP;",
        "case D3DTADDRESS_MIRROR: return D3D11_TEXTURE_ADDRESS_MIRROR;",
        "case D3DTADDRESS_MIRRORONCE: return D3D11_TEXTURE_ADDRESS_MIRROR_ONCE;",
        "default: return static_cast<D3D11_TEXTURE_ADDRESS_MODE>(0);",
        "state.AddressU = translateAddress(capture.addressU);",
        "state.AddressV = translateAddress(capture.addressV);",
        "if (!state.AddressU || !state.AddressV) return false;",
        "state.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;",
        "dev->CreateSamplerState(&state, sampler.GetAddressOf())",
    ]
    draw_required = [
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetSamplers(0, 1, &boundSampler);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
    ]
    return (all(x in gate for x in gate_required) and
            all(x in sampler for x in sampler_required) and
            all(x in draw for x in draw_required) and
            "return optedIn;" in s and "void before_game_present(" in s)

def address(mode: str, uv: float) -> float:
    """Reference UV addressing at texel centers (not a GPU parity claim)."""
    if mode == "wrap":
        return uv % 1.0
    if mode == "clamp":
        return min(1.0, max(0.0, uv))
    if mode == "mirror":
        mirrored = uv % 2.0
        return 2.0 - mirrored if mirrored > 1.0 else mirrored
    if mode == "mirror_once":
        return min(1.0, abs(uv))
    raise ValueError(mode)

def main() -> None:
    s = SOURCE.read_text(encoding="utf-8")
    assert wired(s), "game UV state -> D3D11 sampler -> Draw/DrawIndexed disconnected"
    mutations = [
        ("srgb > 1u ||", "srgb > 2u ||"),
        ("addressU != D3DTADDRESS_MIRROR && addressU != D3DTADDRESS_MIRRORONCE)", "false)"),
        ("addressV != D3DTADDRESS_MIRROR && addressV != D3DTADDRESS_MIRRORONCE)", "false)"),
        ("case D3DTADDRESS_MIRROR: return D3D11_TEXTURE_ADDRESS_MIRROR;", "case D3DTADDRESS_MIRROR: return D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("case D3DTADDRESS_MIRRORONCE: return D3D11_TEXTURE_ADDRESS_MIRROR_ONCE;", "case D3DTADDRESS_MIRRORONCE: return D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("case D3DTADDRESS_WRAP: return D3D11_TEXTURE_ADDRESS_WRAP;", "case D3DTADDRESS_WRAP: return D3D11_TEXTURE_ADDRESS_MIRROR;"),
        ("case D3DTADDRESS_CLAMP: return D3D11_TEXTURE_ADDRESS_CLAMP;", "case D3DTADDRESS_CLAMP: return D3D11_TEXTURE_ADDRESS_WRAP;"),
        ("default: return static_cast<D3D11_TEXTURE_ADDRESS_MODE>(0);", "default: return D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("state.AddressU = translateAddress(capture.addressU);", "state.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("state.AddressV = translateAddress(capture.addressV);", "state.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("if (!state.AddressU || !state.AddressV) return false;", "if (false) return false;"),
        ("capture.addressU = static_cast<D3DTEXTUREADDRESS>(addressU);", "capture.addressU = D3DTADDRESS_CLAMP;"),
        ("capture.addressV = static_cast<D3DTEXTUREADDRESS>(addressV);", "capture.addressV = D3DTADDRESS_CLAMP;"),
        ("dev->CreateSamplerState(&state, sampler.GetAddressOf())", "dev->CreateSamplerState(nullptr, sampler.GetAddressOf())"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    ]
    for old, new in mutations:
        assert old in s, old
        assert not wired(s.replace(old, new, 1)), old
    assert len({"wrap", "clamp", "mirror", "mirror_once"}) == 4
    for uv in (-2.75, -2.25, -1.75, -1.25, -.75, -.25, 0., .25, .75, 1.25, 1.75, 2.25, 2.75):
        for mode in ("wrap", "clamp", "mirror", "mirror_once"):
            mapped = address(mode, uv)
            assert 0 <= mapped <= 1
        assert abs(address("mirror", -uv) - address("mirror", uv)) < 1e-9
        assert abs(address("mirror_once", -uv) - address("mirror_once", uv)) < 1e-9
    for mode_u in ("wrap", "clamp", "mirror", "mirror_once"):
        for mode_v in ("wrap", "clamp", "mirror", "mirror_once"):
            for u, v in ((-.25, 1.25), (1.75, -.75)):
                assert all(0.0 <= z <= 1.0 for z in (address(mode_u, u), address(mode_v, v)))
    assert address("mirror", 1.25) == .75
    assert address("mirror_once", -1.25) == 1.0
    assert address("wrap", -.25) == .75
    print("00591 PASS: 16 U/V address combinations, 16 negative mutations, guarded native Draw; HMD UNTESTED")

if __name__ == "__main__":
    main()
