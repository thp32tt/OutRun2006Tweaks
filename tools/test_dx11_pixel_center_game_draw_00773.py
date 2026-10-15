#!/usr/bin/env python3
"""00773: Native game XYZRHW/WVP pixel centers for live Draw and DrawIndexed."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/live_game_pixel_center.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(s):
    if '#include "live_game_pixel_center.hpp"' not in s:
        return False
    block = s.split("bool translate_vertices(", 1)[1].split(
        "bool create_game_sampler(", 1)[0]
    correction = """if (!game_native_d3d9_raster_center(
                v.clip, static_cast<float>(vp.Width),
                static_cast<float>(vp.Height))) return false;"""
    return (correction in block and
            block.index("if (layout.pretransformed)") <
            block.index("game_native_world_depth_clip(") <
            block.index(correction) <
            block.index("v.diffuse[0] =") and
            "translate_vertices(bytes, vertexCount, stride, vp," in s and
            "ctx->DrawIndexed(indexCount, 0, 0);" in s and
            "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in s and
            "python tools/test_dx11_pixel_center_game_draw_00773.py" in workflow)

assert integrated(source), "shared real game Draw/Indexed XYZRHW + WVP path disconnected"
for token in ('#include "live_game_pixel_center.hpp"',
              "game_native_d3d9_raster_center(", "static_cast<float>(vp.Width)",
              "static_cast<float>(vp.Height)"):
    mutated = source.replace(token, "/* stripped for negative regression */", 1)
    assert mutated != source and not integrated(mutated), token

probe = r"""
#include "live_game_pixel_center.hpp"
#include <cassert>
#include <cmath>
#include <limits>
using outrun::vr::dx11::live_game_frame::game_native_d3d9_raster_center;
int main() {
    float menu[4] = {0.f, 0.f, .5f, 1.f};
    assert(game_native_d3d9_raster_center(menu, 100.f, 50.f));
    assert(std::fabs(menu[0]-.01f)<.000001f && std::fabs(menu[1]+.02f)<.000001f);
    assert(menu[2]==.5f && menu[3]==1.f);
    float world[4] = {0.f, 0.f, .3f, 2.f};
    assert(game_native_d3d9_raster_center(world, 100.f, 50.f));
    assert(std::fabs(world[0]/world[3]-.01f)<.000001f);
    assert(std::fabs(world[1]/world[3]+.02f)<.000001f);
    float behind[4] = {0.f, 0.f, .2f, -2.f};
    assert(game_native_d3d9_raster_center(behind, 100.f, 50.f));
    assert(std::fabs(behind[0]/behind[3]-.01f)<.000001f);
    assert(std::fabs(behind[1]/behind[3]+.02f)<.000001f);
    float camera[4] = {1.f, 2.f, .2f, 0.f};
    assert(game_native_d3d9_raster_center(camera, 100.f, 50.f));
    assert(camera[0]==1.f && camera[1]==2.f);
    float bad[4] = {1.f, 2.f, 0.f, 1.f};
    assert(!game_native_d3d9_raster_center(bad, 0.f, 50.f));
    assert(!game_native_d3d9_raster_center(bad, 100.f, -1.f));
    assert(bad[0]==1.f && bad[1]==2.f);
    bad[0]=std::numeric_limits<float>::infinity();
    assert(!game_native_d3d9_raster_center(bad, 100.f, 50.f));
    float overflow[4]={3.e38f, 0.f, 0.f, 3.e38f};
    assert(!game_native_d3d9_raster_center(overflow, .01f, 50.f));
    assert(overflow[0]==3.e38f);
}
"""
cc = shutil.which("g++") or shutil.which("clang++")
assert cc, "C++17 compiler required for native vertex regression"
with TemporaryDirectory(prefix="dx11-00773-") as d:
    tmp = Path(d)
    (tmp/"probe.cpp").write_text(probe)
    def passes(h):
        (tmp/"live_game_pixel_center.hpp").write_text(h)
        compile_result = subprocess.run(
            [cc,"-std=c++17","-O2","-Wall","-Wextra","-Werror","-pedantic",
             str(tmp/"probe.cpp"),"-o",str(tmp/"probe")],capture_output=True,text=True
        )
        return compile_result.returncode == 0 and subprocess.run(
            [str(tmp/"probe")],capture_output=True).returncode == 0
    assert passes(header), "native pixel parity positive/negative C++ proof failed"
    for before, after in (
        ("clip[3] / viewportWidth","0.0f"),
        ("clip[3] / viewportHeight","0.0f"),
        ("clip[1] - clip[3] / viewportHeight","clip[1] + clip[3] / viewportHeight"),
        ("viewportWidth <= 0.0f","viewportWidth < 0.0f"),
        ("!std::isfinite(x) || !std::isfinite(y)","false"),
    ):
        assert before in header and not passes(header.replace(before,after,1)), before
print("00773 PASS: D3D9 menu/world real native Draw/Indexed half-pixel + fallback")
