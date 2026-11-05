#!/usr/bin/env python3
"""00697: native D3D11 game eye -> R23 x64 host -> OpenXR shader transfer."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
def source(path):
    return (ROOT / path).read_text(encoding="utf-8")
header = source("vrhost/src/runtime/native_direct_stereo_pair.hpp")
host = source("vrhost/src/main.cpp")
shader = source("vrhost/src/stereo_shader.hpp")
smoke = source("vrhost/tests/native_direct_eye_pair_smoke.cpp")
r23 = source("vrhost/src/main_r23.cpp")
cmake = source("vrhost/CMakeLists.txt")

def wired(h=header, c=host, s=shader):
    return (
        "IsSupportedSourceFormat(d.Format)" in c and
        "IsSrgbView(format)" in h and
        "DXGI_FORMAT_B8G8R8A8_UNORM_SRGB" in h and
        "DXGI_FORMAT_R8G8B8A8_UNORM_SRGB" in h and
        "IsSupportedSourceFormat(d.Format)" in h and
        c.count("p->sourceIsSrgbView =") == 2 and
        c.count("OutRunVrNativeEyePair::IsSrgbView(sourceFormat)") == 2 and
        "static_assert(sizeof(BlitParams) == 32u" in c and
        "float SourceIsSrgbView;" in s and
        "else if (SourceIsSrgbView > 0.5)" in s and
        "linearColor = saturate(src.rgb);" in s and
        "linearColor = SrgbToLinear(saturate(src.rgb));" in s and
        s.index("if (SourceIsScRgb > 0.5)") <
        s.index("else if (SourceIsSrgbView > 0.5)") <
        s.index("else\n        // Legacy unorm")
    )

assert wired(), "R23 source formats and BOTH OpenXR draw paths must use typed-SRGB shader branch"
assert '#include "main.cpp"' in r23 and "src/main_r23.cpp" in cmake, (
    "The edited compositor must be used by the actual production x64 host")
assert "Native two-eye host source/projection contract PASS" in smoke
assert "BGRA sRGB native stereo source must enter OpenXR hold" in smoke
for key in (
    "IsSupportedSourceFormat(d.Format)",
    "p->sourceIsSrgbView =",
    "OutRunVrNativeEyePair::IsSrgbView(sourceFormat)",
):
    assert not wired(c=host.replace(key, "/* disconnected */", 1)), key
for key in ("IsSrgbView(format)", "DXGI_FORMAT_R8G8B8A8_UNORM_SRGB"):
    assert not wired(h=header.replace(key, "/* disconnected */", 1)), key
for key in ("else if (SourceIsSrgbView > 0.5)", "linearColor = saturate(src.rgb);",
            "linearColor = SrgbToLinear(saturate(src.rgb));"):
    assert not wired(s=shader.replace(key, "/* removed */", 1)), key

# Compile the real header with a minimal D3D11 ABI stub. The host's own
# Windows x64 smoke still compiles the same header against the actual SDK.
compiler = shutil.which("g++") or shutil.which("clang++")
if compiler:
    d3d_stub = """
#pragma once
#include <cstdint>
enum DXGI_FORMAT { DXGI_FORMAT_UNKNOWN, DXGI_FORMAT_B8G8R8A8_UNORM,
    DXGI_FORMAT_R8G8B8A8_UNORM, DXGI_FORMAT_R10G10B10A2_UNORM,
    DXGI_FORMAT_R16G16B16A16_FLOAT, DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,
    DXGI_FORMAT_R8G8B8A8_UNORM_SRGB };
enum D3D11_USAGE { D3D11_USAGE_DEFAULT };
// Keep this SDK enum visible even when the source's templated context guard
// is not instantiated by the portable color-format-only regression.
enum D3D11_DEVICE_CONTEXT_TYPE {
    D3D11_DEVICE_CONTEXT_IMMEDIATE = 0,
    D3D11_DEVICE_CONTEXT_DEFERRED = 1
};
constexpr unsigned D3D11_BIND_RENDER_TARGET = 0x20u;
constexpr unsigned D3D11_BIND_SHADER_RESOURCE = 0x8u;
struct DXGI_SAMPLE_DESC { unsigned Count{}, Quality{}; };
struct D3D11_TEXTURE2D_DESC {
    unsigned Width{}, Height{}, MipLevels{}, ArraySize{};
    DXGI_FORMAT Format{DXGI_FORMAT_UNKNOWN};
    DXGI_SAMPLE_DESC SampleDesc{};
    D3D11_USAGE Usage{D3D11_USAGE_DEFAULT};
    unsigned BindFlags{}, CPUAccessFlags{}, MiscFlags{};
};
"""
    probe = """
#include <cassert>
#include "runtime/native_direct_stereo_pair.hpp"
int main() {
    using namespace OutRunVrNativeEyePair;
    D3D11_TEXTURE2D_DESC a{};
    a.Width = a.Height = 96; a.MipLevels = a.ArraySize = 1;
    a.SampleDesc.Count = 1;
    a.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
    a.Format = DXGI_FORMAT_B8G8R8A8_UNORM_SRGB;
    auto b = a;
    assert(IsSrgbView(a.Format) && Compatible(10, 11, 12, 96, 96, a, b));
    a.Format = b.Format = DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
    assert(IsSrgbView(a.Format) && Compatible(10, 11, 12, 96, 96, a, b));
    b.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    assert(!Compatible(10, 11, 12, 96, 96, a, b));
    a.Format = b.Format;
    assert(!IsSrgbView(a.Format) && Compatible(10, 11, 12, 96, 96, a, b));
    a.Format = b.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    assert(!IsSrgbView(a.Format) && Compatible(10, 11, 12, 96, 96, a, b));
    assert(!Compatible(10, 10, 12, 96, 96, a, b));
    b.SampleDesc.Count = 4;
    assert(!Compatible(10, 11, 12, 96, 96, a, b));
}
"""
    with TemporaryDirectory(prefix="dx11-host-srgb-00697-") as tmp:
        tmp = Path(tmp)
        (tmp / "d3d11.h").write_text(d3d_stub)
        (tmp / "test.cpp").write_text(probe)
        binary = tmp / "test"
        compile_result = subprocess.run(
            [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
             "-I", str(tmp), "-I", str(ROOT / "vrhost/src"),
             str(tmp / "test.cpp"), "-o", str(binary)],
            capture_output=True, text=True)
        assert compile_result.returncode == 0, compile_result.stderr
        executed = subprocess.run([str(binary)], capture_output=True, text=True)
        assert executed.returncode == 0, executed.stderr
    print("00697 C++17 sRGB/legacy/scRGB + negative alias/MSAA PASS")
else:
    print("00697 C++17 compile unavailable on runner; structural checks only")
print("00697 x64 native-eye importer -> R23 menu/projection -> HLSL transfer PASS; runtime HMD UNTESTED")
