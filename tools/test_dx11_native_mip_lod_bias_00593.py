#!/usr/bin/env python3
"""00593: game D3D9 signed floating-point LOD bias -> native PS Draw."""
from pathlib import Path
import math
import struct

SRC = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def wired(s):
    try:
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        mirror = s.split("bool create_game_sampler(", 1)[1].split("bool submit(", 1)[0]
        # Both the standalone Stage1 sampler and the Stage0 game texture
        # mirror must remain connected after 00716 sampler extraction.
        if "return create_game_sampler(dev, capture, levels, sampler);" not in mirror:
            return False
        draw = s.split("bool submit(", 1)[1].split("void observe(", 1)[0]
        capture = s.split("struct TextureCapture {", 1)[1].split("struct OutputCapture {", 1)[0]
    except IndexError:
        return False
    admission = (
        "GetSamplerState(0, D3DSAMP_MIPMAPLODBIAS, &mipBias)",
        "std::memcpy(&decodedMipBias, &mipBias, sizeof(decodedMipBias));",
        "std::isfinite(decodedMipBias)",
        "decodedMipBias >= kMinMipLodBias",
        "decodedMipBias <= kMaxMipLodBias",
        "(maxMip != 0u || decodedMipBias != 0.0f)",
        "!validMipBias",
        "capture.mipLodBias = decodedMipBias;",
        "capture.mipFilter = static_cast<D3DTEXTUREFILTERTYPE>(mip)",
    )
    native = (
        "capture.mipFilter == D3DTEXF_POINT ||",
        "capture.mipFilter == D3DTEXF_LINEAR;",
        "if (usesMips && capture.maxMipLevel >= sourceLevels) return false;",
        "std::isfinite(capture.mipLodBias)",
        "capture.mipLodBias < kMinMipLodBias",
        "capture.mipLodBias > kMaxMipLodBias",
        "(!usesMips && capture.mipLodBias != 0.0f)",
        "state.MinLOD = usesMips ? static_cast<float>(capture.maxMipLevel) : 0.0f;",
        "state.MipLODBias = usesMips ? capture.mipLodBias : 0.0f;",
        "dev->CreateSamplerState(&state, sampler.GetAddressOf())",
    )
    draw_reqs = ("mirror_texture(dev, capture, sampledView, sampledSampler)",
                 "ctx->PSSetSamplers(0, 1, &boundSampler);",
                 "ctx->DrawIndexed(indexCount, 0, 0);",
                 "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")
    return (all(x in s for x in ("constexpr float kMinMipLodBias = -16.0f;",
                                "constexpr float kMaxMipLodBias = 15.99f;",
                                "return optedIn;", "void before_game_present("))
            and "float mipLodBias = 0.0f;" in capture
            and all(x in gate for x in admission)
            and all(x in mirror for x in native)
            and all(x in draw for x in draw_reqs))

def decode_f32(v):
    return struct.unpack("<f", struct.pack("<I", struct.unpack("<I", struct.pack("<f", v))[0]))[0]

def admitted(mode, bias, most_detailed, levels):
    if not 1 <= levels <= 11 or not math.isfinite(bias) or not -16.0 <= bias <= 15.99:
        return None
    if mode == "none":
        return 0.0 if most_detailed == 0 and bias == 0.0 else None
    if mode not in ("point", "linear") or not 0 <= most_detailed < levels:
        return None
    return bias

def main():
    source = SRC.read_text(encoding="utf-8")
    assert wired(source), "source D3D9 bias -> native D3D11 sampler/Draw disconnected"
    mutations = [
        ("GetSamplerState(0, D3DSAMP_MIPMAPLODBIAS, &mipBias)", "GetSamplerState(0, D3DSAMP_MIPMAPLODBIAS, &maxMip)"),
        ("std::memcpy(&decodedMipBias, &mipBias, sizeof(decodedMipBias));", "decodedMipBias = static_cast<float>(mipBias);"),
        ("std::isfinite(decodedMipBias)", "true"),
        ("decodedMipBias >= kMinMipLodBias", "true"),
        ("decodedMipBias <= kMaxMipLodBias", "true"),
        ("!validMipBias", "false"),
        ("(maxMip != 0u || decodedMipBias != 0.0f)", "(maxMip != 0u)"),
        ("capture.mipLodBias = decodedMipBias;", "capture.mipLodBias = 0.0f;"),
        ("float mipLodBias = 0.0f;", "float mipLodBias = 1.0f;"),
        ("std::isfinite(capture.mipLodBias)", "true"),
        ("capture.mipLodBias < kMinMipLodBias", "false"),
        ("capture.mipLodBias > kMaxMipLodBias", "false"),
        ("(!usesMips && capture.mipLodBias != 0.0f)", "false"),
        ("state.MipLODBias = usesMips ? capture.mipLodBias : 0.0f;", "state.MipLODBias = 0.0f;"),
        ("dev->CreateSamplerState(&state, sampler.GetAddressOf())", "dev->CreateSamplerState(nullptr, sampler.GetAddressOf())"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    ]
    for old, new in mutations:
        assert old in source, old
        assert not wired(source.replace(old, new, 1)), "mutation undetected: " + old
    count = 0
    for levels in range(1, 12):
        for mode in ("none", "point", "linear", "aniso"):
            for max_mip in (0, levels - 1, levels):
                for bias in (-math.inf, -16.01, -16.0, -2.5, -0.5, -0.0, 0.0, 0.25, 2.5, 15.5, 16.0, math.inf, math.nan):
                    b = decode_f32(bias)
                    got = admitted(mode, b, max_mip, levels)
                    expected = (math.isfinite(b) and -16.0 <= b <= 15.99
                                and ((mode == "none" and max_mip == 0 and b == 0)
                                     or (mode in ("point", "linear") and max_mip < levels)))
                    assert (got is not None) == expected
                    if got is not None:
                        assert got == b
                    count += 1
    assert decode_f32(-2.5) == -2.5 and decode_f32(0.25) == 0.25
    assert admitted("linear", -2.5, 1, 5) == -2.5
    assert admitted("none", -0.5, 0, 5) is None
    print(f"00593 PASS: {count} IEEE754 cases and {len(mutations)} source mutations; HMD UNTESTED")

if __name__ == "__main__":
    main()
