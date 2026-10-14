#!/usr/bin/env python3
"""00750 full-size native frame inside an exact D3D9 dirty Present crop."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR = (ROOT/"src/vr/d3d11/native_game_dirty_region.hpp").read_text(encoding="utf-8")
WF = (ROOT/".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def integrated(source, header):
    a=source.find("void before_game_present(")
    b=source.find("void before_game_reset(",a)
    if a<0 or b<=a: return False
    code=source[a:b]
    single_start=header.find("static constexpr bool covers_present_crop(")
    tile_start=header.find("static constexpr bool covers_partition_crop(", single_start)
    full_partition_start=header.find("static constexpr bool covers_partition(", tile_start)
    if not 0<=single_start<tile_start<full_partition_start: return False
    single_hdr=header[single_start:tile_start]
    tiled_hdr=header[tile_start:full_partition_start]
    crop_admission=code.find("const bool cropDirtyCoverage =")
    gate=code.find("GameNativeDirtyRegionCoverage::covers_present_crop(")
    bound=code.find("const bool outputWritable =",gate)
    queued=code.find("ctx->CopyResource(next.staging.Get(), s.backend.color_texture());",bound)
    tiled=code.find("GameNativeDirtyRegionCoverage::covers_partition_crop(",gate)
    crop=code.find("const RECT uploadSourceCrop{",queued)
    dest=code.find("destination.x = uploadSourceCrop.left;",crop)
    submit=code.find("game->UpdateSurface(",dest)
    return all((
        '#include "native_game_dirty_region.hpp"' in source,
        0<=crop_admission<gate<tiled<bound<queued<crop<dest<submit,
        # Do not match the earlier *whole-backbuffer* oneBoundedDirtyRect.
        # This guard must belong to the cropped-source admission itself.
        "oneBoundedDirtyRect &&" in code[crop_admission:gate],
        "dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top" in code[gate:bound],
        "dirtyRect.left, dirtyRect.top, dirtyRect.right, dirtyRect.bottom" in code[gate:bound],
        "croppedNativeUpload && fullPlacement.valid" in code[bound:queued],
        "boundedPartition &&" in code[gate:bound],
        "(cropDirtyCoverage || partitionCropCoverage) && !fullDirtyCoverage" in code[tiled:bound],
        "partitionRects);" in code[tiled:bound],
        "const bool partitionCropCoverage = fullMode && backbufferKnown &&" in code[gate:tiled],
        "(!outputNow.hasDirtyRegion || fullDirtyCoverage) &&" in code[bound:queued],
        "croppedNativeUpload ? &uploadSourceCrop : nullptr" in code[submit:submit+220],
        "destination.y = uploadSourceCrop.top;" in code[crop:submit],
        "s.insetSurface.Get()" in code[submit:submit+220],
        "cropRight > static_cast<std::int64_t>(width)" in single_hdr,
        "cropBottom > static_cast<std::int64_t>(height)" in single_hdr,
        "rectangleCount != 1u || bufferBytes < 16u" in single_hdr,
        "boundLeft == cropLeft && boundTop == cropTop" in single_hdr,
        "static constexpr bool covers_partition_crop(" in tiled_hdr,
        "bufferBytes < rectangleCount * 16u" in tiled_hdr,
        "boundLeft != cropLeft || boundTop != cropTop" in tiled_hdr,
        "if (area > total - covered) return false;" in tiled_hdr,
        "r.left < p.right && p.left < r.right" in tiled_hdr,
        "rectRight == cropRight && rectBottom == cropBottom" in single_hdr,
        "(cropLeft == 0 && cropTop == 0 &&" in single_hdr,
    ))
assert integrated(SRC,HDR), "crop must bind region proof -> admission -> bounded UpdateSurface"
for old,new in (
    ("oneBoundedDirtyRect &&\n            GameNativeDirtyRegionCoverage::covers_present_crop(",
     "true /* unchecked region */ &&\n            GameNativeDirtyRegionCoverage::covers_present_crop("),
    ("croppedNativeUpload && fullPlacement.valid","true /* unbounded crop */"),
    ("croppedNativeUpload ? &uploadSourceCrop : nullptr","nullptr /* full overwrite */"),
    ("destination.x = uploadSourceCrop.left;","destination.x = 0;"),
    ("destination.y = uploadSourceCrop.top;","destination.y = 0;"),
    ("(cropDirtyCoverage || partitionCropCoverage) && !fullDirtyCoverage",
     "cropDirtyCoverage && !fullDirtyCoverage"),
    ("boundedPartition &&\n            GameNativeDirtyRegionCoverage::covers_partition_crop(",
     "true /* unsafe partial tiles */ &&\n            GameNativeDirtyRegionCoverage::covers_partition_crop("),
):
    mutant=SRC.replace(old,new,1)
    assert mutant!=SRC and not integrated(mutant,HDR),old
for old,new in (
    ("rectangleCount != 1u || bufferBytes < 16u","false /* unknown dirty bytes */"),
    ("boundLeft == cropLeft && boundTop == cropTop","true /* unverified bounds */"),
    ("rectRight == cropRight && rectBottom == cropBottom","true /* partial dirty */"),
    ("cropRight > static_cast<std::int64_t>(width)","false /* OOB x */"),
    ("cropBottom > static_cast<std::int64_t>(height)","false /* OOB y */"),
    ("boundLeft != cropLeft || boundTop != cropTop", "false /* unchecked tiled bounds */"),
    ("static constexpr bool covers_partition_crop(", "static constexpr bool unchecked_partition_crop("),
):
    mutant=HDR.replace(old,new,1)
    assert mutant!=HDR and not integrated(SRC,mutant),old
assert "python tools/test_dx11_full_dirty_crop_00750.py" in WF
assert "tools/dx11_full_dirty_crop_probe_00750.cpp" in WF
print("00750 full native cropped game Present and D3D9 fallback source gates PASS")
