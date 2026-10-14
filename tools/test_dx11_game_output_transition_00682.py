#!/usr/bin/env python3
"""00682: output-generation GPU readback and device-owned D3D9 upload."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import shutil

root = Path(__file__).resolve().parents[1]
src = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr = (root/"src/vr/d3d11/native_game_readback_provenance.hpp").read_text()
def connected(code):
    present = code[code.index("void before_game_present("):code.index("void before_game_reset(")]
    reset = code[code.index("void before_game_reset("):]
    return (
        "GameOutputSignature previousOutput{};" in code
        and "!s.previousOutput.same(outputNow)" in present
        and "s.insetSurfaceDevice != presentDevice" in present
        and "s.insetSurfaceDevice == presentDevice" in present
        and "s.insetSurfaceDevice = presentDevice;" in present
        and "!oldest.provenance.same_output(s.outputGeneration)" in present
        and "s.sourceGameDevice != presentDevice" in present
        and present.count("next.provenance.outputGeneration = s.outputGeneration;") == 2
        and present.index("next.provenance.outputGeneration = s.outputGeneration;")
            < present.index("ctx->End(next.fence.Get());")
        and "const bool complete = fullMode" in present
        and "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in present
        and ": s.frameBatch.publishable(s.pending);" in present
        and present.count("if (complete && outputWritable &&") == 2
        and "game->CreateOffscreenPlainSurface(" in present
        and "game->UpdateSurface(" in present
        and "s.outputGeneration = 0u;" in reset
        and "s.insetSurfaceDevice = 0u;" in reset
        and "item.provenance = {};" in reset)
assert connected(src), "live D3D9 output-to-native-GPU handoff disconnected"
for label, token in (
    ("stale GPU generation", "!oldest.provenance.same_output(s.outputGeneration)"),
    ("lost GPU stamp", "next.provenance.outputGeneration = s.outputGeneration;"),
    ("foreign D3D9 surface", "s.insetSurfaceDevice != presentDevice"),
    ("unsafe D3D9 UpdateSurface", "s.insetSurfaceDevice == presentDevice"),
    ("unsupported output", "if (complete && outputWritable &&"),
    ("incomplete full game", "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)"),
):
    mutated = src.replace(token, "/* missing output ownership */", 1)
    assert mutated != src and not connected(mutated), label
start = src.index("void before_game_reset(")
mutated = src[:start] + src[start:].replace(
    "    s.insetSurfaceDevice = 0u;",
    "    /* missing output owner reset */", 1)
assert mutated != src and not connected(mutated), "device cache reset"

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler
probe = r"""
#include "native_game_readback_provenance.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameOutputSignature output{0x10u,3440u,1440u,21u,0xabcdu};
static_assert(output.valid());
static_assert(output.same(GameOutputSignature{0x10u,3440u,1440u,21u,0xabcdu}));
static_assert(!output.same(GameOutputSignature{0x20u,3440u,1440u,21u,0xabcdu}));
static_assert(!output.same(GameOutputSignature{0x10u,1920u,1440u,21u,0xabcdu}));
static_assert(!output.same(GameOutputSignature{0x10u,3440u,1080u,21u,0xabcdu}));
static_assert(!output.same(GameOutputSignature{0x10u,3440u,1440u,22u,0xabcdu}));
static_assert(!output.same(GameOutputSignature{}));
static_assert(!GameOutputSignature{}.valid());
static_assert(!GameOutputSignature{0x10u,3440u,1440u,21u,0u}.valid());
static_assert(!output.same(GameOutputSignature{0x10u,3440u,1440u,21u,0xbeefu}));
static_assert(!GameOutputSignature{0x10u,3440u,1440u,0u,0xabcdu}.valid());
static_assert(GameReadbackProvenance{20u,4u,0x10u,2u}.same_output(2u));
static_assert(!GameReadbackProvenance{20u,4u,0x10u,2u}.same_output(3u));
static_assert(!GameReadbackProvenance{20u,4u,0x10u,0u}.same_output(0u));
static_assert(!GameReadbackProvenance{20u,4u,0x10u,0u}.same_output(1u));
static_assert(GameReadbackProvenance{20u,4u,0x10u,2u}.same_device(0x10u));
int main() { return 0; }
"""
with TemporaryDirectory(prefix="dx11-00682-") as temporary:
    d = Path(temporary)
    (d/"probe.cpp").write_text(probe)
    cmd = [compiler,"-std=c++17","-O2","-Wall","-Wextra","-Werror",
           "-pedantic",str(d/"probe.cpp"),"-o",str(d/"probe")]
    cases = (
        ("valid", hdr, True),
        ("generation-reversed", hdr.replace(
            "outputGeneration == currentGeneration",
            "outputGeneration != currentGeneration"), False),
        ("generation-zero", hdr.replace(
            "outputGeneration != 0u && ", ""), False),
        ("foreign-device", hdr.replace(
            "device == other.device", "device != other.device"), False),
        ("width-change", hdr.replace(
            "width == other.width", "width != other.width"), False),
        ("format-unknown", hdr.replace(
            "format != 0u", "format == 0u"), False),
    )
    for label, text, expected in cases:
        assert label == "valid" or text != hdr, label
        (d/"native_game_readback_provenance.hpp").write_text(text)
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert (result.returncode == 0) == expected, (label, result.stderr)
        if expected: assert subprocess.run([str(d/"probe")]).returncode == 0
print("PASS: output generation, D3D9 upload ownership, 6 bridge + 5 C++ mutations")
