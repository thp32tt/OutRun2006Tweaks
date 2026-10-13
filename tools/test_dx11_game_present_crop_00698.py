#!/usr/bin/env python3
"""00698: crop-safe game Present diagnostic pixels and asynchronous source lifetime."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
r30 = (ROOT/"src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
bridge_h = (ROOT/"src/vr/d3d11/live_game_frame_bridge.hpp").read_text()
bridge = (ROOT/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
provenance = (ROOT/"src/vr/d3d11/native_game_readback_provenance.hpp").read_text()
region = (ROOT/"src/vr/d3d11/native_game_present_region.hpp").read_text()
workflow = (ROOT/".github/workflows/dx11-fast-structural.yml").read_text()

def connected(hook, hdr, impl, prov):
    present = impl.split("void before_game_present(", 1)[-1].split(
        "void before_game_reset(", 1)[0]
    return all((
        "before_game_present(device, sourceRect, dirtyRegion)" in hook,
        "const RECT* sourceRect, const RGNDATA* dirtyRegion) noexcept;" in hdr,
        "const RECT* sourceRect, const RGNDATA* dirtyRegion) noexcept {" in impl,
        "GameNativePresentRegion presentRegion{" in present,
        "sourceRect ? static_cast<std::int64_t>(sourceRect->left)" in present,
        "sourceRect ? static_cast<std::int64_t>(sourceRect->right)" in present,
        "sourceRect ? static_cast<std::int64_t>(sourceRect->bottom)" in present,
        "presentRegion.allows_inset(bb.Width, bb.Height, kWidth, kHeight, 8u)" in present,
        "!outputNow.hasDirtyRegion" in present,
        "outputNow.hasDirtyRegion = dirtyRegion != nullptr;" in present,
        "outputNow.sourceLeft = presentRegion.left;" in present,
        "outputNow.sourceRight = presentRegion.right;" in present,
        "outputNow.sourceBottom = presentRegion.bottom;" in present,
        "!s.previousOutput.same(outputNow)" in present,
        "!oldest.provenance.same_output(s.outputGeneration)" in present,
        "next.provenance.outputGeneration = s.outputGeneration;" in present,
        "s.frameBatch.publishable(s.pending) && outputWritable" in present,
        "sourceLeft == other.sourceLeft" in prov,
        "sourceRight == other.sourceRight" in prov,
        "sourceBottom == other.sourceBottom" in prov,
        "hasDirtyRegion == other.hasDirtyRegion" in prov,
    ))
assert connected(r30, bridge_h, bridge, provenance)
for label, i, token in (
    ("R30 actual Present attribution", 0,
     "before_game_present(device, sourceRect, dirtyRegion)"),
    ("crop reject", 2,
     "presentRegion.allows_inset(bb.Width, bb.Height, kWidth, kHeight, 8u)"),
    ("dirty rectangle rejection", 2, "!outputNow.hasDirtyRegion"),
    ("async generation change", 2, "!s.previousOutput.same(outputNow)"),
    ("late readback owner", 2, "!oldest.provenance.same_output(s.outputGeneration)"),
    ("crop identity", 3, "sourceRight == other.sourceRight"),
    ("dirty mode identity", 3, "hasDirtyRegion == other.hasDirtyRegion"),
):
    variants = [r30, bridge_h, bridge, provenance]
    assert token in variants[i], label
    variants[i] = variants[i].replace(token, "/* deliberately broken 00698 */", 1)
    assert not connected(*variants), label
assert "python tools/test_dx11_game_present_crop_00698.py" in workflow

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
code = r"""
#include "native_game_present_region.hpp"
#include "native_game_readback_provenance.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameNativePresentRegion full{0,0,3440,1440};
static_assert(full.allows_inset(3440,1440,256,144,8));
static_assert(GameNativePresentRegion{3000,0,3440,500}.allows_inset(3440,1440,256,144,8));
static_assert(!GameNativePresentRegion{0,0,1920,1080}.allows_inset(3440,1440,256,144,8));
static_assert(!GameNativePresentRegion{0,0,3440,100}.allows_inset(3440,1440,256,144,8));
static_assert(!GameNativePresentRegion{-1,0,3440,1440}.allows_inset(3440,1440,256,144,8));
static_assert(!GameNativePresentRegion{100,0,50,1440}.allows_inset(3440,1440,256,144,8));
static_assert(!GameNativePresentRegion{0,0,3441,1440}.allows_inset(3440,1440,256,144,8));
static_assert(!GameNativePresentRegion{0,0,3440,1441}.allows_inset(3440,1440,256,144,8));
static_assert(!full.allows_inset(200,100,256,144,8));
static_assert(!full.allows_inset(3440,1440,256,144,4000));
constexpr GameOutputSignature a{0x10u,3440u,1440u,21u,0xabcdu,0,0,3440,1440,false};
static_assert(a.valid());
static_assert(a.same(GameOutputSignature{0x10u,3440u,1440u,21u,0xabcdu,0,0,3440,1440,false}));
static_assert(!a.same(GameOutputSignature{0x10u,3440u,1440u,21u,0xabcdu,3000,0,3440,500,false}));
static_assert(!a.same(GameOutputSignature{0x10u,3440u,1440u,21u,0xabcdu,0,0,3440,1440,true}));
static_assert(!a.same(GameOutputSignature{0x10u,3440u,1440u,21u,0xabcdu,0,0,3000,1440,false}));
static_assert(GameReadbackProvenance{20u,4u,0x10u,2u}.same_output(2u));
static_assert(!GameReadbackProvenance{20u,4u,0x10u,2u}.same_output(3u));
int main() { return 0; }
"""
with TemporaryDirectory(prefix="dx11-00698-") as temporary:
    directory = Path(temporary)
    (directory/"probe.cpp").write_text(code)
    result = subprocess.run(
        [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
         "-pedantic", "-I", str(ROOT/"src/vr/d3d11"),
         str(directory/"probe.cpp"), "-o", str(directory/"probe")],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert subprocess.run([str(directory/"probe")]).returncode == 0
print("PASS 00698: D3D9 Present crop/dirty source -> native inset + async GPU generation")
