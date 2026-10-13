#!/usr/bin/env python3
"""00685: real game world-space near-camera Draw/Indexed may use D3D11 homogeneous clipping."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr = (root / "src/vr/d3d11/live_game_object_clip.hpp").read_text()

def connected(code):
    span = code[code.index("bool translate_vertices("):code.index("bool observe_source_device(")]
    entry = code[code.index("void observe("):code.index("} // namespace", code.index("void observe("))]
    return all(t in code for t in (
        '#include "live_game_object_clip.hpp"',
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        "s.pending = true;",
    )) and all(t in span for t in (
        "clip[row] * matrix.m[row][col]",
        "if (!game_native_object_clip_position(clip))",
        "std::copy(clip.begin(), clip.end(), v.clip);",
    )) and all(t in entry for t in (
        "translate_vertices(bytes, vertexCount, stride, vp,",
        "if (indices)",
        "submit(s, vertices,",
        "s.frameBatch.succeeded(",
    )) and "clip[3] <= 0.0f" not in span

assert connected(src), "live OutRun world WVP -> D3D11 Draw/Indexed path disconnected"
for token in (
    '#include "live_game_object_clip.hpp"',
    "if (!game_native_object_clip_position(clip))",
    "std::copy(clip.begin(), clip.end(), v.clip);",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
):
    edited = src.replace(token, "/* stripped for regression */", 1)
    assert edited != src and not connected(edited), token

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
probe = r"""
#include "live_game_object_clip.hpp"
#include <array>
#include <cassert>
#include <limits>
using namespace outrun::vr::dx11::live_game_frame;
using V = std::array<float,4>;
int main() {
    // Menu overlays and ordinary in-front world geometry retain native routing.
    assert(game_native_object_clip_position(V{0.0f, 0.0f, 0.1f, 1.0f}));
    assert(game_native_object_clip_position(V{0.0f, 0.0f, 0.2f, 0.5f}));
    // One vertex behind the camera is legal input to the homogeneous clipper.
    // Both Draw and DrawIndexed submit this same converted NativeVertex span.
    assert(game_native_object_clip_position(V{0.0f, 0.0f,-0.1f,-0.5f}));
    assert(game_native_object_clip_position(V{0.1f, 0.2f, 0.3f, 2.0f}));
    // No division by zero or undefined coordinates can reach the GPU.
    assert(!game_native_object_clip_position(V{0.0f, 0.0f, 0.0f, 0.0f}));
    assert(!game_native_object_clip_position(V{0.0f, 0.0f, 0.0f,-0.0f}));
    const float inf = std::numeric_limits<float>::infinity();
    const float nan = std::numeric_limits<float>::quiet_NaN();
    assert(!game_native_object_clip_position(V{0.0f, 0.0f, 0.0f, inf}));
    assert(!game_native_object_clip_position(V{inf, 0.0f, 0.0f, 1.0f}));
    assert(!game_native_object_clip_position(V{0.0f, nan, 0.0f, 1.0f}));
    assert(!game_native_object_clip_position(V{0.0f, 0.0f, inf, 1.0f}));
}
"""
with TemporaryDirectory(prefix="dx11-00685-") as d:
    tmp = Path(d)
    (tmp / "probe.cpp").write_text(probe)
    cmd = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
           "-Werror", "-pedantic", str(tmp / "probe.cpp"), "-o", str(tmp / "probe")]
    cases = (
        ("valid clipped world", hdr, True),
        ("negative W rejected", hdr.replace("clip[3] != 0.0f", "clip[3] > 0.0f"), False),
        ("zero W admitted", hdr.replace("clip[3] != 0.0f", "true"), False),
        ("invalid W admitted", hdr.replace("std::isfinite(clip[3])", "true"), False),
        ("invalid X admitted", hdr.replace("std::isfinite(clip[0])", "true"), False),
        ("invalid Y admitted", hdr.replace("std::isfinite(clip[1])", "true"), False),
        ("invalid Z admitted", hdr.replace("std::isfinite(clip[2])", "true"), False),
    )
    for name, contents, should_pass in cases:
        assert name == "valid clipped world" or contents != hdr, name
        (tmp / "live_game_object_clip.hpp").write_text(contents)
        result = subprocess.run(cmd, text=True, capture_output=True)
        if result.returncode == 0:
            result = subprocess.run([str(tmp / "probe")], text=True, capture_output=True)
        assert (result.returncode == 0) == should_pass, (name, result.stderr)
print("PASS: near-camera live Draw/Indexed WVP, DX9Ex fallback, 5 source + 6 C++ destructive regressions")
