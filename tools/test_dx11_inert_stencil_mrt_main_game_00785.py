#!/usr/bin/env python3
"""00785: live pixel-writing RT0 native Draw with inert stencil/MRT + main Z owner."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
admission = bridge.split("bool supported_game_state(", 1)[1].split(
    "GameNativeCullAdmission admittedCull{}", 1)[0]
draw = bridge.split("void observe(IDirect3DDevice9* game,", 1)[1].split(
    "} // namespace", 1)[0]
def linked(candidate, draw_source=draw):
    return all(x in candidate for x in (
        "GetRenderState(D3DRS_STENCILFUNC, &stencilFunc)",
        "GetRenderState(D3DRS_STENCILWRITEMASK, &stencilWriteMask)",
        "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)",
        "stencil_equivalent_to_disabled(",
        "GetDeviceCaps(&caps)", "valid_mrt_count(caps.NumSimultaneousRTs)",
        "GetRenderTarget(slot, extra.GetAddressOf())",
        "if (hr == D3DERR_NOTFOUND) continue;",
        "GetRenderState(extraColorMasks[slot - 1u],",
        "extra_target_inert(true, extraMask)",
    )) and all(x in draw_source for x in (
        "if (fullMode && output.nativeDepthTest)",
        "main_depth_still_bound(",
        "s.frameBatch.abort();",
        "if (!supported_game_state(game, type,",
    ))
assert linked(admission), "inert main GPU Draw or canonical main Z not wired"
for old in ("stencil_equivalent_to_disabled(", "extra_target_inert(true, extraMask)",
            "GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided)"):
    assert not linked(admission.replace(old, "bypassed(", 1)), old
assert not linked(admission, draw.replace(
    "if (fullMode && output.nativeDepthTest)", "if (false)", 1))
assert "python tools/test_dx11_inert_stencil_mrt_main_game_00785.py" in workflow
cxx = shutil.which("g++") or shutil.which("clang++")
assert cxx, "C++17 compiler required"
with TemporaryDirectory(prefix="dx11-main-active-draw-") as tmp:
    base = Path(tmp)
    (base / "src/vr/d3d11").mkdir(parents=True)
    (base / "tools").mkdir()
    headers = ("native_game_inert_stencil_mrt.hpp", "native_game_offscreen_pass.hpp",
               "native_game_clear_color.hpp", "native_game_frame_batch.hpp")
    for name in headers:
        shutil.copyfile(root / "src/vr/d3d11" / name,
                        base / "src/vr/d3d11" / name)
    name = "dx11_inert_stencil_mrt_main_game_00785.cpp"
    shutil.copyfile(root / "tools" / name, base / "tools" / name)
    exe = base / "main_active_draw"
    cmd = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
           "-pedantic", str(base / "tools" / name), "-o", str(exe)]
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run([str(exe)], check=True, capture_output=True)
    hdr = base / "src/vr/d3d11/native_game_inert_stencil_mrt.hpp"
    content = hdr.read_text(encoding="utf-8")
    assert "writeMask == 0u" in content
    hdr.write_text(content.replace("writeMask == 0u", "true", 1), encoding="utf-8")
    assert subprocess.run(cmd, capture_output=True).returncode != 0, (
        "unsafe writable stencil mutation must fail compiled test")
    hdr.write_text(content.replace(
        "return stateKnown && writeMask == 0u;",
        "return stateKnown;"), encoding="utf-8")
    assert subprocess.run(cmd, capture_output=True).returncode != 0, (
        "unsafe writable MRT mutation must fail compiled test")
print("00785 inert-stencil/MRT real GPU Draw and canonical main-Z fallback PASS")
