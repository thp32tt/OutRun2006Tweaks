#!/usr/bin/env python3
"""00699: real D3D9 2K menu/car texture atlas upload to native Draw/DrawIndexed."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
bridge = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (ROOT / "src/vr/d3d11/native_game_texture_atlas_budget.hpp").read_text()
r30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
workflow = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(src, budget):
    mirror = src.split("bool mirror_texture(", 1)[1].split("bool submit(", 1)[0]
    return all((
        '#include "native_game_texture_atlas_budget.hpp"' in src,
        "sourceLevels > 12u" in mirror,
        "base.Width > kMaxNativeGameAtlasDimension" in mirror,
        "base.Height > kMaxNativeGameAtlasDimension" in mirror,
        "if (gpuRenderTarget && (base.Width > 1024u || base.Height > 1024u))" in mirror,
        "nativeFormat == DXGI_FORMAT_R32G32B32A32_FLOAT ? 16u" in mirror,
        "nativeFormat == DXGI_FORMAT_R16G16B16A16_FLOAT" in mirror,
        "nativeFormat == DXGI_FORMAT_R16G16B16A16_UNORM" in mirror,
        "nativeFormat == DXGI_FORMAT_R32G32_FLOAT) ? 8u : 4u;" in mirror,
        "const UINT atlasBlockBytes = compressed ?" in mirror,
        "if (!native_game_texture_upload_bytes(" in mirror,
        "compressed ? 0u : atlasTexelBytes, atlasBlockBytes))" in mirror,
        mirror.find("native_game_texture_upload_bytes(") >= 0 and
        mirror.find("native_game_texture_upload_bytes(") < mirror.find(
            "ComPtr<IDirect3DSurface9> readbackSurface;"),
        "CreateTexture2D(&desc, initial.data(), texture.GetAddressOf())" in mirror,
        "CreateShaderResourceView(texture.Get(), nullptr, view.GetAddressOf())" in mirror,
        "mirror_texture(dev, capture, sampledView, sampledSampler)" in src,
        "ctx->PSSetShaderResources(0, 1, &boundView);" in src,
        "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in src,
        "else ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in src,
        "void observe_linear(" in src and "void observe_indexed(" in src,
        "before_game_present(" in src and "s.frameBatch.publishable(s.pending)" in src,
        "observe_unavailable_game_draw(device);" in r30,
        "kMaxNativeGameAtlasUploadBytes = 24ull * 1024ull * 1024ull" in budget,
    ))

assert integrated(bridge, header)
# Destructive source proof: no source limit/real upload/real draw is optional.
for old in ("sourceLevels > 12u", "if (!native_game_texture_upload_bytes(",
            "mirror_texture(dev, capture, sampledView, sampledSampler)",
            "ctx->PSSetShaderResources(0, 1, &boundView);",
            "if (ib) ctx->DrawIndexed(indexCount, 0, 0);"):
    assert old in bridge
    assert not integrated(bridge.replace(old, "/* missing 00699 integration */", 1), header), old
assert "python tools/test_dx11_game_texture_atlas_00699.py" in workflow

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
code = r"""
#include "native_game_texture_atlas_budget.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr auto menu2k = native_game_texture_upload_bytes(2048, 2048, 12, 4, 0);
static_assert(menu2k > 16ull*1024ull*1024ull);
static_assert(menu2k < kMaxNativeGameAtlasUploadBytes);
static_assert(native_game_texture_upload_bytes(2048, 2048, 1, 4, 0)
              == 2048ull*2048ull*4ull);
static_assert(native_game_texture_upload_bytes(1024, 1024, 11, 8, 0) > 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 12, 0, 8) > 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 12, 0, 16) > 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 1, 8, 0) == 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 12, 16, 0) == 0);
static_assert(native_game_texture_upload_bytes(4096, 512, 1, 4, 0) == 0);
static_assert(native_game_texture_upload_bytes(512, 4096, 1, 4, 0) == 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 13, 4, 0) == 0);
static_assert(native_game_texture_upload_bytes(0, 2048, 1, 4, 0) == 0);
static_assert(native_game_texture_upload_bytes(2048, 0, 1, 4, 0) == 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 0, 4, 0) == 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 1, 4, 8) == 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 1, 0, 0) == 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 1, 0, 12) == 0);
static_assert(native_game_texture_upload_bytes(2048, 2048, 1, 2, 0) == 0);
int main() { return 0; }
"""
with TemporaryDirectory(prefix="dx11-00699-") as temp:
    path = Path(temp)
    (path / "probe.cpp").write_text(code)
    result = subprocess.run(
        [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-I", str(ROOT / "src/vr/d3d11"),
         str(path / "probe.cpp"), "-o", str(path / "probe")],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert subprocess.run([str(path / "probe")]).returncode == 0
print("PASS 00699: game 2K texture atlas native SRV/Draw/IndexedDraw, capped mip memory, RT DX9Ex fallback")
