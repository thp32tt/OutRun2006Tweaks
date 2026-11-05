#!/usr/bin/env python3
"""00753 single partial dirty native full-game Present and input-safe D3D9 fallback."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR=(ROOT/"src/vr/d3d11/native_game_partial_dirty_upload.hpp").read_text(encoding="utf-8")
WF=(ROOT/".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def connected(src,hdr):
    a=src.find("void before_game_present(")
    b=src.find("void before_game_reset(",a)
    if not 0<=a<b: return False
    code=src[a:b]
    selection=code.find("const auto partialDirty = GameNativePartialDirtyUpload::select(")
    admission=code.find("const bool partialNativeUpload =",selection)
    writable=code.find("const bool outputWritable =",admission)
    readback=code.find("ctx->CopyResource(next.staging.Get(), s.backend.color_texture());",writable)
    copy=code.find("partialNativeUpload\n                                             ? GameNativeFrameUpload::copy_rect(",readback)
    unlock=code.find("const HRESULT unlockStatus",copy)
    upload=code.find("game->UpdateSurface(",unlock)
    return all((
      '#include "native_game_partial_dirty_upload.hpp"' in src,
      0<=selection<admission<writable<readback<copy<unlock<upload,
      "oneBoundedDirtyRect && !fullDirtyCoverage && !croppedNativeUpload &&" in code[admission:writable],
      "partialDirty.valid" in code[admission:writable],
      "(partialNativeUpload && fullPlacement.valid)" in code[writable:readback],
      "partialDirty.source.left" in code[copy:unlock],
      "partialDirty.source.bottom" in code[copy:unlock],
      "partialNativeUpload ? &partialSourceUpload :" in code[upload:upload+360],
      "croppedNativeUpload ? &uploadSourceCrop : nullptr" in code[upload:upload+360],
      "destination.x = partialSourceUpload.left;" in code[copy:upload],
      "destination.y = partialSourceUpload.top;" in code[copy:upload],
      "!copied || FAILED(unlockStatus)" in code[copy:upload],
      "rectangleCount != 1u || bufferBytes < 16u" in hdr,
      "boundLeft != rectLeft || boundTop != rectTop" in hdr,
      "rectRight > static_cast<std::int64_t>(width)" in hdr,
      "left >= right || top >= bottom" in hdr,
      "presentSource.full_frame_placement(width, height, width, height).valid" in hdr,
    ))
assert connected(SRC,HDR), "native partial dirty game Draw/Present wiring incomplete"
for old,new in (
 ("oneBoundedDirtyRect && !fullDirtyCoverage && !croppedNativeUpload &&","true /* unbounded */ &&"),
 ("partialDirty.valid;","true /* unchecked */;"),
 ("(partialNativeUpload && fullPlacement.valid)","false /* disabled */"),
 ("partialNativeUpload ? &partialSourceUpload :","nullptr /* broken source */ ? &partialSourceUpload :"),
 ("destination.x = partialSourceUpload.left;","destination.x = 0;"),
 ("destination.y = partialSourceUpload.top;","destination.y = 0;"),
 ("!copied || FAILED(unlockStatus)","FAILED(unlockStatus)"),
):
    mutant=SRC.replace(old,new,1)
    assert mutant!=SRC and not connected(mutant,HDR),old
for old,new in (
 ("rectangleCount != 1u || bufferBytes < 16u","false /* unchecked */"),
 ("boundLeft != rectLeft || boundTop != rectTop","false /* unchecked */"),
 ("left >= right || top >= bottom","false /* unchecked */"),
 ("presentSource.full_frame_placement(width, height, width, height).valid","true /* unchecked */"),
):
    mutant=HDR.replace(old,new,1)
    assert mutant!=HDR and not connected(SRC,mutant),old
assert "python tools/test_dx11_partial_dirty_upload_00753.py" in WF
assert "tools/dx11_partial_dirty_upload_probe_00753.cpp" in WF
print("00753 partial native game Present / cropped dirty source / D3D9 input fallback PASS")
