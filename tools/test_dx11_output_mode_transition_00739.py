#!/usr/bin/env python3
"""00739: native menu/car/race full-frame output mode and upload provenance.

Source assertions, destructive mutations and portable C++ compile contracts.
Game/Quest3 runtime validation is deliberately NOT inferred from these checks.
"""
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
SIG = (ROOT / "src/vr/d3d11/native_game_readback_provenance.hpp").read_text(encoding="utf-8")
PUB = (ROOT / "src/vr/d3d11/native_game_frame_publication.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")


def connected(code: str) -> bool:
    draw = code[code.index("void observe(IDirect3DDevice9*"):code.index("void observe_scene_boundary(")]
    unavailable = code[code.index("void observe_unavailable_game_draw("):code.index("void observe_failed_game_draw(")]
    present = code[code.index("void before_game_present("):code.index("void before_game_reset()")]
    reset = code[code.index("void before_game_reset()"):]
    signature_pos = present.find("outputNow.nativeFullFrame = fullMode;")
    generation_pos = present.find("!s.previousOutput.same(outputNow)")
    mode_pos = present.find("GameNativeFramePublication::source_mode_contiguous(")
    complete_pos = present.find("currentFullFrameComplete =")
    return all((
        "bool sourceModeKnown = false;" in code,
        "bool sourceWasFullMode = false;" in code,
        "if (!observe_source_frame_mode(s, fullMode)) return;" in draw,
        "if (!observe_source_frame_mode(s, env_full_game_opt_in())) return;" in unavailable,
        "const bool fullMode = env_full_game_opt_in();" in present,
        "outputNow.nativeFullFrame = fullMode;" in present,
        0 <= signature_pos < generation_pos,
        "GameNativeFramePublication::source_mode_contiguous(" in present,
        0 <= mode_pos < complete_pos,
        mode_pos >= 0 and complete_pos > mode_pos and
        "s.frameBatch.abort();" in present[mode_pos:complete_pos],
        present.count("GameNativeFramePublication::matching_upload_extent(") == 2,
        "s.insetSurfaceWidth = surfaceWidth;" in present,
        "s.insetSurfaceHeight = surfaceHeight;" in present,
        "s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;" in present,
        "s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;" in reset,
        "s.sourceModeKnown = false;" in reset,
        "s.sourceModeKnown = false;" in present,
        "sourceModeKnown = false" in code[code.index("void observe_game_clear("):code.index("void observe_unavailable_game_draw(")],
        "python tools/test_dx11_output_mode_transition_00739.py" in WF,
    ))


assert connected(SRC), "native game Draw/Present/source-mode/resize fallback disconnected"
for bad, replacement in (
    ("outputNow.nativeFullFrame = fullMode;", "/* source mode omitted */"),
    ("if (!observe_source_frame_mode(s, fullMode)) return;", "/* mixed source mode */"),
    ("if (!observe_source_frame_mode(s, env_full_game_opt_in())) return;", "/* missing source mode */"),
    ("GameNativeFramePublication::source_mode_contiguous(", "GameNativeFramePublication::ignored_source_mode("),
    ("s.insetSurfaceWidth = surfaceWidth;", "/* width cache omitted */"),
    ("s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;", "/* stale upload dimensions */"),
):
    # Mutate the owned Present branch instead of an earlier pipeline-reset
    # occurrence of the same expression.
    if bad == "s.insetSurfaceWidth = s.insetSurfaceHeight = 0u;":
        offset = SRC.index("void before_game_present(")
        changed = SRC[:offset] + SRC[offset:].replace(bad, replacement, 1)
    else:
        changed = SRC.replace(bad, replacement, 1)
    assert changed != SRC and not connected(changed), bad

PROBE = r"""
#include "native_game_readback_provenance.hpp"
#include "native_game_frame_publication.hpp"
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool mode_and_extent_contract() {
    GameOutputSignature diag{0x11u, 3440u, 1440u, 21u, 0x123u};
    if (!diag.valid()) return false;
    auto full = diag;
    full.nativeFullFrame = true;
    if (diag.same(full) || !full.same(full)) return false;
    if (!GameNativeFramePublication::source_mode_contiguous(false, false, true) ||
        !GameNativeFramePublication::source_mode_contiguous(true, false, false) ||
        !GameNativeFramePublication::source_mode_contiguous(true, true, true) ||
        GameNativeFramePublication::source_mode_contiguous(true, false, true) ||
        GameNativeFramePublication::source_mode_contiguous(true, true, false)) return false;
    if (!GameNativeFramePublication::matching_upload_extent(256u, 144u, 256u, 144u) ||
        !GameNativeFramePublication::matching_upload_extent(3440u, 1440u, 3440u, 1440u) ||
        GameNativeFramePublication::matching_upload_extent(256u, 144u, 3440u, 1440u) ||
        GameNativeFramePublication::matching_upload_extent(3440u, 1440u, 256u, 144u) ||
        GameNativeFramePublication::matching_upload_extent(0u, 144u, 0u, 144u) ||
        GameNativeFramePublication::matching_upload_extent(3440u, 0u, 3440u, 0u)) return false;
    return true;
}
static_assert(mode_and_extent_contract(), "live Draw and Present mode/extent mismatch");
int main() { return mode_and_extent_contract() ? 0 : 1; }
"""
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "DX11 Fast Gate requires portable C++ compiler"
with TemporaryDirectory(prefix="dx11-00739-") as folder:
    folder = Path(folder)
    (folder / "probe.cpp").write_text(PROBE, encoding="utf-8")
    cases = (
        ("original", SIG, PUB, True),
        ("mode identity", SIG.replace("nativeFullFrame == other.nativeFullFrame",
                                      "nativeFullFrame != other.nativeFullFrame"), PUB, False),
        ("mode source", SIG, PUB.replace("sourceFullMode == presentFullMode",
                                       "sourceFullMode != presentFullMode"), False),
        ("extent width", SIG, PUB.replace("cachedWidth == outputWidth",
                                         "cachedWidth != outputWidth"), False),
        ("extent height", SIG, PUB.replace("cachedHeight == outputHeight",
                                          "cachedHeight != outputHeight"), False),
    )
    for name, sig, publication, should_pass in cases:
        assert should_pass or sig != SIG or publication != PUB, name
        (folder / "native_game_readback_provenance.hpp").write_text(sig, encoding="utf-8")
        (folder / "native_game_frame_publication.hpp").write_text(publication, encoding="utf-8")
        result = subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                                 "-Werror", "-pedantic", str(folder / "probe.cpp"),
                                 "-o", str(folder / "probe")],
                                capture_output=True, text=True)
        assert (result.returncode == 0) == should_pass, (name, result.stderr)
        if should_pass:
            assert subprocess.run([str(folder / "probe")], check=False).returncode == 0
print("PASS: 00739 native full-frame mode/extent ownership + destructive fallback")
