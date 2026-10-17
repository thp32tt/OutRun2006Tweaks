#!/usr/bin/env python3
"""00767 integrated D3D11 full-frame -> D3D9 Present 32-region output + fallback."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
dirty = (root / "src/vr/d3d11/native_game_dirty_region.hpp").read_text(encoding="utf-8")
multi = (root / "src/vr/d3d11/native_game_multi_dirty_upload.hpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
probe = root / "tools/dx11_extended_dirty_batch_probe_00767.cpp"

def linked(text, hdr, selector):
    p = text.split("void before_game_present(", 1)[-1].split("void before_game_reset(", 1)[0]
    return all((
        "kMaxPartitionRects = 32u" in hdr,
        "rectangleCount > kMaxPartitionRects" in hdr,
        "rectangleCount > GameNativeDirtyRegionCoverage::kMaxPartitionRects" in selector,
        "dirtyRegion->rdh.nCount <= GameNativeDirtyRegionCoverage::kMaxPartitionRects" in p,
        "dirtyRegion->rdh.nRgnSize >= dirtyRegion->rdh.nCount * sizeof(RECT)" in p,
        "GameNativeDirtyRegionCoverage::covers_partition(" in p,
        "GameNativeDirtyRegionCoverage::covers_partition_crop(" in p,
        "const auto multiDirty = GameNativeMultiDirtyUpload::select(" in p,
        "(!multiNativeUpload || SUCCEEDED(game->GetRenderTargetData(" in p,
        "for (std::uint32_t i = 0u; i < multiDirty.count; ++i)" in p,
        "GameNativeFrameUpload::copy_rect(" in p,
        "s.insetSurface.Get(), &sourceTiles," in p,
        "back.Get(), &targetTiles" in p,
        "if (!multiNativeUpload)" in p,
        "if (uploaded)" in p,
    ))

assert linked(bridge, dirty, multi)
assert not linked(bridge, dirty.replace("kMaxPartitionRects = 32u", "kMaxPartitionRects = 8u"), multi)
assert not linked(bridge.replace(
    "dirtyRegion->rdh.nCount <= GameNativeDirtyRegionCoverage::kMaxPartitionRects",
    "dirtyRegion->rdh.nCount <= 8u"), dirty, multi)
assert not linked(bridge.replace(
    "(!multiNativeUpload || SUCCEEDED(game->GetRenderTargetData(",
    "(true || SUCCEEDED(game->GetRenderTargetData("), dirty, multi)
assert "python tools/test_dx11_extended_dirty_batch_00767.py" in workflow

cxx = shutil.which("g++") or shutil.which("clang++")
assert cxx, "portable C++17 compiler required"
with TemporaryDirectory(prefix="dx11-complex-dirty-") as tmp:
    dst = Path(tmp)
    (dst / "tools").mkdir()
    (dst / "src/vr/d3d11").mkdir(parents=True)
    for filename in ("native_game_dirty_region.hpp", "native_game_multi_dirty_upload.hpp",
                     "native_game_frame_upload.hpp", "native_game_present_region.hpp",
                     "native_game_frame_publication.hpp"):
        shutil.copyfile(root / "src/vr/d3d11" / filename, dst / "src/vr/d3d11" / filename)
    shutil.copyfile(probe, dst / "tools" / probe.name)
    output = dst / "extended_dirty_probe"
    cmd = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
           "-pedantic", str(dst / "tools" / probe.name), "-o", str(output)]
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run([str(output)], check=True, capture_output=True)
    # An obsolete eight-rectangle compiler build must fail the positive
    # full-frame/crop static_asserts, not merely a source-text probe.
    header = dst / "src/vr/d3d11/native_game_dirty_region.hpp"
    header.write_text(dirty.replace("kMaxPartitionRects = 32u",
                                    "kMaxPartitionRects = 8u"), encoding="utf-8")
    negative = subprocess.run(cmd, capture_output=True)
    assert negative.returncode != 0, "eight-region regression escaped C++ proof"
print("00767 32-tile menu/car/race full-frame + crop + atomic D3D9 fallback PASS")
