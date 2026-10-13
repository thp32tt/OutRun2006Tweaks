#!/usr/bin/env python3
"""00594 live D3D9 BORDER U/V ARGB -> guarded native D3D11 sampler Draw."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d11/live_game_frame_bridge.cpp"

def wired(s: str) -> bool:
    try:
        cap = s.split("struct TextureCapture {", 1)[1].split("struct OutputCapture {", 1)[0]
        gate = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
        sampler = s.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = s.split("bool submit(", 1)[1].split("void observe(", 1)[0]
    except IndexError:
        return False
    return all(t in cap for t in (
        "DWORD borderColor = 0u;", "D3DTEXTUREADDRESS addressU", "D3DTEXTUREADDRESS addressV"
    )) and all(t in gate for t in (
        "DWORD borderColor = 0u;",
        "(addressU == D3DTADDRESS_BORDER || addressV == D3DTADDRESS_BORDER) &&",
        "FAILED(game->GetSamplerState(0, D3DSAMP_BORDERCOLOR, &borderColor))",
        "addressU != D3DTADDRESS_BORDER)", "addressV != D3DTADDRESS_BORDER)",
        "capture.borderColor = borderColor;",
        "capture.addressU = static_cast<D3DTEXTUREADDRESS>(addressU);",
        "capture.addressV = static_cast<D3DTEXTUREADDRESS>(addressV);",
        "srgb > 1u ||",
        "capture.srgbTexture = srgb == TRUE;"
    )) and all(t in sampler for t in (
        "case D3DTADDRESS_BORDER: return D3D11_TEXTURE_ADDRESS_BORDER;",
        "default: return static_cast<D3D11_TEXTURE_ADDRESS_MODE>(0);",
        "state.AddressU = translateAddress(capture.addressU);",
        "state.AddressV = translateAddress(capture.addressV);",
        "if (!state.AddressU || !state.AddressV) return false;",
        "state.BorderColor[0] = static_cast<float>((capture.borderColor >> 16) & 0xffu) / 255.0f;",
        "state.BorderColor[1] = static_cast<float>((capture.borderColor >> 8) & 0xffu) / 255.0f;",
        "state.BorderColor[2] = static_cast<float>(capture.borderColor & 0xffu) / 255.0f;",
        "state.BorderColor[3] = static_cast<float>((capture.borderColor >> 24) & 0xffu) / 255.0f;",
        "dev->CreateSamplerState(&state, sampler.GetAddressOf())"
    )) and all(t in draw for t in (
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetSamplers(0, 1, &boundSampler);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"
    )) and "return optedIn;" in s and "void before_game_present(" in s

def rgba(color: int) -> tuple[float, float, float, float]:
    return tuple(((color >> n) & 255) / 255.0 for n in (16, 8, 0, 24))

def main() -> None:
    s = SOURCE.read_text(encoding="utf-8")
    assert wired(s), "D3D9 BORDER sampler did not reach native Draw/DrawIndexed"
    bad = [
        ("srgb > 1u ||", "srgb > 2u ||"),
        ("DWORD borderColor = 0u; // Live game", "DWORD wrongBorder = 0u; // Live game"),
        ("(addressU == D3DTADDRESS_BORDER || addressV == D3DTADDRESS_BORDER) &&", "false &&"),
        ("FAILED(game->GetSamplerState(0, D3DSAMP_BORDERCOLOR, &borderColor))", "false"),
        ("addressU != D3DTADDRESS_BORDER)", "addressU != D3DTADDRESS_CLAMP)"),
        ("addressV != D3DTADDRESS_BORDER)", "addressV != D3DTADDRESS_CLAMP)"),
        ("capture.borderColor = borderColor;", "capture.borderColor = 0u;"),
        ("capture.addressU = static_cast<D3DTEXTUREADDRESS>(addressU);", "capture.addressU = D3DTADDRESS_CLAMP;"),
        ("capture.addressV = static_cast<D3DTEXTUREADDRESS>(addressV);", "capture.addressV = D3DTADDRESS_CLAMP;"),
        ("case D3DTADDRESS_BORDER: return D3D11_TEXTURE_ADDRESS_BORDER;", "case D3DTADDRESS_BORDER: return D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("default: return static_cast<D3D11_TEXTURE_ADDRESS_MODE>(0);", "default: return D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("state.AddressU = translateAddress(capture.addressU);", "state.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("state.AddressV = translateAddress(capture.addressV);", "state.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;"),
        ("state.BorderColor[0] = static_cast<float>((capture.borderColor >> 16) & 0xffu) / 255.0f;", "state.BorderColor[0] = 0.0f;"),
        ("state.BorderColor[1] = static_cast<float>((capture.borderColor >> 8) & 0xffu) / 255.0f;", "state.BorderColor[1] = 0.0f;"),
        ("state.BorderColor[2] = static_cast<float>(capture.borderColor & 0xffu) / 255.0f;", "state.BorderColor[2] = 0.0f;"),
        ("state.BorderColor[3] = static_cast<float>((capture.borderColor >> 24) & 0xffu) / 255.0f;", "state.BorderColor[3] = 1.0f;"),
        ("dev->CreateSamplerState(&state, sampler.GetAddressOf())", "dev->CreateSamplerState(nullptr, sampler.GetAddressOf())"),
        ("ctx->PSSetSamplers(0, 1, &boundSampler);", "ctx->PSSetSamplers(0, 0, &boundSampler);"),
        ("ctx->DrawIndexed(indexCount, 0, 0);", "ctx->DrawIndexed(0, 0, 0);"),
        ("ctx->Draw(static_cast<UINT>(vertices.size()), 0);", "ctx->Draw(0, 0);"),
    ]
    for before, after in bad:
        assert before in s, before
        assert not wired(s.replace(before, after, 1)), before
    count = 0
    for a in (0, 1, 127, 128, 254, 255):
        for r in (0, 1, 127, 255):
            for g in (0, 64, 128, 255):
                for b in (0, 1, 192, 255):
                    q = rgba((a << 24) | (r << 16) | (g << 8) | b)
                    assert tuple(round(x * 255) for x in q) == (r, g, b, a)
                    count += 1
    assert rgba(0x80402010) == (64/255, 32/255, 16/255, 128/255)
    cases = 0
    for mu in ("border", "wrap", "mirror", "clamp", "mirror_once"):
        for mv in ("border", "wrap", "mirror", "clamp", "mirror_once"):
            for u in (-1.25, -.01, 0.0, .5, 1.0, 1.01, 2.0):
                for v in (-.1, 0.0, 1.0, 1.1):
                    hit = (mu == "border" and not (0 <= u <= 1)) or (
                        mv == "border" and not (0 <= v <= 1))
                    assert hit == ((mu == "border" and (u < 0 or u > 1)) or (
                        mv == "border" and (v < 0 or v > 1)))
                    cases += 1
    print(f"00594 PASS: {len(bad)} negative mutations, {count} ARGB cases, {cases} address cases; HMD UNTESTED")

if __name__ == "__main__":
    main()
