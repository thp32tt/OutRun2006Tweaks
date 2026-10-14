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
    gate=code.find("GameNativeDirtyRegionCoverage::covers_present_crop(")
    bound=code.find("const bool outputWritable =",gate)
    queued=code.find("ctx->CopyResource(next.staging.Get(), s.backend.color_texture());",bound)
    crop=code.find("const RECT uploadSourceCrop{",queued)
    dest=code.find("destination.x = uploadSourceCrop.left;",crop)
    submit=code.find("game->UpdateSurface(",dest)
    return all((
        '#include "native_game_dirty_region.hpp"' in source,
        0<=gate<bound<queued<crop<dest<submit,
        "oneBoundedDirtyRect &&" in code[:gate],
        "dirtyRegion->rdh.rcBound.left, dirtyRegion->rdh.rcBound.top" in code[gate:bound],
        "dirtyRect.left, dirtyRect.top, dirtyRect.right, dirtyRect.bottom" in code[gate:bound],
        "croppedNativeUpload && fullPlacement.valid" in code[bound:queued],
        "(!outputNow.hasDirtyRegion || fullDirtyCoverage) &&" in code[bound:queued],
        "croppedNativeUpload ? &uploadSourceCrop : nullptr" in code[submit:submit+220],
        "destination.y = uploadSourceCrop.top;" in code[crop:submit],
        "s.insetSurface.Get()" in code[submit:submit+220],
        "cropRight > static_cast<std::int64_t>(width)" in header,
        "cropBottom > static_cast<std::int64_t>(height)" in header,
        "rectangleCount != 1u || bufferBytes < 16u" in header,
        "boundLeft == cropLeft && boundTop == cropTop" in header,
        "rectRight == cropRight && rectBottom == cropBottom" in header,
        "(cropLeft == 0 && cropTop == 0 &&" in header,
    ))
assert integrated(SRC,HDR), "crop must bind region proof -> admission -> bounded UpdateSurface"
for old,new in (
    ("oneBoundedDirtyRect &&\n            GameNativeDirtyRegionCoverage::covers_present_crop(",
     "true /* unchecked region */ &&\n            GameNativeDirtyRegionCoverage::covers_present_crop("),
    ("croppedNativeUpload && fullPlacement.valid","true /* unbounded crop */"),
    ("croppedNativeUpload ? &uploadSourceCrop : nullptr","nullptr /* full overwrite */"),
    ("destination.x = uploadSourceCrop.left;","destination.x = 0;"),
    ("destination.y = uploadSourceCrop.top;","destination.y = 0;"),
):
    mutant=SRC.replace(old,new,1)
    assert mutant!=SRC and not integrated(mutant,HDR),old
for old,new in (
    ("rectangleCount != 1u || bufferBytes < 16u","false /* unknown dirty bytes */"),
    ("boundLeft == cropLeft && boundTop == cropTop","true /* unverified bounds */"),
    ("rectRight == cropRight && rectBottom == cropBottom","true /* partial dirty */"),
    ("cropRight > static_cast<std::int64_t>(width)","false /* OOB x */"),
    ("cropBottom > static_cast<std::int64_t>(height)","false /* OOB y */"),
):
    mutant=HDR.replace(old,new,1)
    assert mutant!=HDR and not integrated(SRC,mutant),old
assert "python tools/test_dx11_full_dirty_crop_00750.py" in WF
assert "tools/dx11_full_dirty_crop_probe_00750.cpp" in WF
print("00750 full native cropped game Present and D3D9 fallback source gates PASS")
