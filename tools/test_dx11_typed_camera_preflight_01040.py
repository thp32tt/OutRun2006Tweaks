#!/usr/bin/env python3
"""01040: real game typed camera survives preflight; playback still proves view."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
hdr = (root / "src/vr/d3d11/native_game_typed_camera_postpass.hpp").read_text()
start = src.index("bool NativeGameStereoSubmission::render_game_eye_passes(")
preflight = src[start:src.index("// The shared-eye ring owns", start)]
assert preflight.count("preflight_game_camera_shader_postpass(") == 2
assert "native_game_typed_camera_preflight_formats(source.Format)" in src
assert "native_game_typed_camera_shader_format(source.Format, typed) != typed" in src
assert "CheckFormatSupport(typed, &formatSupport)" in src
assert "NativeGameStretchSourceTransfer::Reject" in src
assert "native_game_copy_clipped_region(" in preflight
assert "native_game_stretch_clipped_region(" in preflight
assert "!event.source" in preflight
assert "producer.Get() != sourceOwner.Get()" in preflight
assert "sourceMip.valid" in preflight
# Actual playback, not preflight's format-family enumeration, selects the
# observed game Draw/Clear RTV. Unknown/mixed views still fail closed.
assert "offscreen_color_view_format(source, sourceArraySlice, sourceMipSlice)" in src
assert "native_game_typed_camera_shader_format(" in src
assert "if (sampleFormat == DXGI_FORMAT_UNKNOWN) return false;" in src
assert "CheckFormatSupport(sampleFormat, &sourceSupport)" in src
for typeless, candidate in [
    ("R8G8B8A8_TYPELESS", "R8G8B8A8_UNORM_SRGB"),
    ("B8G8R8A8_TYPELESS", "B8G8R8A8_UNORM"),
    ("R16G16B16A16_TYPELESS", "R16G16B16A16_FLOAT"),
    ("R32_TYPELESS", "R32_FLOAT")]:
    assert "F::DXGI_FORMAT_" + typeless in hdr
    assert "F::DXGI_FORMAT_" + candidate in hdr
assert "DXGI_FORMAT_R24G8_TYPELESS)[0] == DXGI_FORMAT_UNKNOWN" in hdr
assert "DXGI_FORMAT_BC1_TYPELESS)[0] == DXGI_FORMAT_UNKNOWN" in hdr
print("01040 camera GPU preflight and observed typed RTV playback PASS")
