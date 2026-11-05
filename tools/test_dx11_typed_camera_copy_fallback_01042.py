#!/usr/bin/env python3
"""01042: live camera SourceCopy chooses GPU Copy/Resolve or shader conversion."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_game_typed_camera_postpass.hpp").read_text()
cpp = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
copy_start = cpp.index("bool NativeGameEyeDrawEncoder::copy_game_surface(")
copy_end = cpp.index("// The D3D9 game and native OpenXR path", copy_start)
copy = cpp[copy_start:copy_end]
pre_start = cpp.index("bool NativeGameStereoSubmission::render_game_eye_passes(")
pre_end = cpp.index("// The shared-eye ring owns", pre_start)
preflight = cpp[pre_start:pre_end]

for token in (
    "native_game_camera_copy_needs_shader_fallback(",
    "native_game_camera_copy_route(",
    "NativeGameCameraCopyRoute::DirectGpuCopy",
    "NativeGameCameraCopyRoute::ShaderConvert",
    "NativeGameCameraCopyRoute::Reject",
    "DXGI_FORMAT_B8G8R8A8_UNORM_SRGB",
    "DXGI_FORMAT_R24G8_TYPELESS",
):
    assert token in header, token
assert "const DXGI_FORMAT observedCameraView = offscreen_color_view_format(" in copy
assert "native_game_camera_copy_route(" in copy
assert "copyRoute == NativeGameCameraCopyRoute::Reject" in copy
assert "copyRoute == NativeGameCameraCopyRoute::ShaderConvert" in copy
assert "stretch_game_surface(" in copy
assert "rawTypedCameraCopy ? eyeDesc.Format : sourceDesc.Format" in copy
assert "context_->CopySubresourceRegion(" in copy
assert "context_->ResolveSubresource(" in copy
assert "native_game_camera_copy_needs_shader_fallback(" in preflight
assert "needsPostpassShader = true" in preflight
assert "preflight_game_camera_shader_postpass(" in preflight
assert 'LoadLibraryW(L"d3dcompiler_47.dll")' in preflight
assert "if (needsPostpassShader)" in preflight
assert "producer.Get() != sourceOwner.Get()" in preflight
assert "native_game_copy_clipped_region(" in preflight
assert "offscreen_color_source_proven(" in cpp
assert "offscreenColorProvenance_.allows_postpass(" in cpp
print("01042 game camera typed GPU Copy/Resolve -> shader fallback PASS")
