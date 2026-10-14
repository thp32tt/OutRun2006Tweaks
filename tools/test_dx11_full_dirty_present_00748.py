#!/usr/bin/env python3
"""00748: real D3D9 whole-backbuffer dirty Present can publish full native frame."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR = (ROOT / "src/vr/d3d11/native_game_dirty_region.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(src, hdr):
    a = src.find("void before_game_present(")
    b = src.find("void before_game_reset(", a)
    if not 0 <= a < b: return False
    code = src[a:b]
    read = code.find("std::memcpy(&dirtyRect, dirtyRegion->Buffer, sizeof(dirtyRect));")
    covered = code.find("GameNativeDirtyRegionCoverage::covers_full_backbuffer(", read)
    writable = code.find("const bool outputWritable =", covered)
    enqueue = code.find("ctx->CopyResource(next.staging.Get(), s.backend.color_texture());", writable)
    upload = code.find("game->UpdateSurface(", enqueue)
    return all((
        '#include "native_game_dirty_region.hpp"' in src,
        0 <= read < covered < writable < enqueue < upload,
        "dirtyRegion->rdh.nCount == 1u" in code[:read],
        "dirtyRegion->rdh.nRgnSize >= sizeof(RECT)" in code[:read],
        "dirtyRegion->rdh.iType == RDH_RECTANGLES" in code[:covered],
        "fullMode && backbufferKnown && dirtyRegion" in code[:covered],
        "(!outputNow.hasDirtyRegion || fullDirtyCoverage)" in code[writable:enqueue],
        "fullDirtyCoverage" not in code[enqueue:upload],
        "rectangleCount == 1u && bufferBytes >= 16u" in hdr,
        "rectLeft == boundLeft && rectTop == boundTop" in hdr,
        "rectRight == boundRight && rectBottom == boundBottom" in hdr,
        "boundRight == static_cast<std::int64_t>(width)" in hdr,
    ))
assert integrated(SRC, HDR), "whole-coverage D3D9 dirty Present must opt in safely"
for old, new in (
    ("(!outputNow.hasDirtyRegion || fullDirtyCoverage)", "true /* bypass dirty */"),
    ("dirtyRegion->rdh.nCount == 1u", "dirtyRegion->rdh.nCount >= 1u"),
    ("dirtyRegion->rdh.nRgnSize >= sizeof(RECT)", "true /* unknown size */"),
    ("dirtyRegion->rdh.iType == RDH_RECTANGLES", "true /* ignored region kind */"),
    ("GameNativeDirtyRegionCoverage::covers_full_backbuffer(", "/* no proof */("),
    ("std::memcpy(&dirtyRect, dirtyRegion->Buffer, sizeof(dirtyRect));", "/* no dirty rectangle snapshot */"),
):
    mutant = SRC.replace(old, new, 1)
    assert mutant != SRC and not integrated(mutant, HDR), old
for old, new in (
    ("rectangleCount == 1u && bufferBytes >= 16u", "rectangleCount > 0u"),
    ("rectRight == boundRight && rectBottom == boundBottom", "true"),
    ("boundRight == static_cast<std::int64_t>(width)", "true"),
):
    mutant = HDR.replace(old, new, 1)
    assert mutant != HDR and not integrated(SRC, mutant), old
assert "python tools/test_dx11_full_dirty_present_00748.py" in WF
assert "tools/dx11_full_dirty_present_probe_00748.cpp" in WF
print("00748 strict full dirty D3D9 Present -> native full-frame publication, fallback PASS")
