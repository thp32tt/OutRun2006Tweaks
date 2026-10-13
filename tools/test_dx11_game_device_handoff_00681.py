#!/usr/bin/env python3
"""Menu/car/race real Draw -> D3D11 GPU fence -> same D3D9 Present device."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_game_readback_provenance.hpp").read_text()
def connected(code):
    observer = code[code.index("void observe(IDirect3DDevice9*"):code.index("void observe_linear(")]
    unavailable = code[code.index("void observe_unavailable_game_draw("):code.index("void before_game_present(")]
    present = code[code.index("void before_game_present("):code.index("void before_game_reset(")]
    reset = code[code.index("void before_game_reset("):]
    return (
        "s.sourceGameDevice != current" in code and
        "s.frameBatch.abort();" in code[code.index("bool observe_source_device("):code.index("void observe(IDirect3DDevice9*")] and
        "if (!observe_source_device(s, game)) return;" in observer and
        "if (!observe_source_device(s, game)) return;" in unavailable and
        "s.sourceGameDevice != presentDevice" in present and
        "s.frameBatch.abort();" in present and
        "s.pending = false;" in present and
        "oldest.provenance.same_device(presentDevice)" in present and
        "next.provenance.sourceDevice = presentDevice;" in present and
        present.index("next.provenance.sourceDevice = presentDevice;") < present.index("ctx->End(next.fence.Get());") and
        "s.sourceGameDevice = 0u;" in present and
        "s.sourceGameDevice = 0u;" in reset
    )
assert connected(cpp), "real game device/Draw/native GPU/Present path disconnected"
for label,needle in (
    ("foreign-draw", "if (!observe_source_device(s, game)) return;"),
    ("mismatched-present", "s.sourceGameDevice != presentDevice"),
    ("foreign-gpu-frame", "oldest.provenance.same_device(presentDevice)"),
    ("unowned-fence", "next.provenance.sourceDevice = presentDevice;"),
    ("reset", "s.sourceGameDevice = 0u;"),
):
    mutation = cpp.replace(needle, "/* adversarial missing device link */", 1)
    assert mutation != cpp and not connected(mutation), label

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
probe = r"""
#include "native_game_readback_provenance.hpp"
using outrun::vr::dx11::live_game_frame::GameReadbackProvenance;
static_assert(GameReadbackProvenance{20,4,0xA0}.may_overlay(21));
static_assert(GameReadbackProvenance{20,4,0xA0}.same_device(0xA0));
static_assert(!GameReadbackProvenance{20,4,0xA0}.same_device(0xB0));
static_assert(!GameReadbackProvenance{20,4,0xA0}.same_device(0));
static_assert(!GameReadbackProvenance{20,4,0}.same_device(0xA0));
static_assert(!GameReadbackProvenance{20,4,0xA0}.may_overlay(23));
static_assert(!GameReadbackProvenance{20,0,0xA0}.may_overlay(21));
int main() { return 0; }
"""
with TemporaryDirectory(prefix="dx11-game-device-") as tmp:
    d = Path(tmp)
    (d / "p.cpp").write_text(probe)
    cmd = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
           "-pedantic", str(d / "p.cpp"), "-o", str(d / "p")]
    for label,body,ok in (
        ("same-device", header, True),
        ("foreign-pass", header.replace("presentDevice == sourceDevice", "presentDevice != sourceDevice"), False),
        ("null-pass", header.replace("sourceDevice != 0u && ", ""), False),
    ):
        (d / "native_game_readback_provenance.hpp").write_text(body)
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert (result.returncode == 0) == ok, (label, result.stderr)
        if ok: assert subprocess.run([str(d / "p")]).returncode == 0
print("PASS: game-device-owned native Draw/DrawIndexed, GPU fence, Present; five bridge + two C++ destructive regressions")
