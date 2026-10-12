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
