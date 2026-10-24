#!/usr/bin/env python3
"""Live game-authored TYPELESS camera -> typed GPU Copy/Resolve eye path."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
hdr = (root / "src/vr/d3d11/native_game_typed_camera_postpass.hpp").read_text()
src = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
a = src[src.index("bool NativeGameEyeDrawEncoder::copy_game_surface("):
        src.index("// The D3D9 game and native OpenXR path")]
b = src[src.index("bool NativeGameStereoSubmission::render_game_eye_passes("):
        src.index("// The shared-eye ring owns")]
assert "native_game_raw_camera_copy_candidate(" in hdr
assert "native_game_raw_camera_copy_format(" in hdr
for neg in ("DXGI_FORMAT_UNKNOWN", "DXGI_FORMAT_R24G8_TYPELESS",
            "DXGI_FORMAT_BC1_TYPELESS", "DXGI_FORMAT_R8G8B8A8_UINT"):
    assert neg in hdr
assert "offscreen_color_view_format(" in a
assert "native_game_raw_camera_copy_format(" in a
assert "sourceDesc.Format != eyeDesc.Format && !rawTypedCameraCopy" in a
assert "if (rawTypedCameraCopy) resolvedDesc.Format = eyeDesc.Format" in a
assert "rawTypedCameraCopy ? eyeDesc.Format : sourceDesc.Format" in a
assert "context_->CopySubresourceRegion(" in a
assert "context_->ResolveSubresource(" in a
assert "ScopedNativePostpassOutputs restore{context_}" in a
assert "ScopedNativeGameGpuTransferInputs eyeCopyInputs" in a
assert "native_game_raw_camera_copy_candidate(" in b
assert "native_game_copy_clipped_region(" in b
assert "producer.Get() != sourceOwner.Get()" in b
assert "preflight_game_camera_shader_postpass(" in b
assert "offscreen_color_source_proven(" in src
assert "offscreenColorProvenance_.allows_postpass(" in src
print("01041 native typed game camera GPU Copy/Resolve + DX9Ex fallback PASS")
