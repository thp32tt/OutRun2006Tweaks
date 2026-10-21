#!/usr/bin/env python3
"""GAME_RT_16BIT_TO_NATIVE_SCENE: real D3D9 DEFAULT RT -> native DX11 Draw."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess, shutil
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
decoder=(root/"src/vr/d3d11/live_game_render_target_readback.hpp").read_text(encoding="utf-8")
formats={"D3DFMT_R5G6B5":"rgb565","D3DFMT_A1R5G5B5":"argb1555",
         "D3DFMT_A4R4G4B4":"argb4444","D3DFMT_X1R5G5B5":"xrgb1555",
         "D3DFMT_X4R4G4B4":"xrgb4444"}
def wired(s,h):
    try:
        mirror=s.split("bool mirror_texture(",1)[1].split("bool submit(",1)[0]
        draw=s.split("bool submit(",1)[1].split("bool observe_source_device(",1)[0]
    except IndexError: return False
    a=all(("base.Format == "+f+" ? native_rt_readback::Layout::"+v) in mirror
          for f,v in formats.items())
    b=all(("case Layout::"+v+":") in h and ("layout != Layout::"+v) in h
          for v in formats.values())
    c=all(x in mirror for x in (
      "native_rt_readback::sampleable(rtLayout, capture.srgbTexture)",
      "if (sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
      "const UINT sourceTexelBytes = packed16 ? 2u",
      "const UINT uploadPitch = ((packed16 || luminance) || rgb24 || rgbaSwizzle)",
      "gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())",
      "readbackSurface->LockRect(&lock, nullptr, D3DLOCK_READONLY)",
      "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
      "if (!native_rt_readback::unpack_row(",
      "source, destination, desc.Width, rtLayout)",
      "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
      "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())"))
    d=all(x in draw for x in (
      "mirror_texture(dev, capture, sampledView, sampledSampler)",
      "ctx->PSSetShaderResources(0, 1, &boundView);",
      "ctx->DrawIndexed(indexCount, 0, 0);",
      "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"))
    e=all(x in h for x in (
      '#include "packed_texture_16bit.hpp"',
      "packed_texture16::unpack_row(source, destination, width, packing);",
      "layout == Layout::argb1555 ?"))
    return a and b and c and d and e
assert wired(src,decoder), "RT16 staging/source/native Draw disconnected"
mutations=0
for f,v in formats.items():
    old="base.Format == "+f+" ? native_rt_readback::Layout::"+v
    # Cube reflections also carry 16-bit D3D9 color formats. Mutation must
    # strike the original 00692 offscreen 2D RT producer, not its cube sibling.
    prefix, sep, suffix = src.partition("bool mirror_texture(")
    assert sep and old in suffix, "2D RT color layout missing"
    broken = prefix + sep + suffix.replace(
        old, "false ? native_rt_readback::Layout::"+v, 1)
    assert not wired(broken, decoder), "2D RT negative mutation escaped"
    mutations+=1
for old in (
    "native_rt_readback::sampleable(rtLayout, capture.srgbTexture)",
    "gameDevice->GetRenderTargetData(sourceSurface.Get(), readbackSurface.Get())",
    "if (!native_rt_readback::unpack_row(",
    "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"):
    assert old in src and not wired(src.replace(old,"false",1),decoder)
    mutations+=1
for old in ("packed_texture16::unpack_row(source, destination, width, packing);",
            "layout != Layout::rgb565"):
    assert old in decoder and not wired(src,decoder.replace(old,"// disconnected",1))
    mutations+=1
compiler=shutil.which("g++") or shutil.which("clang++")
assert compiler, "C++ compiler required"
with TemporaryDirectory(prefix="dx11-rt16-00692-") as tmp:
    binary=Path(tmp)/"probe"
    r=subprocess.run([compiler,"-std=c++17","-O2","-Wall","-Wextra","-Werror",
       "-pedantic",str(root/"tools/dx11_game_rt_16bit_probe_00692.cpp"),"-o",str(binary)],
       capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    r=subprocess.run([str(binary)],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
print("00692 PASS: five RT16 layouts, sRGB/invalid fallback and "+str(mutations)+" negative mutations; HMD UNTESTED")
