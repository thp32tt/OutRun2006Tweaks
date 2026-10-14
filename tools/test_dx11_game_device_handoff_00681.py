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
    normal_present = present[:present.index("} catch (...)")]
    reset = code[code.index("void before_game_reset("):]
    # Only device selection is required to remain side-effect-free. A
    # separate, later source-mode guard may legitimately abort a mixed
    # native scene without touching the original game Draw or input.
    foreign_observer = code[code.index("bool observe_source_device("):code.index("bool observe_source_frame_mode(")]
    owner_gate = "if (GameNativeFrameBatch::foreign_present("
    return (
        "GameNativeFrameBatch::admits_game_source(" in foreign_observer and
        "s.previousOutput.valid()" in foreign_observer and
        "s.previousOutput.device : 0u" in foreign_observer and
        "return false;" in foreign_observer and
        "s.frameBatch.abort();" not in foreign_observer and
        "s.pending = false;" not in foreign_observer and
        "if (!observe_source_device(s, game)) return;" in observer and
        "if (!observe_source_device(s, game)) return;" in unavailable and
        owner_gate in present and
        present.index(owner_gate) < present.index("game->GetBackBuffer(") and
        "s.previousOutput.valid() ? s.previousOutput.device : 0u" in present and
        "presentDevice)) return;" in present and
        # Reject mutations before the foreign Present guard has returned,
        # not deliberate frame-mode rollback after owning-device validation.
        "s.frameBatch.abort();" not in present[:present.index("game->GetBackBuffer(")] and
        "s.pending = false;" in present and
        "oldest.provenance.same_device(presentDevice)" in present and
        "next.provenance.sourceDevice = presentDevice;" in present and
        present.index("next.provenance.sourceDevice = presentDevice;") < present.index("ctx->End(next.fence.Get());") and
        "s.sourceGameDevice = 0u;" in normal_present and
        "s.sourceGameDevice = 0u;" in present[present.index("} catch (...)"):] and
        "s.sourceGameDevice = 0u;" in reset
    )
assert connected(cpp), "real game device/Draw/native GPU/Present path disconnected"
for label,needle in (
    ("foreign-draw", "if (!observe_source_device(s, game)) return;"),
    ("mismatched-present", "if (GameNativeFrameBatch::foreign_present("),
    ("foreign-gpu-frame", "oldest.provenance.same_device(presentDevice)"),
    ("unowned-fence", "next.provenance.sourceDevice = presentDevice;"),
    ("reset", "s.sourceGameDevice = 0u;"),
):
    mutation = cpp.replace(needle, "/* adversarial missing device link */", 1)
    assert mutation != cpp and not connected(mutation), label

# Compile the same device-selection helper bound into the live renderer, with
# negative mutations that restore foreign-Present acceptance.
frame_header = (root / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
assert "static constexpr bool foreign_present(" in frame_header
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
probe = r"""
#include "native_game_readback_provenance.hpp"
#include "native_game_frame_batch.hpp"
using outrun::vr::dx11::live_game_frame::GameReadbackProvenance;
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
static_assert(!GameNativeFrameBatch::foreign_present(0xA0, 0, 0xA0));
static_assert(GameNativeFrameBatch::foreign_present(0xA0, 0, 0xB0));
static_assert(!GameNativeFrameBatch::foreign_present(0xA0, 0xB0, 0xA0));
static_assert(GameNativeFrameBatch::foreign_present(0xA0, 0xA0, 0xB0));
static_assert(!GameNativeFrameBatch::foreign_present(0, 0xA0, 0xA0));
static_assert(GameNativeFrameBatch::foreign_present(0, 0xA0, 0xB0));
static_assert(!GameNativeFrameBatch::foreign_present(0, 0, 0xB0));
static_assert(GameNativeFrameBatch::foreign_present(0, 0, 0));
static_assert(GameReadbackProvenance{20,4,0xA0}.may_overlay(21));
static_assert(GameReadbackProvenance{20,4,0xA0}.same_device(0xA0));
static_assert(!GameReadbackProvenance{20,4,0xA0}.same_device(0xB0));
static_assert(!GameReadbackProvenance{20,4,0xA0}.same_device(0));
static_assert(!GameReadbackProvenance{20,4,0}.same_device(0xA0));
static_assert(!GameReadbackProvenance{20,4,0}.same_device(0));
static_assert(!GameReadbackProvenance{20,4,0xA0}.may_overlay(23));
static_assert(!GameReadbackProvenance{20,0,0xA0}.may_overlay(21));
int main() { return 0; }
"""
with TemporaryDirectory(prefix="dx11-game-device-") as tmp:
    d = Path(tmp)
    (d / "p.cpp").write_text(probe)
    (d / "native_game_frame_batch.hpp").write_text(frame_header)
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
    (d / "native_game_readback_provenance.hpp").write_text(header)
    for label, bad in (
        ("foreign-source-accepted", frame_header.replace(
            "sourceDevice != presentingDevice", "sourceDevice == presentingDevice")),
        ("foreign-output-accepted", frame_header.replace(
            "lastOutputDevice != presentingDevice", "lastOutputDevice == presentingDevice")),
    ):
        assert bad != frame_header, label
        (d / "native_game_frame_batch.hpp").write_text(bad)
        outcome = subprocess.run(cmd, capture_output=True, text=True)
        assert outcome.returncode != 0, (label, outcome.stderr)
print("PASS: live game source/Present ownership, retained async readback, foreign draw isolation, 4 C++ mutants")
