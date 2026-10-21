#!/usr/bin/env python3
"""00657: captured D3D9 sRGB sampling -> native DX11 SRV -> live Draw bridge.

No claim of Quest3 or live game pixels: these are deterministic source/mutation
checks backed by the independent exact-SHA Windows build and DX11 Gates.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"


def connected(source: str) -> bool:
    try:
        cap = source.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        mirror = source.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        cube = source.split("bool mirror_cube_texture(", 1)[1].split("bool mirror_texture(", 1)[0]
        texture2d = source.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        # Sampler state now lives in create_game_sampler, while mirror_texture
        # uploads texture pixels and delegates to the shared native sampler.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in mirror:
            return False
        draw = source.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    except IndexError:
        return False
    return (
        all(value in source for value in (
            "bool srgbTexture = false;",
            "capture.srgbTexture = srgb == TRUE;",
        ))
        and all(value in cap for value in (
            "GetSamplerState(0, D3DSAMP_SRGBTEXTURE, &srgb)",
            "GetRenderState(D3DRS_SRGBWRITEENABLE, &srgbWrite)",
            "srgbWrite != FALSE",
            "srgb > 1u",
            "capture.srgbTexture = srgb == TRUE;",
        ))
        and all(value in mirror for value in (
            "if (capture.srgbTexture && packed16) return false;",
            "DXGI_FORMAT_BC1_UNORM_SRGB : DXGI_FORMAT_BC1_UNORM",
            "DXGI_FORMAT_BC2_UNORM_SRGB : DXGI_FORMAT_BC2_UNORM",
            "DXGI_FORMAT_BC3_UNORM_SRGB : DXGI_FORMAT_BC3_UNORM",
            "DXGI_FORMAT_B8G8R8A8_UNORM_SRGB : DXGI_FORMAT_B8G8R8A8_UNORM",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
            "dev->CreateSamplerState(&state, sampler.GetAddressOf())",
        ))
        # Each SRGB format mapping must survive independently in both live
        # game texture routes. A mutation in the cube path must not hide behind
        # an unchanged 2D mapping (or vice versa).
        and all(value in cube for value in (
            "DXGI_FORMAT_BC1_UNORM_SRGB : DXGI_FORMAT_BC1_UNORM",
            "DXGI_FORMAT_BC2_UNORM_SRGB : DXGI_FORMAT_BC2_UNORM",
            "DXGI_FORMAT_BC3_UNORM_SRGB : DXGI_FORMAT_BC3_UNORM",
            "capture.srgbTexture ? DXGI_FORMAT_B8G8R8A8_UNORM_SRGB",
            ": DXGI_FORMAT_B8G8R8A8_UNORM",
        ))
        and all(value in texture2d for value in (
            "DXGI_FORMAT_BC1_UNORM_SRGB : DXGI_FORMAT_BC1_UNORM",
            "DXGI_FORMAT_BC2_UNORM_SRGB : DXGI_FORMAT_BC2_UNORM",
            "DXGI_FORMAT_BC3_UNORM_SRGB : DXGI_FORMAT_BC3_UNORM",
            "DXGI_FORMAT_B8G8R8A8_UNORM_SRGB : DXGI_FORMAT_B8G8R8A8_UNORM",
        ))
        and all(value in draw for value in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->PSSetSamplers(0, 1, &boundSampler);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ))
    )


def native_format(d3d9_format: str, srgb: int):
    """Independent DX9 format mapping oracle: None must use original DX9Ex."""
    if srgb not in (0, 1):
        return None
    mapping = {
        "a8": "B8G8R8A8",
        "x8": "B8G8R8A8",
        "dxt1": "BC1",
        "dxt3": "BC2",
        "dxt5": "BC3",
    }
    linear_16 = {"565", "1555", "4444"}
    if d3d9_format in linear_16:
        return "B8G8R8A8_UNORM" if not srgb else None
    name = mapping.get(d3d9_format)
    return name + ("_UNORM_SRGB" if srgb else "_UNORM") if name else None


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert connected(source), "live D3D9 sampler -> SRGB SRV -> native Draw disconnected"
    mutations = (
        ("GetSamplerState(0, D3DSAMP_SRGBTEXTURE, &srgb)", "GetSamplerState(0, D3DSAMP_ADDRESSW, &srgb)"),
        ("GetRenderState(D3DRS_SRGBWRITEENABLE, &srgbWrite)", "GetRenderState(D3DRS_ALPHATESTENABLE, &srgbWrite)"),
        ("srgbWrite != FALSE", "srgbWrite != TRUE"),
        ("srgb > 1u", "srgb > 2u"),
        ("capture.srgbTexture = srgb == TRUE;", "capture.srgbTexture = false;"),
        ("if (capture.srgbTexture && packed16) return false;", "if (false && packed16) return false;"),
        ("DXGI_FORMAT_BC1_UNORM_SRGB : DXGI_FORMAT_BC1_UNORM", "DXGI_FORMAT_BC1_UNORM : DXGI_FORMAT_BC1_UNORM"),
        ("DXGI_FORMAT_BC2_UNORM_SRGB : DXGI_FORMAT_BC2_UNORM", "DXGI_FORMAT_BC2_UNORM : DXGI_FORMAT_BC2_UNORM"),
        ("DXGI_FORMAT_BC3_UNORM_SRGB : DXGI_FORMAT_BC3_UNORM", "DXGI_FORMAT_BC3_UNORM : DXGI_FORMAT_BC3_UNORM"),
        ("DXGI_FORMAT_B8G8R8A8_UNORM_SRGB : DXGI_FORMAT_B8G8R8A8_UNORM", "DXGI_FORMAT_B8G8R8A8_UNORM : DXGI_FORMAT_B8G8R8A8_UNORM"),
        ("return create_game_sampler(dev, capture, levels, sampler);", "return false;"),
        ("dev->CreateSamplerState(&state, sampler.GetAddressOf())", "false"),
        ("mirror_texture(dev, capture, sampledView, sampledSampler)", "false"),
        ("ctx->PSSetShaderResources(0, 1, &boundView);", "ctx->PSSetShaderResources(0, 0, &boundView);"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    )
    for old, bad in mutations:
        assert old in source, old
        assert not connected(source.replace(old, bad, 1)), "mutation survived: " + old
        # The first occurrence may belong to a cube mirror; also mutate the
        # 2D route on its own when both paths carry the same source fragment.
        prefix, rest = source.split("bool mirror_texture(", 1)
        texture2d, suffix = rest.split("bool submit(", 1)
        if old in texture2d:
            changed = (prefix + "bool mirror_texture(" +
                       texture2d.replace(old, bad, 1) + "bool submit(" + suffix)
            assert not connected(changed), "2D mutation survived: " + old
    formats = ("a8", "x8", "dxt1", "dxt3", "dxt5", "565", "1555", "4444", "unknown")
    valid = 0
    for fmt in formats:
        for srgb in (-1, 0, 1, 2):
            actual = native_format(fmt, srgb)
            expected = (fmt in formats[:5] and srgb in (0, 1)) or (fmt in formats[5:8] and srgb == 0)
            assert (actual is not None) == expected, (fmt, srgb, actual)
            if actual and srgb == 1:
                assert actual.endswith("_UNORM_SRGB")
            valid += int(actual is not None)
    assert valid == 13
    print(f"00657 PASS: 36 sampler-format cases, {valid} admitted, {len(mutations)} destructive mutations; HMD UNTESTED")


if __name__ == "__main__":
    main()
