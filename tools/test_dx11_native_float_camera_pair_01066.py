#!/usr/bin/env python3
"""01066: FLOAT32 live-game two/three-channel RTs reach authentic stereo GPU postpass."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_game_typed_camera_postpass.hpp").read_text()
stereo = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(h, s):
    typed = h.split("constexpr DXGI_FORMAT native_game_typed_camera_shader_format(", 1)[1].split(
        "static_assert(native_game_typed_camera_shader_format(", 1)[0]
    preflight_formats = h.split("native_game_typed_camera_preflight_formats(DXGI_FORMAT allocation)", 1)[1].split(
        "static_assert(native_game_typed_camera_preflight_formats(", 1)[0]
    choose = h.split("constexpr NativeGameCameraCopyRoute native_game_camera_copy_route(", 1)[1].split(
        "static_assert(native_game_camera_copy_route(", 1)[0]
    shader_copy = s.split("bool NativeGameEyeDrawEncoder::stretch_game_surface(", 1)[1].split(
        "void NativeGameStereoSubmission::release_local()", 1)[0]
    before_eye = s.split("bool preflight_game_camera_shader_postpass(", 1)[1].split(
        "bool NativeGameStereoSubmission::render_game_eye_passes(", 1)[0]
    both_eye = s.split("bool NativeGameStereoSubmission::render_game_eye_passes(", 1)[1].split(
        "bool NativeGameStereoSubmission::try_publish(", 1)[0]
    return all((
        "case DXGI_FORMAT_R32G32_TYPELESS:" in typed,
        "renderedView == DXGI_FORMAT_R32G32_FLOAT" in typed,
        "case DXGI_FORMAT_R32G32B32_TYPELESS:" in typed,
        "renderedView == DXGI_FORMAT_R32G32B32_FLOAT" in typed,
        "case F::DXGI_FORMAT_R32G32_TYPELESS:" in preflight_formats,
        "case F::DXGI_FORMAT_R32G32B32_TYPELESS:" in preflight_formats,
        "native_game_typed_camera_shader_format(allocation, observedView)" in choose,
        "offscreen_color_view_format(source, sourceArraySlice, sourceMipSlice)" in shader_copy,
        "native_game_typed_camera_shader_format(" in shader_copy,
        "context_->Draw(3u, 0u);" in shader_copy,
        "native_game_typed_camera_preflight_formats(" in before_eye,
        "D3D11_FORMAT_SUPPORT_SHADER_SAMPLE" in before_eye,
        "for (std::uint32_t eye = 0u; eye < 2u; ++eye)" in both_eye,
        "NativeGameEyeDrawEncoder encoder(" in both_eye,
        "RUNTIME_VALIDATION=UNTESTED" not in shader_copy,
    ))

assert integrated(header, stereo)
for needle in (
    "case DXGI_FORMAT_R32G32_TYPELESS:",
    "renderedView == DXGI_FORMAT_R32G32B32_FLOAT",
    "case F::DXGI_FORMAT_R32G32_TYPELESS:",
    "case F::DXGI_FORMAT_R32G32B32_TYPELESS:",
):
    mutant = header.replace(needle, "/* omit real float RTV route */")
    assert mutant != header and not integrated(mutant, stereo), needle
for needle in (
    "offscreen_color_view_format(source, sourceArraySlice, sourceMipSlice)",
    "context_->Draw(3u, 0u);",
    "for (std::uint32_t eye = 0u; eye < 2u; ++eye)",
):
    mutant = stereo.replace(needle, "/* remove source and eye GPU link */")
    assert mutant != stereo and not integrated(header, mutant), needle
assert "python tools/test_dx11_native_float_camera_pair_01066.py" in workflow
print("PASS 01066 typed FLOAT32 2/3-channel real camera RTV through both-eye GPU sampling")
