#!/usr/bin/env python3
"""Game-created D3D9 R/RG FLOAT mip family reaches native Draw/Indexed safely."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hdr = (root / "src/vr/d3d11/live_game_float_vector_texture.hpp").read_text(encoding="utf-8")
formats = {
    "D3DFMT_R16F": ("r16f", "DXGI_FORMAT_R16_FLOAT"),
    "D3DFMT_G16R16F": ("rg16f", "DXGI_FORMAT_R16G16_FLOAT"),
    "D3DFMT_R32F": ("r32f", "DXGI_FORMAT_R32_FLOAT"),
    "D3DFMT_G32R32F": ("rg32f", "DXGI_FORMAT_R32G32_FLOAT"),
}

def connected(source, decoder):
    try:
        mirror = source.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = source.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    except IndexError:
        return False
    return (
        all("base.Format == " + fmt for fmt in formats) and
        all("float_vector_texture::Layout::" + layout in mirror and
            "base.Format == " + fmt + " ? " + native in mirror
            for fmt, (layout, native) in formats.items()) and
        all("case Layout::" + layout + ":" in decoder
            for layout in ["r16f", "rg16f", "r32f", "rg32f"]) and
        all(s in mirror for s in [
            "if (capture.srgbTexture && floatVector) return false;",
            "floatVector ? float_vector_texture::source_bytes_per_texel(floatVectorLayout)",
            "float_vector_texture::copy_row(source, destination, desc.Width, floatVectorLayout)",
            "desc.MipLevels = levels; desc.ArraySize = 1;",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
            "FAILED(lockResult)",
            "if (!readable) return false;",
        ]) and
        all(s in draw for s in [
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        ]) and
        "static_cast<std::size_t>(width) * source_bytes_per_texel(layout)" in decoder
    )

assert connected(src, hdr), "live R/RG float source->native Draw integration disconnected"
mutations = 0
for fmt, (_, native) in formats.items():
    old = "base.Format == " + fmt + " ? " + native
    assert old in src and not connected(src.replace(old, "false ? " + native, 1), hdr)
    mutations += 1
for old in [
    "if (capture.srgbTexture && floatVector) return false;",
    "floatVector ? float_vector_texture::source_bytes_per_texel(floatVectorLayout)",
    "float_vector_texture::copy_row(source, destination, desc.Width, floatVectorLayout)",
    "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
    "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
]:
    assert old in src and not connected(src.replace(old, "/* broken */", 1), hdr)
    mutations += 1
for old in [
    "case Layout::r16f: return 2u;",
    "static_cast<std::size_t>(width) * source_bytes_per_texel(layout)",
]:
    assert old in hdr and not connected(src, hdr.replace(old, "/* broken */", 1))
    mutations += 1
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "C++ compiler required"
with TemporaryDirectory(prefix="dx11-float-vector-00693-") as tmp:
    binary = Path(tmp) / "probe"
    result = subprocess.run([compiler, "-std=c++17", "-O2", "-Wall",
         "-Wextra", "-Werror", "-pedantic",
         str(root/"tools/dx11_game_float_vector_probe_00693.cpp"), "-o", str(binary)],
         capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([str(binary)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
print("00693 PASS: native R/RG FLOAT family, source/Draw wiring and "+
      str(mutations)+" destructive regressions; Quest3/VDXR UNTESTED")
