#!/usr/bin/env python3
"""01065: real game camera GPU postpass must sample typed float4 color in BOTH eyes."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_game_typed_camera_postpass.hpp").read_text()
source = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()

def integrated(h, s):
    family = h.split("constexpr bool native_game_float4_camera_sample_format(", 1)[1].split(
        "static_assert(native_game_float4_camera_sample_format", 1)[0]
    choose = h.split("constexpr DXGI_FORMAT native_game_typed_camera_shader_format(", 1)[1].split(
        "static_assert(native_game_typed_camera_shader_format(", 1)[0]
    actual = s.split("bool NativeGameEyeDrawEncoder::stretch_game_surface(", 1)[1].split(
        "void NativeGameStereoSubmission::release_local()", 1)[0]
    preflight = s.split("bool preflight_game_camera_shader_postpass(", 1)[1].split(
        "bool NativeGameStereoSubmission::render_game_eye_passes(", 1)[0]
    return all((
        "DXGI_FORMAT_R8G8B8A8_UINT" not in family.split("return true;", 1)[0],
        "DXGI_FORMAT_R8G8B8A8_SINT" not in family.split("return true;", 1)[0],
        "DXGI_FORMAT_D32_FLOAT" not in family.split("return true;", 1)[0],
        "DXGI_FORMAT_NV12" not in family.split("return true;", 1)[0],
        "DXGI_FORMAT_R8G8B8A8_UNORM_SRGB" in family,
        "DXGI_FORMAT_R16G16B16A16_FLOAT" in family,
        "return native_game_float4_camera_sample_format(allocation)" in choose,
        "? allocation : DXGI_FORMAT_UNKNOWN;" in choose,
        "if (sampleFormat == DXGI_FORMAT_UNKNOWN) return false;" in actual,
        "D3D11_FORMAT_SUPPORT_TEXTURE2D" in actual,
        "context_->Draw(3u, 0u);" in actual,
        "native_game_typed_camera_preflight_formats(" in preflight,
        "eyeRequired = D3D11_FORMAT_SUPPORT_RENDER_TARGET |" in preflight,
        "D3D11_FORMAT_SUPPORT_TEXTURE2D" in preflight,
        "D3D11_FORMAT_SUPPORT_SHADER_SAMPLE |" in preflight,
        "if (transfer != NativeGameStretchSourceTransfer::Reject)" in preflight,
        "RUNTIME_VALIDATION=UNTESTED" not in actual,
    ))

assert integrated(header, source)
# Negative mutations prove that both actual shader replay and preflight
# cannot silently drop their texture format gate.
for needle in ("return native_game_float4_camera_sample_format(allocation)",
               "DXGI_FORMAT_R16G16B16A16_FLOAT:"):
    assert needle in header
    assert not integrated(header.replace(needle, "/* unsafe format path */", 1), source)
for needle in ("(sourceSupport & D3D11_FORMAT_SUPPORT_TEXTURE2D) == 0u",
               "eyeRequired = D3D11_FORMAT_SUPPORT_RENDER_TARGET |",
               "D3D11_FORMAT_SUPPORT_SHADER_SAMPLE |"):
    assert needle in source
    assert not integrated(header, source.replace(needle, "/* format coverage missing */", 1))
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
assert "python tools/test_dx11_native_float_camera_postpass_01065.py" in workflow
print("PASS 01065 native game float4 shader camera typed color and both-eye GPU preflight")
