#!/usr/bin/env python3
"""Native game frame source -> fenced GPU copy -> nonblocking D3D9 Present tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
src = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root/"src/vr/d3d11/native_game_readback_provenance.hpp").read_text()
def wired(code):
    a = code.index("void before_game_present(")
    b = code.index("void before_game_reset(")
    x = code[a:b]
    return (code.count('#include "native_game_readback_provenance.hpp"') == 1
        and "GameReadbackProvenance provenance{};" in code
        and "ready == S_OK && (!oldest.provenance.may_present(s.presents, fullMode) ||" in x
        and "!oldest.provenance.same_device(presentDevice)" in x
        and "++s.staleReadbacks;" in x
        and "next.provenance = {s.presents, s.sourceDrawsThisFrame};" in x
        and "ctx->CopyResource(next.staging.Get(), s.backend.color_texture());" in x
        and "D3D11_ASYNC_GETDATA_DONOTFLUSH" in x
        and "fullMode ? fullSlot : s.readSlot" in x
        and "fullMode ? capturedAtPresent == currentPresent" in header
        and "D3D11_MAP_FLAG_DO_NOT_WAIT" in x
        and "game->UpdateSurface(" in x
        and x.index("!oldest.provenance.may_present(s.presents, fullMode)") < x.index("ctx->Map(oldest.staging.Get()")
        and x.index("next.provenance = {s.presents, s.sourceDrawsThisFrame};") < x.index("ctx->End(next.fence.Get());")
        and "item.provenance = {};" in code[b:])
assert wired(src)
for token in ("!oldest.provenance.may_present(s.presents, fullMode)",
              "next.provenance = {s.presents, s.sourceDrawsThisFrame};",
              "++s.staleReadbacks;", "item.provenance = {};"):
    mutant = src.replace(token, "/* removed game GPU scene link */", 1)
    assert mutant != src and not wired(mutant), token

cxx = shutil.which("g++") or shutil.which("clang++")
assert cxx
probe = """
#include "native_game_readback_provenance.hpp"
using outrun::vr::dx11::live_game_frame::GameReadbackProvenance;
static_assert(GameReadbackProvenance{20u, 1u}.may_overlay(21u));
static_assert(GameReadbackProvenance{20u, 8u}.may_overlay(22u));
static_assert(!GameReadbackProvenance{20u, 8u}.may_overlay(23u));
static_assert(!GameReadbackProvenance{20u, 0u}.may_overlay(21u));
static_assert(!GameReadbackProvenance{20u, 5u}.may_overlay(20u));
static_assert(!GameReadbackProvenance{20u, 5u}.may_overlay(19u));
static_assert(!GameReadbackProvenance{~0ull, 1u}.may_overlay(0u));
int main(){return 0;}
"""
with TemporaryDirectory(prefix="game-dx11-readback-") as tmp:
    d = Path(tmp)
    (d/"p.cpp").write_text(probe)
    cmd = [cxx,"-std=c++17","-O2","-Wall","-Wextra","-Werror","-pedantic",str(d/"p.cpp"),"-o",str(d/"p")]
    for name,data,positive in (
        ("exact",header,True),
        ("late",header.replace("kMaxPresentLag = 2u","kMaxPresentLag = 999u"),False),
        ("unowned",header.replace("return sourceDraws != 0u && currentPresent > capturedAtPresent",
                                   "return sourceDraws >= 0u && currentPresent > capturedAtPresent"),False),
        ("same-frame",header.replace("currentPresent > capturedAtPresent","currentPresent >= capturedAtPresent"),False)):
        (d/"native_game_readback_provenance.hpp").write_text(data)
        result=subprocess.run(cmd,capture_output=True,text=True)
        if positive:
            assert result.returncode == 0, result.stderr
            assert subprocess.run([str(d/"p")]).returncode == 0
        else: assert result.returncode != 0, name
print("PASS: real Draw GPU ring->fresh game Present, four bridge + three C++ destructive regressions")
