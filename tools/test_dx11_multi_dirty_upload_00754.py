#!/usr/bin/env python3
"""Multi-dirty full-game output requires D3D9 gap seed + single atomic upload."""
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
    snapshot=p.find("game->GetRenderTargetData(\n",bound)
    locked=p.find("SUCCEEDED(s.insetSurface->LockRect(",snapshot)
    copy=p.find("for (std::uint32_t i = 0u; i < multiDirty.count; ++i)",locked)
    unlock=p.find("const HRESULT unlockStatus",copy)
    branch=p.find("if (!multiNativeUpload)",unlock)
    gpu=p.find("const auto& bounds = multiDirty.uploadBounds;",branch)
    single=p.find("uploaded = SUCCEEDED(game->UpdateSurface(",gpu)
    return all((
        '#include "native_game_multi_dirty_upload.hpp"' in s,
        0<=select<admit<bound<snapshot<locked<copy<unlock<branch<gpu<single,
        "fullMode && backbufferKnown &&" in p[admit:bound],
        "multiDirty.valid" in p[admit:bound],
        "(multiNativeUpload && fullPlacement.valid)" in p[bound:snapshot],
        "(!multiNativeUpload || SUCCEEDED(game->GetRenderTargetData(" in p[bound:locked],
        "GameNativeFrameUpload::copy_rect(" in p[copy:unlock],
        "!copied || FAILED(unlockStatus)" in p[unlock:branch],
        "s.insetSurface.Get(), &sourceTiles," in p[single:],
        "back.Get(), &targetTiles" in p[single:],
        p.count("game->UpdateSurface(")==2,
        "if (uploaded)" in p[single:],
        "r.left < p.right && p.left < r.right" in h,
        "r.top < p.bottom && p.top < r.bottom" in h,
        "bufferBytes < rectangleCount * 16u" in h,
        "minX != boundLeft || minY != boundTop" in h,
        "!out.count" in h,
        "out.regions[out.count++] = {left, top, right, bottom};" in h,
        "out.uploadBounds = {uploadLeft, uploadTop, uploadRight, uploadBottom};" in h,
    ))
assert connected(src,hdr), "multi-dirty atomic game frame/Present contract broken"
for before,after in (
    ("multiDirty.valid;","true /* unchecked */;"),
    ("(multiNativeUpload && fullPlacement.valid)","false /* dropped */"),
    ("const bool multiNativeUpload = fullMode && backbufferKnown &&",
     "const bool multiNativeUpload = true /* unchecked */ &&"),
    ("game->GetRenderTargetData(","game->DisabledReadback("),
    ("const auto& bounds = multiDirty.uploadBounds;","const auto& bounds = presentRegion;"),
    ("back.Get(), &targetTiles","back.Get(), &destination"),
    ("s.insetSurface.Get(), &sourceTiles,","s.insetSurface.Get(), nullptr,"),
    ("!copied || FAILED(unlockStatus)","FAILED(unlockStatus)"),
):
    variant=src.replace(before,after,1)
    assert variant!=src and not connected(variant,hdr), before
for before,after in (
    ("r.left < p.right && p.left < r.right","false /* overlap */"),
    ("bufferBytes < rectangleCount * 16u","false /* unchecked buffer */"),
    ("minX != boundLeft || minY != boundTop","false /* forged bbox */"),
    ("!out.count","false /* empty */"),
    ("out.uploadBounds = {uploadLeft, uploadTop, uploadRight, uploadBottom};",
     "out.uploadBounds = {};"),
):
    variant=hdr.replace(before,after,1)
    assert variant!=hdr and not connected(src,variant),before
assert "python tools/test_dx11_multi_dirty_upload_00754.py" in wf
assert "tools/dx11_multi_dirty_upload_probe_00754.cpp" in wf
print("DX11 atomic multi-dirty Present: original D3D9 gaps and one native commit PASS")
