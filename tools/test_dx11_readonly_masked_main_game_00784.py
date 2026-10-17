#!/usr/bin/env python3
"""00784: real main-target masked MRT/read-only stencil source continuity."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
offscreen = (root / "src/vr/d3d11/native_game_offscreen_pass.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
helper = bridge.split("bool proven_game_draw_no_target_writes(", 1)[1].split(
    "void observe(IDirect3DDevice9* game,", 1)[0]
draw = bridge.split("void observe(IDirect3DDevice9* game,", 1)[1].split(
    "} // namespace", 1)[0]
unavailable = bridge.split("void observe_unavailable_game_draw(", 1)[1].split(
    "void observe_failed_game_draw(", 1)[0]
def linked(h, source=draw, miss=unavailable):
    return all(token in h for token in (
        "GetDeviceCaps(&caps)", "valid_mrt_count(caps.NumSimultaneousRTs)",
        "GetRenderTarget(i, extra.GetAddressOf())",
        "if (status == D3DERR_NOTFOUND) continue;",
        "GetRenderState(kExtraColorMasks[i - 1u], &extraMask)",
        "inactive_extra_mrt(true, extraMask)",
        "GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)",
        "const bool stencilReadOnly = game_stencil_is_read_only(",
        "stencilEnabled, stencilMaskKnown, stencilWriteMask",
        "if (!stencilReadOnly) return false;",
        "stencilWrites, false", "!stencilWrites, alphaTest == TRUE",
        "s.clearColor.matches(", "targetIdentity.Get() != identity.Get()",
    )) and all(token in source for token in (
        "if (fullMode && proven_game_draw_no_target_writes(game, s))",
        "s.frameBatch.absorb_empty_source_draw(",
        "s.frameBatch.abort();",
    )) and all(token in miss for token in (
        "if (fullMode && proven_game_draw_no_target_writes(game, s))",
        "s.frameBatch.absorb_empty_source_draw(",
    ))
assert linked(helper), "read-only stencil/inactive MRT not connected to real Draw/DrawIndexed"
for old, new in (
    ("inactive_extra_mrt(true, extraMask)", "true /* ignored live MRT */"),
    ("if (!stencilReadOnly) return false;", "if (false) return false;"),
    ("!stencilWrites, alphaTest == TRUE", "true, alphaTest == TRUE"),
    ("s.clearColor.matches(", "unconditional_clear("),
):
    altered = helper.replace(old, new, 1)
    assert altered != helper and not linked(altered), old
# The shared D3D9 helper must inspect both stencil faces before the main
# and offscreen callers may consume the original no-output Draw ordinal.
stencil = bridge.split("// Read a real D3D9 stencil state,", 1)[1].split(
    "// Preserve the complete game Draw/DrawIndexed source stream", 1)[0]
def linked_stencil(s):
    return all(token in s for token in (
        "GetRenderState(D3DRS_STENCILFAIL, &frontFail)",
        "GetRenderState(D3DRS_STENCILZFAIL, &frontZFail)",
        "GetRenderState(D3DRS_STENCILPASS, &frontPass)",
        "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)",
        "GetRenderState(D3DRS_CCW_STENCILFAIL, &backFail)",
        "GetRenderState(D3DRS_CCW_STENCILZFAIL, &backZFail)",
        "GetRenderState(D3DRS_CCW_STENCILPASS, &backPass)",
        "GameNativeOffscreenPass::all_stencil_ops_keep(",
    ))
assert linked_stencil(stencil), "both D3D9 stencil faces must be inspected"
for old, new in (
    ("D3DRS_CCW_STENCILFAIL, &backFail", "D3DRS_STENCILFAIL, &backFail"),
    ("D3DRS_CCW_STENCILZFAIL, &backZFail", "D3DRS_STENCILZFAIL, &backZFail"),
    ("D3DRS_CCW_STENCILPASS, &backPass", "D3DRS_STENCILPASS, &backPass"),
    ("GameNativeOffscreenPass::all_stencil_ops_keep(",
     "unconditional_read_only_stencil("),
):
    altered = stencil.replace(old, new, 1)
    assert altered != stencil and not linked_stencil(altered), old
assert "python tools/test_dx11_readonly_masked_main_game_00784.py" in workflow
cxx = shutil.which("g++") or shutil.which("clang++")
assert cxx, "C++17 compiler required"
with TemporaryDirectory(prefix="dx11-masked-main-") as tmp:
    base = Path(tmp)
    (base / "src/vr/d3d11").mkdir(parents=True)
    (base / "tools").mkdir()
    for name in ("native_game_masked_draw.hpp", "native_game_offscreen_pass.hpp",
                 "native_game_fragment_reject.hpp", "native_game_frame_batch.hpp"):
        shutil.copyfile(root / "src/vr/d3d11" / name,
                        base / "src/vr/d3d11" / name)
    source = root / "tools/dx11_readonly_masked_main_game_00784.cpp"
    shutil.copyfile(source, base / "tools" / source.name)
    exe = base / "readonly_main_game"
    cmd = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
           "-pedantic", str(base / "tools" / source.name), "-o", str(exe)]
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run([str(exe)], check=True, capture_output=True)
    hdr = base / "src/vr/d3d11/native_game_offscreen_pass.hpp"
    hdr.write_text(offscreen.replace("maskKnown && writeMask == 0u",
                                     "maskKnown /* ignores writable stencil */"),
                   encoding="utf-8")
    assert subprocess.run(cmd, capture_output=True).returncode != 0, (
        "writable-stencil mutant must fail C++ negative fallback proof")
print("00784 native menu/car/race masked MRT + read-only stencil continuation PASS")
