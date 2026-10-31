#!/usr/bin/env python3
"""Live game D3D9 DEFAULT DYNAMIC LockRect -> native Draw and fail-closed regression."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hdr = (root / "src/vr/d3d11/live_game_dynamic_texture.hpp").read_text(encoding="utf-8")

def connected(source, header):
    try:
        mirror = source.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
        draw = source.split("bool submit(", 1)[1].split("bool observe_source_device(", 1)[0]
        observe = source.split("void observe(", 1)[1].split("} // namespace", 1)[0]
    except IndexError:
        return False
    return all(s in mirror for s in [
        "const auto sourceRoute = dynamic_texture::source_route(",
        "gpuRenderTarget);",
        "sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
        "sourceRoute == dynamic_texture::SourceRoute::dynamic_default &&",
        "desc.Usage != base.Usage",
        "capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
        "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
        "const HRESULT unlockResult = gpuRenderTarget ?",
        "capture.texture->UnlockRect(level);",
        "if (FAILED(lockResult)) return false;",
        "if (FAILED(unlockResult)) return false;",
        "if (!readable) return false;",
        "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
        "dev->CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())"
    ]) and all(s in draw for s in [
        "mirror_texture(dev, capture, sampledView, sampledSampler)",
        "ctx->PSSetShaderResources(0, 1, &boundView);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"
    ]) and all(s in observe for s in [
        "if (!submit(s, vertices, indices, indexCount, type, capture, output))",
        "s.frameBatch.abort();",
        "++s.failed;"
    ]) and all(s in header for s in [
        "usage == kDynamicUsage ? SourceRoute::dynamic_default",
        "if (supportedRenderTarget) return SourceRoute::render_target_readback;",
        "static_cast<std::uint64_t>(pitch) >= rowBytes"
    ])

assert connected(src,hdr), "dynamic game source -> native Draw/Indexed disconnected"
mutations=0
for old in [
    "const auto sourceRoute = dynamic_texture::source_route(",
    "sourceRoute == dynamic_texture::SourceRoute::unsupported) return false;",
    "sourceRoute == dynamic_texture::SourceRoute::dynamic_default &&",
    "desc.Usage != base.Usage",
    "capture.texture->LockRect(level, &lock, nullptr, D3DLOCK_READONLY)",
    "dynamic_texture::readable_pitch(lock.Pitch, rowBytes)",
    "if (FAILED(lockResult)) return false;",
    "if (FAILED(unlockResult)) return false;",
    "if (!readable) return false;",
    "dev->CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);"
]:
    assert old in src and not connected(src.replace(old,"/* broken */",1),hdr),old
    mutations+=1
for old in [
    "usage == kDynamicUsage ? SourceRoute::dynamic_default",
    "static_cast<std::uint64_t>(pitch) >= rowBytes"
]:
    assert old in hdr and not connected(src,hdr.replace(old,"/* broken */",1)),old
    mutations+=1
compiler=shutil.which("g++") or shutil.which("clang++")
assert compiler, "C++ compiler required"
with TemporaryDirectory(prefix="dx11-dynamic-00694-") as tmp:
    binary=Path(tmp)/"probe"
    run=subprocess.run([compiler,"-std=c++17","-O2","-Wall","-Wextra",
        "-Werror","-pedantic",str(root/"tools/dx11_game_dynamic_texture_probe_00694.cpp"),
        "-o",str(binary)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    run=subprocess.run([str(binary)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
print(f"00694 PASS: game DEFAULT DYNAMIC mip snapshots + native Draw/Indexed; {mutations} destructive regressions; Quest3/VDXR UNTESTED")
