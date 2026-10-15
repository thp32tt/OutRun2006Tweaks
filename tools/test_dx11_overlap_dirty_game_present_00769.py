#!/usr/bin/env python3
"""00769 full-resolution native game Present: overlapping partial dirty tiles."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
bridge = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (ROOT / "src/vr/d3d11/native_game_multi_dirty_upload.hpp").read_text()
workflow = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(s, h):
    p = s.split("void before_game_present(", 1)[-1].split(
        "void before_game_reset(", 1)[0]
    select = p.find("const auto multiDirty = GameNativeMultiDirtyUpload::select(")
    snapshot = p.find("game->GetRenderTargetData(", select)
    locks = p.find("s.insetSurface->LockRect(", snapshot)
    copies = p.find("for (std::uint32_t i = 0u; i < multiDirty.count; ++i)", locks)
    bound = p.find("const auto& bounds = multiDirty.uploadBounds;", copies)
    upload = p.find("game->UpdateSurface(", bound)
    return all((
        "bool allowOverlap = false" in h,
        "if (!allowOverlap)" in h,
        "r.left < p.right && p.left < r.right" in h,
        "r.top < p.bottom && p.top < r.bottom" in h,
        "minX != boundLeft || minY != boundTop" in h,
        "bufferBytes < rectangleCount * 16u" in h,
        0 <= select < snapshot < locks < copies < bound < upload,
        "true /* overlapping game dirty tiles are identical native pixels */"
            in p[select:snapshot],
        "(!multiNativeUpload || SUCCEEDED(game->GetRenderTargetData(" in p,
        "GameNativeFrameUpload::copy_rect(" in p[copies:bound],
        "s.insetSurface.Get(), &sourceTiles," in p[upload:],
        "back.Get(), &targetTiles" in p[upload:],
        "if (!copied || FAILED(unlockStatus))" in p,
    ))

assert integrated(bridge, header), "live game native overlap-to-Present disconnected"
for before, after in (
    ("true /* overlapping game dirty tiles are identical native pixels */",
     "false /* no overlap */"),
    ("game->GetRenderTargetData(", "game->IgnoreD3D9Seed("),
    ("const auto& bounds = multiDirty.uploadBounds;",
     "const auto& bounds = presentRegion;"),
    ("back.Get(), &targetTiles", "back.Get(), &destination"),
):
    mutant = bridge.replace(before, after, 1)
    assert mutant != bridge and not integrated(mutant, header), before
for before, after in (
    ("if (!allowOverlap)", "if (true)"),
    ("bool allowOverlap = false", "bool allowOverlap = true"),
    ("minX != boundLeft || minY != boundTop", "false /* bounds bypass */"),
):
    mutant = header.replace(before, after, 1)
    assert mutant != header and not integrated(bridge, mutant), before
assert "python tools/test_dx11_overlap_dirty_game_present_00769.py" in workflow
assert "tools/dx11_overlap_dirty_game_present_00769.cpp" in workflow

cxx = shutil.which("g++") or shutil.which("clang++")
assert cxx, "portable C++17 compiler required"
with TemporaryDirectory(prefix="dx11-overlap-present-") as tmpdir:
    tmp = Path(tmpdir)
    (tmp / "tools").mkdir()
    (tmp / "src/vr/d3d11").mkdir(parents=True)
    names = ("native_game_multi_dirty_upload.hpp",
             "native_game_dirty_region.hpp", "native_game_present_region.hpp",
             "native_game_frame_upload.hpp", "native_game_frame_publication.hpp")
    for name in names:
        shutil.copyfile(ROOT / "src/vr/d3d11" / name,
                        tmp / "src/vr/d3d11" / name)
    name = "dx11_overlap_dirty_game_present_00769.cpp"
    shutil.copyfile(ROOT / "tools" / name, tmp / "tools" / name)
    executable = tmp / "overlap_probe"
    command = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
               "-pedantic", str(tmp / "tools" / name), "-o", str(executable)]
    subprocess.run(command, check=True, capture_output=True)
    subprocess.run([str(executable)], check=True, capture_output=True)
    modified = tmp / "src/vr/d3d11/native_game_multi_dirty_upload.hpp"
    modified.write_text(header.replace("if (!allowOverlap)", "if (true)"))
    assert subprocess.run(command, capture_output=True).returncode != 0, (
        "strict-only regression escaped compiled positive proof")
print("00769 native overlapping menu/car/race Present + D3D9 fallback PASS")
