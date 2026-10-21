#!/usr/bin/env python3
"""00742: game-created mipmapped D3D9 render targets -> complete native D3D11 sampler, opt-in fallback."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (ROOT / "src/vr/d3d11/live_game_render_target_readback.hpp").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def wired(src, hdr):
    try:
        mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        sampled = mirror.split("for (UINT level = 0; level < levels; ++level) {", 1)[1]
        draw = src.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
    except IndexError:
        return False
    return (
        "if (gpuRenderTarget && levels != 1u) return false;" not in mirror
        and "native_game_texture_upload_bytes(" in mirror
        and "sourceLevels > kMaxNativeGameAtlasMipLevels" in mirror
        and "if (gpuRenderTarget && !native_rt_readback::bounded_gpu_snapshot(" in mirror
        and "base.Width, base.Height, levels, rtLayout))" in mirror
        and "kMaxLiveRtReadbackSurfaceBytes = 16ull << 20u" in hdr
        and "kMaxLiveRtReadbackMipChainBytes = 24ull << 20u" in hdr
        and "FAILED(capture.texture->GetDevice(gameDevice.GetAddressOf()))" in mirror
        and "if (gpuRenderTarget) {" in sampled
        and "readbackSurface.Reset();" in sampled
        and "capture.texture->GetSurfaceLevel(level, sourceSurface.GetAddressOf())" in sampled
        and "FAILED(sourceSurface->GetDesc(&sourceDesc))" in sampled
        and "!(sourceDesc.Usage & D3DUSAGE_RENDERTARGET)" in sampled
        and "sourceDesc.MultiSampleType != D3DMULTISAMPLE_NONE" in sampled
        and "native_rt_readback::matching_mip_extent(" in sampled
        and "sourceDesc.Width != desc.Width || sourceDesc.Height != desc.Height" in sampled
        and "desc.Width, desc.Height, desc.Format, D3DPOOL_SYSTEMMEM," in sampled
        and "gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())" in sampled
        and "readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY)" in sampled
        and "if (!native_rt_readback::unpack_row(" in sampled
        and "readbackSurface->UnlockRect();" in sampled
        and "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())" in mirror
        and "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())" in mirror
        and "mirror_texture(dev, capture, sampledView, sampledSampler)" in draw
        and "mirror_texture(dev, second, stage1View, stage1Sampler)" in draw
        and "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in draw
        and "else ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in draw
        and "constexpr bool matching_mip_extent(" in hdr
        and "level >= 32u" in hdr
        and "levelWidth == (expectedWidth ? expectedWidth : 1u)" in hdr
    )

assert wired(source, header), "Each real RT mip must be captured, uploaded and sampled in Draw/Indexed"
assert "python tools/test_dx11_game_rt_mips_00742.py" in workflow
mutations = [
    ("native_rt_readback::bounded_gpu_snapshot(", "/* removed current-mip budget */("),
    ("sourceLevels > kMaxNativeGameAtlasMipLevels",
     "sourceLevels > 99u /* invalid mip provenance */"),
    ("capture.texture->GetSurfaceLevel(level, sourceSurface.GetAddressOf())",
     "capture.texture->GetSurfaceLevel(0, sourceSurface.GetAddressOf())"),
    ("readbackSurface.Reset();", "/* stale base-level surface */"),
    ("native_rt_readback::matching_mip_extent(", "/* no extent proof */("),
    ("sourceDesc.Width != desc.Width || sourceDesc.Height != desc.Height",
     "false /* wrong level dimensions */"),
    ("desc.Width, desc.Height, desc.Format, D3DPOOL_SYSTEMMEM,",
     "base.Width, base.Height, base.Format, D3DPOOL_SYSTEMMEM,"),
    ("gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())",
     "false /* no GPU snapshot */"),
    ("mirror_texture(dev, second, stage1View, stage1Sampler)",
     "false /* missing second sampler */"),
    ("ctx->DrawIndexed(indexCount, 0, 0);", "/* lost indexed game draw */"),
]
for old, new in mutations:
    assert old in source and not wired(source.replace(old, new, 1), header), old
assert not wired(source, header.replace(
    "level >= 32u", "level >= 0u", 1)), "header mutation undetected"

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "C++17 compiler required"
with TemporaryDirectory(prefix="dx11-rt-mips-00742-") as tmp:
    binary = Path(tmp) / "rt_mips"
    command = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
               "-Werror", "-pedantic", "-I", str(ROOT),
               str(ROOT / "tools/dx11_game_rt_mip_probe_00742.cpp"), "-o", str(binary)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([str(binary)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
print("00742 PASS: per-mip D3D9 RT readback -> native stage0/stage1 Draw/Indexed; 9 negative checks; runtime UNTESTED")
