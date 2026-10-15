#!/usr/bin/env python3
"""00754 verifies game-origin multi-RECT Present upload and unchanged D3D9/gamepad fallback."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr=(root/"src/vr/d3d11/native_game_multi_dirty_upload.hpp").read_text()
wf=(root/".github/workflows/dx11-fast-structural.yml").read_text()
def connected(s,h):
    a=s.find("void before_game_present(")
    b=s.find("void before_game_reset(",a)
    if a<0 or b<=a: return False
    p=s[a:b]
    select=p.find("const auto multiDirty = GameNativeMultiDirtyUpload::select(")
    admit=p.find("const bool multiNativeUpload =",select)
    bound=p.find("const bool outputWritable =",admit)
    copy=p.find("for (std::uint32_t i = 0u; i < multiDirty.count; ++i)",bound)
    unlock=p.find("const HRESULT unlockStatus",copy)
    upload=p.find("if (!multiNativeUpload)",unlock)
    tiles=p.find("for (std::uint32_t i = 0u; i < multiDirty.count; ++i)",upload)
    return all((
        '#include "native_game_multi_dirty_upload.hpp"' in s,
        0<=select<admit<bound<copy<unlock<upload<tiles,
        "boundedPartition && !fullDirtyCoverage && !croppedNativeUpload &&" in p[admit:bound],
        "multiDirty.valid" in p[admit:bound],
        "(multiNativeUpload && fullPlacement.valid)" in p[bound:copy],
        "GameNativeFrameUpload::copy_rect(" in p[copy:unlock],
        "!copied || FAILED(unlockStatus)" in p[unlock:upload],
        "uploaded = SUCCEEDED(game->UpdateSurface(" in p[upload:tiles],
        "if (FAILED(game->UpdateSurface(" in p[tiles:],
        "s.insetSurface.Get(), &sourceTile," in p[tiles:],
        "back.Get(), &targetTile" in p[tiles:],
        "if (uploaded)" in p[tiles:],
        "r.left < p.right && p.left < r.right" in h,
        "r.top < p.bottom && p.top < r.bottom" in h,
        "bufferBytes < rectangleCount * 16u" in h,
        "minX != boundLeft || minY != boundTop" in h,
        "!out.count" in h,
        "out.regions[out.count++] = {left, top, right, bottom};" in h,
    ))
assert connected(src,hdr),"multi dirty game frame/Present integration broken"
for before,after in (
    ("multiDirty.valid;","true /* unchecked */;"),
    ("(multiNativeUpload && fullPlacement.valid)","false /* dropped */"),
    ("boundedPartition && !fullDirtyCoverage && !croppedNativeUpload &&",
     "true /* ignore region */ &&"),
    ("back.Get(), &targetTile","back.Get(), &destination"),
    ("if (FAILED(game->UpdateSurface(","if (false /* upload bypassed */ && FAILED(game->UpdateSurface("),
    ("!copied || FAILED(unlockStatus)","FAILED(unlockStatus)"),
):
    variant=src.replace(before,after,1)
    assert variant!=src and not connected(variant,hdr),before
for before,after in (
    ("r.left < p.right && p.left < r.right","false /* overlap */"),
    ("bufferBytes < rectangleCount * 16u","false /* unchecked buffer */"),
    ("minX != boundLeft || minY != boundTop","false /* forged bbox */"),
    ("!out.count","false /* empty */"),
):
    variant=hdr.replace(before,after,1)
    assert variant!=hdr and not connected(src,variant),before
assert "python tools/test_dx11_multi_dirty_upload_00754.py" in wf
assert "tools/dx11_multi_dirty_upload_probe_00754.cpp" in wf
print("00754 native multi-dirty game Draw/Present with hole-safe D3D9/gamepad fallback PASS")
