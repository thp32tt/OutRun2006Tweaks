#!/usr/bin/env python3
"""00775: D3D9 alpha/depth-NEVER live game Draw/Indexed source continuity."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_game_fragment_reject.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
head, rest = bridge.split("bool proven_game_draw_no_target_writes(", 1)
helper = rest.split("void observe(IDirect3DDevice9* game,", 1)[0]
assert '#include "native_game_fragment_reject.hpp"' in head
for key in ("GameNativeFragmentReject::no_target_write(",
            "GameNativeMaskedDraw::no_visible_target_write_source_draw(",
            "D3DRS_ALPHATESTENABLE", "D3DRS_ALPHAFUNC", "D3DRS_ZFUNC",
            "D3DRS_STENCILENABLE", "D3DRS_COLORWRITEENABLE",
            "status != D3DERR_NOTFOUND",
            "targetIdentity.Get() != identity.Get()",
            "s.clearColor.matches("):
    assert key in helper, key
for entry in ("void observe(IDirect3DDevice9* game,",
              "void observe_unavailable_game_draw("):
    section = bridge.split(entry, 1)[1].split("\nvoid ", 1)[0]
    assert "if (fullMode && proven_game_draw_no_target_writes(game, s))" in section
    assert "s.frameBatch.absorb_empty_source_draw(" in section
assert "python tools/test_dx11_rejected_fragments_game_frame_00775.py" in workflow

probe = r'''
#include "native_game_fragment_reject.hpp"
#include "native_game_frame_batch.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool rejected(bool ae, unsigned af, bool ze, unsigned zf,
                        bool clear = true, bool target = true,
                        bool mrtFree = true, bool stencilFree = true,
                        bool full = true) {
    return GameNativeFragmentReject::no_target_write(
        full, clear, target, mrtFree, stencilFree, ae, af, ze, zf);
}
static_assert(rejected(true,1,false,8));
static_assert(rejected(false,8,true,1));
static_assert(rejected(true,1,true,1));
static_assert(!rejected(false,1,false,1));
static_assert(!rejected(true,8,true,8));
static_assert(!rejected(true,1,false,8,false));
static_assert(!rejected(true,1,false,8,true,false));
static_assert(!rejected(true,1,false,8,true,true,false));
static_assert(!rejected(true,1,false,8,true,true,true,false));
static_assert(!rejected(true,1,false,8,true,true,true,true,false));
constexpr bool frame() {
    GameNativeFrameBatch b{};
    if (!b.absorb_empty_source_draw(0,true) || !b.first_draw() ||
        b.publishable_full(true,1) || !b.accepts_full_on_source_target(1,true))
        return false;
    b.succeeded(false); b.record_source_draw(1); // real menu Draw
    if (!b.absorb_empty_source_draw(2,true) ||
        !b.accepts_full_on_source_target(3,true)) return false;
    b.succeeded(true); b.record_source_draw(3); // real race DrawIndexed
    return b.publishable_full(true,4) && !b.publishable_full(true,5) &&
        !b.absorb_empty_source_draw(5,true);
}
constexpr bool noRescue() {
    GameNativeFrameBatch a{},b{};
    if (a.absorb_empty_source_draw(0,false) || a.publishable_full(true,1))
        return false;
    b.succeeded(false); b.record_source_draw(0);
    return !b.absorb_empty_source_draw(2,true) &&
           !b.publishable_full(true,3);
}
static_assert(frame() && noRescue());
int main(){ assert(frame()); assert(noRescue()); }
'''
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "C++17 compiler missing"
with TemporaryDirectory(prefix="dx11-00775-") as tmp:
    work = Path(tmp)
    out = work / "probe"
    src = work / "probe.cpp"
    src.write_text(probe)
    cmd = [compiler,"-std=c++17","-O2","-Wall","-Wextra","-Werror",
           "-pedantic","-I"+str(root / "src/vr/d3d11"),
           str(src),"-o",str(out)]
    subprocess.run(cmd,check=True,capture_output=True)
    subprocess.run([str(out)],check=True,capture_output=True)
    # Compile the same real headers under mutation so a weakened NEVER
    # classifier cannot pass through an unchanged source-pattern test.
    variant = work / "native_game_fragment_reject.hpp"
    # The local override must be ahead of the actual repository include path.
    cmd.insert(7, "-I"+str(work))
    for field in ("alphaFunc == kNever", "depthFunc == kNever"):
        assert field in header
        variant.write_text(header.replace(field,field.replace(" == "," != ")))
        assert subprocess.run(cmd,capture_output=True).returncode != 0, field
print("PASS 00775: live rejected alpha/depth Draw/Indexed stream and fail-closed source fallback")
