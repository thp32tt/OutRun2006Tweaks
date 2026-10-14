#!/usr/bin/env python3
"""00749: a partitioned whole-D3D9-dirty Present can show native game output."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR = (ROOT / "src/vr/d3d11/native_game_dirty_region.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(src, hdr):
    start = src.find("void before_game_present(")
    end = src.find("void before_game_reset(", start)
    if not 0 <= start < end: return False
    code = src[start:end]
    partition = code.find("const bool boundedPartition =")
    read = code.find("std::memcpy(&part, dirtyRegion->Buffer + i * sizeof(RECT), sizeof(part));", partition)
    cover = code.find("GameNativeDirtyRegionCoverage::covers_partition(", read)
    writable = code.find("const bool outputWritable =", cover)
    gpu = code.find("ctx->CopyResource(next.staging.Get(), s.backend.color_texture());", writable)
    upload = code.find("game->UpdateSurface(", gpu)
    return all((
        0 <= partition < read < cover < writable < gpu < upload,
        "dirtyRegion->rdh.dwSize == sizeof(RGNDATAHEADER)" in code[partition:read],
        "dirtyRegion->rdh.iType == RDH_RECTANGLES" in code[partition:read],
        "dirtyRegion->rdh.nCount <= GameNativeDirtyRegionCoverage::kMaxPartitionRects" in code[partition:read],
        "dirtyRegion->rdh.nRgnSize >= dirtyRegion->rdh.nCount * sizeof(RECT)" in code[partition:read],
        "partitionRects[i] = {part.left, part.top, part.right, part.bottom};" in code[read:cover],
        "(boundedPartition &&" in code[read:cover],
        "(!outputNow.hasDirtyRegion || fullDirtyCoverage)" in code[writable:gpu],
        "GameNativeDirtyRegionCoverage::covers_full_backbuffer(" in code[read:cover],
        "area > total - covered" in hdr,
        "r.left < p.right && p.left < r.right" in hdr,
        "r.top < p.bottom && p.top < r.bottom" in hdr,
        "covered == total" in hdr,
        "rectangleCount < 2u || rectangleCount > kMaxPartitionRects" in hdr,
    ))

assert integrated(SRC, HDR), "partitioned full D3D9 Present must enter safe native publication"
for old, new in (
    ("dirtyRegion->rdh.nCount <= GameNativeDirtyRegionCoverage::kMaxPartitionRects", "true /* unbounded */"),
    ("dirtyRegion->rdh.nRgnSize >= dirtyRegion->rdh.nCount * sizeof(RECT)", "true /* short RGNDATA */"),
    ("partitionRects[i] = {part.left, part.top, part.right, part.bottom};", "/* drop source rectangle */"),
    ("GameNativeDirtyRegionCoverage::covers_partition(", "/* skip proof */("),
    ("(!outputNow.hasDirtyRegion || fullDirtyCoverage)", "true /* no safe fallback */"),
):
    changed = SRC.replace(old, new, 1)
    assert changed != SRC and not integrated(changed, HDR), old
for old, new in (
    ("area > total - covered", "false /* allow excess */"),
    ("r.left < p.right && p.left < r.right", "true /* ignore x overlap */"),
    ("r.top < p.bottom && p.top < r.bottom", "true /* ignore y overlap */"),
    ("covered == total", "true /* holes allowed */"),
    ("rectangleCount < 2u || rectangleCount > kMaxPartitionRects", "false /* unlimited */"),
):
    changed = HDR.replace(old, new, 1)
    assert changed != HDR and not integrated(SRC, changed), old
assert "python tools/test_dx11_full_dirty_partition_00749.py" in WF
assert "tools/dx11_full_dirty_partition_probe_00749.cpp" in WF
print("00749 full-frame dirty partition integrated+negative source tests PASS")
