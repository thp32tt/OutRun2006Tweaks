#!/usr/bin/env python3
"""00660: real D3D9 RGBA memory -> native D3D11 game Draw/DrawIndexed source contract."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"

def connected(src):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = src.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
        rgba_branch = mirror.split("else if (rgbaSwizzle)", 1)[1].split("else if (tenBit)", 1)[0]
    except IndexError:
        # Removing the producer branch is an expected destructive mutation.
        return False
    return ('#include "live_game_rgba_texture.hpp"' in src
        and "base.Format == D3DFMT_X8B8G8R8 ?" in rgba_branch
        and all(s in mirror for s in (
            "base.Format == D3DFMT_A8B8G8R8 ||",
            "base.Format == D3DFMT_X8B8G8R8;",
            "|| packed16 || luminance || rgb24 || rgbaSwizzle",
            "capture.srgbTexture ?",
            "DXGI_FORMAT_B8G8R8A8_UNORM_SRGB : DXGI_FORMAT_B8G8R8A8_UNORM",
            "const UINT uploadPitch = ((packed16 || luminance) || rgb24 || rgbaSwizzle)",
            "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
            "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
            "else if (rgbaSwizzle)",
            "rgba_texture::unpack_row(source, destination, desc.Width,",
            "base.Format == D3DFMT_X8B8G8R8 ?",
            "rgba_texture::Layout::xrgb : rgba_texture::Layout::argb);",
            "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
            "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
        )) and all(s in draw for s in (
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "ctx->DrawIndexed(indexCount, 0, 0);",
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        )))

def main():
    src = SOURCE.read_text(encoding="utf-8")
    assert connected(src), "live RGBA D3D9 mip -> native Draw chain is broken"
    mutations = (
        ('#include "live_game_rgba_texture.hpp"', '#include "live_game_rgb24_texture.hpp"'),
        ('base.Format == D3DFMT_A8B8G8R8 ||', 'base.Format == D3DFMT_A8R8G8B8 ||'),
        ('base.Format == D3DFMT_X8B8G8R8;', 'base.Format == D3DFMT_X8R8G8B8;'),
        ('|| packed16 || luminance || rgb24 || rgbaSwizzle', '|| packed16 || luminance || rgb24'),
        ('((packed16 || luminance) || rgb24 || rgbaSwizzle)', '((packed16 || luminance) || rgb24)'),
        ('dynamic_texture::readable_pitch(lock.Pitch, rowBytes)', 'false'),
        ('else if (rgbaSwizzle)', 'else if (false)'),
        ('rgba_texture::unpack_row(source, destination, desc.Width,', 'std::memcpy(destination, source, rowBytes); //'),
        ('base.Format == D3DFMT_X8B8G8R8 ?', 'false ?'),
        ('rgba_texture::Layout::xrgb : rgba_texture::Layout::argb);', 'rgba_texture::Layout::argb : rgba_texture::Layout::argb);'),
        ('if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;', 'if (false) return false;'),
        ('mirror_texture(dev, capture, sampledView, sampledSampler)', 'false'),
        ('ctx->DrawIndexed(indexCount, 0, 0);', 'ctx->DrawIndexed(0, 0, 0);'),
    )
    for old, broken in mutations:
        assert old in src, "missing original source: " + old
        # 00691's earlier format-to-layout ternary also names X8B8G8R8.
        # Mutate the last occurrence, which owns the actual CPU swizzle
        # of non-DEFAULT source mips; never mutate a different feature's gate.
        if old == 'base.Format == D3DFMT_X8B8G8R8 ?':
            prefix, match, suffix = src.rpartition(old)
            mutant = prefix + broken + suffix if match else src
        else:
            mutant = src.replace(old, broken, 1)
        assert not connected(mutant), "destructive mutation escaped: " + old
    print(f"00660 PASS: {len(mutations)} live RGBA/mip/Draw destructive mutations; HMD UNTESTED")


def test_native_render_target_readback():
    """00691: DEFAULT game RT staging -> format conversion -> native Draw/Indexed."""
    import shutil
    import subprocess
    from tempfile import TemporaryDirectory
    src = SOURCE.read_text(encoding="utf-8")
    def wired(code):
        try:
            mirror = code.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
            draw = code.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
        except IndexError:
            return False
        return all(token in mirror for token in (
            'native_rt_readback::sampleable(rtLayout, capture.srgbTexture)',
            'base.Format == D3DFMT_A8B8G8R8 ? native_rt_readback::Layout::a8b8g8r8',
            'base.Format == D3DFMT_X8B8G8R8 ? native_rt_readback::Layout::x8b8g8r8',
            'base.Format == D3DFMT_A2R10G10B10 ? native_rt_readback::Layout::a2r10g10b10',
            'base.Format == D3DFMT_A2B10G10R10 ? native_rt_readback::Layout::a2b10g10r10',
            'gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())',
            'readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY)',
            'dynamic_texture::readable_pitch(lock.Pitch, rowBytes)',
            'if (!native_rt_readback::unpack_row(',
            'source, destination, desc.Width, rtLayout)',
            'readbackSurface->UnlockRect();',
            'const HRESULT unlockResult = gpuRenderTarget ?',
            'dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())',
            'dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())',
        )) and all(token in draw for token in (
            'mirror_texture(dev, capture, sampledView, sampledSampler)',
            'ctx->PSSetShaderResources(0, 1, &boundView);',
            'ctx->DrawIndexed(indexCount, 0, 0);',
            'ctx->Draw(static_cast<UINT>(vertices.size()), 0);',
        ))
    assert '#include "live_game_render_target_readback.hpp"' in src
    assert wired(src), "game render-target staging -> native Draw disconnected"
    for before, after in (
        ('native_rt_readback::sampleable(rtLayout, capture.srgbTexture)', 'false'),
        ('base.Format == D3DFMT_A8B8G8R8 ? native_rt_readback::Layout::a8b8g8r8', 'false ? native_rt_readback::Layout::a8b8g8r8'),
        ('base.Format == D3DFMT_A2R10G10B10 ? native_rt_readback::Layout::a2r10g10b10', 'false ? native_rt_readback::Layout::a2r10g10b10'),
        ('gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())', 'E_FAIL'),
        ('readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY)', 'E_FAIL'),
        ('if (!native_rt_readback::unpack_row(', 'if (false && !native_rt_readback::unpack_row('),
        ('dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())', 'E_FAIL'),
        ('ctx->DrawIndexed(indexCount, 0, 0);', 'ctx->DrawIndexed(0, 0, 0);'),
    ):
        # The cube producer now uses the same D3D9 color-layout literals.
        # Mutate the 00691 2D RT producer itself, never the preceding six-face
        # cube source. Preserve the original destructive check and negative.
        prefix, sep, rest = src.partition("bool mirror_texture(")
        mirror, end, suffix = rest.partition("bool capture_live_sm3_sampler(")
        assert sep and end, "2D game render-target producer missing"
        if before in mirror:
            mutant = prefix + sep + mirror.replace(before, after, 1) + end + suffix
        else:
            assert before in src, before
            mutant = src.replace(before, after, 1)
        assert not wired(mutant), "escaped destructive case: " + before
    cxx = shutil.which("g++") or shutil.which("clang++")
    assert cxx, "portable C++ compiler required"
    with TemporaryDirectory(prefix="dx11-game-rt-00691-") as temp:
        binary = Path(temp) / "rt_readback"
        run = subprocess.run([cxx, "-std=c++17", "-O2", "-Wall", "-Wextra",
                              "-Werror", "-pedantic",
                              str(ROOT / "tools/dx11_game_rt_readback_probe_00691.cpp"),
                              "-o", str(binary)], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert subprocess.run([str(binary)], check=False).returncode == 0
    print("00691 PASS: BGRA/RGBA/10bit RT readback -> native Draw/Indexed + 8 destructive mutations")

if __name__ == '__main__':
    main()
    test_native_render_target_readback()
