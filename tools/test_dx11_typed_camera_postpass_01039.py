#!/usr/bin/env python3
"""01039: camera GPU Draw/Clear typed RTV -> actual stereo postpass SRV path."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
hdr = (root / "src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
typed = (root / "src/vr/d3d11/native_game_typed_camera_postpass.hpp").read_text()
assert "remember_offscreen_color_region(\n        texture.Get(), view.arraySlice, view.mip, vd.Format, region)" in cpp
assert "viewDesc.Format, filled)" in cpp
assert "record.renderedViewFormat = renderedViewFormat;" in cpp
assert "first.renderedViewFormat = record.renderedViewFormat;" in cpp
assert "next.renderedViewFormat = record.renderedViewFormat;" in cpp
assert "prior.renderedViewFormat != renderedViewFormat" in cpp
assert "offscreen_color_view_format(source, sourceArraySlice, sourceMipSlice)" in cpp
assert "CheckFormatSupport(sampleFormat, &sourceSupport)" in cpp
assert "desc.Format = sampleFormat;" in cpp
assert "typedView.Format = sampleFormat;" in cpp
assert "sampled.Get(), 0u, source, sourceSubresource, sampleFormat)" in cpp
assert "renderedViewFormat{DXGI_FORMAT_UNKNOWN}" in hdr
for name in ["R8G8B8A8_TYPELESS", "B8G8R8A8_TYPELESS",
             "R16G16B16A16_TYPELESS", "R32_TYPELESS"]:
    assert name in typed
assert "DXGI_FORMAT_R8G8B8A8_UINT) ==" in typed
assert "DXGI_FORMAT_D32_FLOAT) ==" in typed
print("01039 typed camera RTV -> GPU SRV/Resolve source graph PASS")
