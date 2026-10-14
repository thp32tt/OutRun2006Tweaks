#!/usr/bin/env python3
"""00684: menu/car/race same-resolution Present backbuffer replacement invalidates stale native GPU uploads."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
hdr = (root/"src/vr/d3d11/native_game_readback_provenance.hpp").read_text()
src = (root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
present = src[src.index("void before_game_present("):src.index("void before_game_reset(")]
required = (
    "ComPtr<IUnknown> presentBackbufferIdentity;",
    "presentBackbuffer.As(&presentBackbufferIdentity)",
    "reinterpret_cast<std::uintptr_t>(",
    "presentBackbufferIdentity.Get()",
    "!s.previousOutput.same(outputNow)",
    "++s.outputGeneration",
    "s.insetSurface.Reset();",
    "!oldest.provenance.same_output(s.outputGeneration)",
    "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)",
    ": s.frameBatch.publishable(s.pending);",
    "if (complete && outputWritable &&",
    "game->UpdateSurface(",
)
assert all(token in present for token in required), "source Present/COM identity-to-GPU readback-to-D3D9 upload incomplete"
# A lost source identity must be an actual failing connection test.
for removed in ("presentBackbuffer.As(&presentBackbufferIdentity)",
                "presentBackbufferIdentity.Get()",
                "!s.previousOutput.same(outputNow)",
                "!oldest.provenance.same_output(s.outputGeneration)",
                "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)"):
    assert removed in present
    assert not all(token in present.replace(removed, "/* removed */", 1)
                   for token in required), removed

compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
probe = r"""
#include "native_game_readback_provenance.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr GameOutputSignature menu{0x10u,1920u,1080u,21u,0x100u};
constexpr GameOutputSignature vehicle{0x10u,1920u,1080u,21u,0x200u};
constexpr GameOutputSignature race{0x10u,1920u,1080u,21u,0x300u};
static_assert(menu.valid() && vehicle.valid() && race.valid());
static_assert(menu.same(GameOutputSignature{0x10u,1920u,1080u,21u,0x100u}));
static_assert(!menu.same(vehicle) && !vehicle.same(race) && !menu.same(race));
static_assert(!menu.same(GameOutputSignature{0x20u,1920u,1080u,21u,0x100u}));
static_assert(!menu.same(GameOutputSignature{0x10u,1280u,720u,21u,0x100u}));
static_assert(!GameOutputSignature{0x10u,1920u,1080u,21u,0u}.valid());
static_assert(!GameOutputSignature{}.valid());
static_assert(GameReadbackProvenance{40u,4u,0x10u,7u}.same_output(7u));
static_assert(!GameReadbackProvenance{40u,4u,0x10u,7u}.same_output(8u));
int main() { return 0; }
"""
with TemporaryDirectory(prefix="dx11-00684-") as td:
    p = Path(td)
    (p/"probe.cpp").write_text(probe)
    command = [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
               str(p/"probe.cpp"), "-o", str(p/"probe")]
    cases = [
        ("valid", hdr, True),
        ("COM identity comparison removed",
         hdr.replace("backbufferIdentity == other.backbufferIdentity", "true"), False),
        ("COM identity mandatory removed",
         hdr.replace("backbufferIdentity != 0u;", "true;"), False),
        ("same identity accidentally rejected",
         hdr.replace("backbufferIdentity == other.backbufferIdentity",
                     "backbufferIdentity != other.backbufferIdentity"), False),
    ]
    for name, modified, expected in cases:
        assert name == "valid" or modified != hdr, name
        (p/"native_game_readback_provenance.hpp").write_text(modified)
        outcome = subprocess.run(command, text=True, capture_output=True)
        assert (outcome.returncode == 0) == expected, (name, outcome.stderr)
        if expected:
            assert subprocess.run([str(p/"probe")], capture_output=True).returncode == 0
print("PASS: live backbuffer COM capture, same-mode menu/car/race generation, 4 source + 3 C++ negative cases")
