#!/usr/bin/env python3
"""R33 stereo viewport-elision ownership/negative-mutation regression."""
from pathlib import Path

src = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8")
start = src.index("bool R33TargetResetViewportMatches(")
end = src.index("thread_local R33DepthStencilWriteState", start)
helper = src[start:end]
assert "rightEye->GetDesc(&desc)" in helper
assert "desc.Width == 0 || desc.Height == 0" in helper
for condition in ("saved.X != 0", "saved.Y != 0",
                  "saved.MinZ != 0.0f", "saved.MaxZ != 1.0f",
                  "saved.Width == R33RightViewport.width",
                  "saved.Height == R33RightViewport.height"):
    assert condition in helper, condition
assert src.count("R33TargetResetViewportMatches(rightEye, savedViewport)") == 2
assert src.count("SUCCEEDED(rightHr) && !viewportAlreadyFull") == 2
assert src.count("rightHr = device->SetViewport(&savedViewport);") == 2
assert src.count("R33RightViewport = {};") >= 3  # re-probe, Reset, rollback
# These mutation classes must each fail the source contract.
for mutant in (
    helper.replace("saved.X != 0", "saved.X == 0", 1),
    helper.replace("saved.MaxZ != 1.0f", "saved.MaxZ != 0.0f", 1),
    helper.replace("saved.Height == R33RightViewport.height", "true", 1),
    helper.replace("rightEye->GetDesc(&desc)", "rightEye->GetContainer(nullptr, nullptr)", 1),
):
    assert any(token not in mutant for token in (
        "saved.X != 0", "saved.MaxZ != 1.0f",
        "saved.Height == R33RightViewport.height",
        "rightEye->GetDesc(&desc)"))
def can_skip(x, y, w, h, minz, maxz, targetw, targeth):
    return (x == 0 and y == 0 and minz == 0.0 and maxz == 1.0
            and w == targetw and h == targeth)
assert can_skip(0, 0, 2496, 2688, 0, 1, 2496, 2688)
for inputs in (
    (1, 0, 2496, 2688, 0, 1, 2496, 2688),
    (0, 0, 2496, 2688, 0, 1, 2048, 2160),
    (0, 0, 2496, 2688, 0.1, 1, 2496, 2688),
    (0, 0, 2496, 2688, 0, 0.9, 2496, 2688),
):
    assert not can_skip(*inputs)
print("R33 full-target viewport elision: PASS")

# Original RT0 restoration must not borrow right-eye extent or elide a failed
# SetRenderTarget. Check both dispatcher routes, C++ guard and model mutations.
r32 = (Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r32.cpp").read_text(encoding="utf-8")
api = (Path(__file__).resolve().parents[1] / "src/vr/core/r32_review_api.hpp").read_text(encoding="utf-8")
restore = r32.split("bool R32RestoreRightPassState(",1)[1].split("template <typename LowerDraw>",1)[0]
saved = src.split("bool R33SavedTargetResetViewportMatches(",1)[1].split("thread_local R33DepthStencilWriteState",1)[0]
for tok in ("!savedRt", "saved.X != 0", "saved.Y != 0", "saved.MinZ != 0.0f",
            "saved.MaxZ != 1.0f", "savedRt->GetDesc(&desc)",
            "desc.Width == 0 || desc.Height == 0",
            "saved.Width == R33SavedViewport.width", "saved.Height == R33SavedViewport.height"):
    assert tok in saved, tok
assert src.count("R33SavedTargetResetViewportMatches(savedRt, savedViewport)") == 2
assert src.count("StateBlockTracker::Reliable() &&\n                R33SavedTargetResetViewportMatches") == 2
assert src.count("true, depthlessPass, skipSavedViewportRestore);") == 2
assert src.count("R33SavedViewport = {};") >= 3
assert "bool skipSavedViewportRestore) noexcept;" in api
assert "bool restoredRt = false;" in restore
assert "restoredRt = SUCCEEDED(R30SupportCallOriginalSetRenderTarget(" in restore
assert "(!restoredRt || !skipSavedViewportRestore)" in restore
assert "FAILED(device->SetViewport(&savedViewport))" in restore
assert restore.index("R30SupportCallOriginalSetRenderTarget(") < restore.index("device->SetViewport(&savedViewport)")
for a,b in (("saved.MinZ != 0.0f","false"),
            ("saved.Width == R33SavedViewport.width","true"),
            ("savedRt->GetDesc(&desc)","savedRt->GetContainer(nullptr,nullptr)"),
            ("R33SavedViewport.surface != savedRt","false")):
    assert a in saved and a not in saved.replace(a,b,1)
def can_skip_restore(bind_ok, reliable, x,y,w,h,minz,maxz,rw,rh):
    return bind_ok and reliable and can_skip(x,y,w,h,minz,maxz,rw,rh)
for w,h in ((640,480),(1920,1080),(3440,1440),(2496,2688)):
    assert can_skip_restore(True, True,0,0,w,h,0.,1.,w,h)
    for x,y,sw,sh,minz,maxz,rw,rh,bind,reliable in (
        (1,0,w,h,0.,1.,w,h,True,True),
        (0,0,w-1,h,0.,1.,w,h,True,True),
        (0,0,w,h,.1,1.,w,h,True,True),
        (0,0,w,h,0.,1.,w+1,h,True,True),
        (0,0,w,h,0.,1.,w,h,False,True),
        (0,0,w,h,0.,1.,w,h,True,False)):
        assert not can_skip_restore(bind,reliable,x,y,sw,sh,minz,maxz,rw,rh)
print("R33 restore-side viewport guarded world/HUD path: PASS")
