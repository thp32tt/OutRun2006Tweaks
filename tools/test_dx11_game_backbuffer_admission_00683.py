#!/usr/bin/env python3
"""00683: native live game Draw must come from same Present backbuffer."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
root = Path(__file__).resolve().parents[1]
src = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr = (root/"src/vr/d3d11/native_game_backbuffer_admission.hpp").read_text()
def connected(code):
    helper = code[code.index("bool game_native_backbuffer_ready("):code.index("bool supported_game_state(")]
    draw = code[code.index("bool supported_game_state("):code.index("bool translate_vertices(")]
    present = code[code.index("void before_game_present("):code.index("void before_game_reset(")]
    return all(p in helper for p in (
        "game->GetRenderTarget(0,", "game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,",
        "target.As(&targetIdentity)", "backbuffer.As(&backbufferIdentity)",
        "targetDesc.Format == bbDesc.Format", "bbDesc.MultiSampleType == D3DMULTISAMPLE_NONE",
        "admission.accepts(kWidth, kHeight, 8u)")) and all(p in draw for p in (
        "if (!game_native_backbuffer_ready(game, viewport)) return false;",
        "return true;")) and all(p in src for p in (
        "if (!supported_game_state(game, type, vp, layout, transforms, capture, output))",
        "ctx->DrawIndexed(indexCount, 0, 0);", "ctx->Draw(static_cast<UINT>(vertices.size()), 0);")) and (
        "s.frameBatch.publishable(s.pending) && outputWritable" in present and
        "game->UpdateSurface(" in present and "s.sourceGameDevice == presentDevice" in present)
assert connected(src), "Draw to native GPU to actual Present bridge disconnected"
for token in (
    "game->GetRenderTarget(0,", "game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,",
    "target.As(&targetIdentity)", "backbuffer.As(&backbufferIdentity)",
    "targetDesc.Format == bbDesc.Format", "bbDesc.MultiSampleType == D3DMULTISAMPLE_NONE",
    "admission.accepts(kWidth, kHeight, 8u)",
    "if (!game_native_backbuffer_ready(game, viewport)) return false;"):
    mutated = src.replace(token,"/* regression */",1)
    assert mutated != src and not connected(mutated), token
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
probe = r'''
#include "native_game_backbuffer_admission.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameNativeBackbufferAdmission full{0x10,0x10,3440,1440,3440,1440,400,200,1600,900,true,true,true};
constexpr GameNativeBackbufferAdmission letterbox{0x10,0x10,1920,1080,1920,1080,240,0,1440,1080,true,true,true};
static_assert(full.accepts(256,144,8));
static_assert(letterbox.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0x10,0x20,3440,1440,3440,1440,400,200,1600,900,true,true,true}.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0x10,0x10,1024,1024,3440,1440,400,200,1600,900,true,true,true}.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0x10,0x10,3440,1440,3440,1440,400,200,1600,900,false,true,true}.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0x10,0x10,3440,1440,3440,1440,400,200,1600,900,true,true,false}.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0x10,0x10,3440,1440,3440,1440,3430,0,20,200,true,true,true}.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0x10,0x10,256,144,256,144,0,0,256,144,true,true,true}.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0x10,0x10,3440,1440,3440,1440,400,200,1600,900,true,false,true}.accepts(256,144,8));
static_assert(!GameNativeBackbufferAdmission{0,0,3440,1440,3440,1440,400,200,1600,900,true,true,true}.accepts(256,144,8));
int main() { return 0; }
'''
with TemporaryDirectory(prefix="dx11-00683-") as tmp:
    p=Path(tmp)
    (p/"probe.cpp").write_text(probe)
    cmd=[compiler,"-std=c++17","-O2","-Wall","-Wextra","-Werror","-pedantic",
        str(p/"probe.cpp"),"-o",str(p/"probe")]
    cases=(("valid",hdr,True),
        ("auxiliary RT",hdr.replace("targetIdentity == backbufferIdentity","targetIdentity != backbufferIdentity"),False),
        ("target size",hdr.replace("targetWidth == backbufferWidth","targetWidth != backbufferWidth"),False),
        ("format",hdr.replace("formatMatches && ",""),False),
        ("MSAA",hdr.replace("supportedBackbufferFormat && singleSample &&", "supportedBackbufferFormat &&"),False),
        ("viewport",hdr.replace("viewportWidth <= backbufferWidth - viewportX","viewportWidth > backbufferWidth - viewportX"),False),
        ("present inset",hdr.replace("insetHeight <= backbufferHeight - margin","insetHeight > backbufferHeight - margin"),False))
    for label,body,expected in cases:
        assert label=="valid" or body!=hdr,label
        (p/"native_game_backbuffer_admission.hpp").write_text(body)
        done=subprocess.run(cmd,cwd=p,capture_output=True,text=True)
        assert (done.returncode==0)==expected,(label,done.stderr)
        if expected: assert subprocess.run([str(p/"probe")],cwd=p).returncode==0
print("PASS: real Draw-native GPU-Present backbuffer, 8 source + 6 C++ destructive regressions")
