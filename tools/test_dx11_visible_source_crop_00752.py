#!/usr/bin/env python3
"""00752 visible-source native game Present, null/full dirty and original D3D9 fallback."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR=(ROOT/"src/vr/d3d11/native_game_present_region.hpp").read_text(encoding="utf-8")
WF=(ROOT/".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def integrated(src,hdr):
    a=src.find("void before_game_present(")
    b=src.find("void before_game_reset(",a)
    if a<0 or b<=a: return False
    code=src[a:b]
    gate=code.find("const bool croppedNativeUpload =")
    output=code.find("const bool outputWritable =",gate)
    copy=code.find("GameNativeFrameUpload::copy_rect(",output)
    update=code.find("game->UpdateSurface(",copy)
    if not 0<=gate<output<copy<update: return False
    select=code[gate:output]
    return all((
        "presentRegion.partial_backbuffer_source(presentDesc.Width, presentDesc.Height)" in select,
        "(!dirtyRegion || fullDirtyCoverage || provenCroppedDirty)" in select,
        "(cropDirtyCoverage || partitionCropCoverage) && !fullDirtyCoverage" in code[code.find("const bool provenCroppedDirty ="):gate],
        "croppedNativeUpload && fullPlacement.valid" in code[output:copy],
        "croppedNativeUpload ? &uploadSourceCrop : nullptr" in code[update:update+360],
        "destination.x = uploadSourceCrop.left;" in code[copy:update],
        "destination.y = uploadSourceCrop.top;" in code[copy:update],
        "partial_backbuffer_source(" in hdr,
        "full_frame_placement(width, height, width, height).valid" in hdr,
        "left != 0 || top != 0" in hdr,
        "right != static_cast<std::int64_t>(width)" in hdr,
        "bottom != static_cast<std::int64_t>(height)" in hdr,
    ))
assert integrated(SRC,HDR), "partial D3D9 Present must clip native frame even with null/full dirty"
for before,after in (
    ("(!dirtyRegion || fullDirtyCoverage || provenCroppedDirty)","provenCroppedDirty"),
    ("presentRegion.partial_backbuffer_source(presentDesc.Width, presentDesc.Height)","true /* unchecked source */"),
    ("croppedNativeUpload ? &uploadSourceCrop : nullptr","nullptr /* outside-source overwrite */"),
    ("destination.x = uploadSourceCrop.left;","destination.x = 0;"),
    ("destination.y = uploadSourceCrop.top;","destination.y = 0;"),
):
    mutated=SRC.replace(before,after,1)
    assert mutated!=SRC and not integrated(mutated,HDR),before
for before,after in (
    ("full_frame_placement(width, height, width, height).valid","true /* unchecked bounds */"),
    ("left != 0 || top != 0","false /* missing offset */"),
    ("right != static_cast<std::int64_t>(width)","false /* missing extent */"),
):
    mutated=HDR.replace(before,after,1)
    assert mutated!=HDR and not integrated(SRC,mutated),before
assert "python tools/test_dx11_visible_source_crop_00752.py" in WF
assert "tools/dx11_visible_source_crop_probe_00752.cpp" in WF
print("00752 live native cropped Present, null/full dirty and D3D9/gamepad fallback PASS")
