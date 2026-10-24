#pragma once
#include <dxgiformat.h>

namespace outrun::vr::dx11 {
// A real D3D9 camera can be backed by a DXGI TYPELESS allocation whose
// native D3D11 RTV uses a specific float/UNORM color interpretation.
// Reuse ONLY that observed RTV interpretation when the GPU postpass later
// samples the exact source mip/array. Never reinterpret integer/depth pixels
// as float4 or infer a view for an unobserved camera.
[[nodiscard]] constexpr DXGI_FORMAT native_game_typed_camera_shader_format(
    DXGI_FORMAT allocation, DXGI_FORMAT renderedView) noexcept {
    if (allocation == DXGI_FORMAT_UNKNOWN) return DXGI_FORMAT_UNKNOWN;
    if (allocation == renderedView) return allocation;
    switch (allocation) {
    case DXGI_FORMAT_R8G8B8A8_TYPELESS:
        return renderedView == DXGI_FORMAT_R8G8B8A8_UNORM ||
               renderedView == DXGI_FORMAT_R8G8B8A8_UNORM_SRGB
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_B8G8R8A8_TYPELESS:
        return renderedView == DXGI_FORMAT_B8G8R8A8_UNORM ||
               renderedView == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_B8G8R8X8_TYPELESS:
        return renderedView == DXGI_FORMAT_B8G8R8X8_UNORM ||
               renderedView == DXGI_FORMAT_B8G8R8X8_UNORM_SRGB
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R16G16B16A16_TYPELESS:
        return renderedView == DXGI_FORMAT_R16G16B16A16_FLOAT ||
               renderedView == DXGI_FORMAT_R16G16B16A16_UNORM ||
               renderedView == DXGI_FORMAT_R16G16B16A16_SNORM
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R10G10B10A2_TYPELESS:
        return renderedView == DXGI_FORMAT_R10G10B10A2_UNORM
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R16G16_TYPELESS:
        return renderedView == DXGI_FORMAT_R16G16_FLOAT ||
               renderedView == DXGI_FORMAT_R16G16_UNORM ||
               renderedView == DXGI_FORMAT_R16G16_SNORM
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R32G32B32A32_TYPELESS:
        return renderedView == DXGI_FORMAT_R32G32B32A32_FLOAT
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R8G8_TYPELESS:
        return renderedView == DXGI_FORMAT_R8G8_UNORM ||
               renderedView == DXGI_FORMAT_R8G8_SNORM
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R8_TYPELESS:
        return renderedView == DXGI_FORMAT_R8_UNORM ||
               renderedView == DXGI_FORMAT_R8_SNORM
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R16_TYPELESS:
        return renderedView == DXGI_FORMAT_R16_FLOAT ||
               renderedView == DXGI_FORMAT_R16_UNORM ||
               renderedView == DXGI_FORMAT_R16_SNORM
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    case DXGI_FORMAT_R32_TYPELESS:
        return renderedView == DXGI_FORMAT_R32_FLOAT
            ? renderedView : DXGI_FORMAT_UNKNOWN;
    // Unhandled typeless families are never implicitly shader-readable.
    case DXGI_FORMAT_R32G32B32_TYPELESS:
    case DXGI_FORMAT_R32G32_TYPELESS:
    case DXGI_FORMAT_R32G8X24_TYPELESS:
    case DXGI_FORMAT_R24G8_TYPELESS:
    case DXGI_FORMAT_BC1_TYPELESS:
    case DXGI_FORMAT_BC2_TYPELESS:
    case DXGI_FORMAT_BC3_TYPELESS:
    case DXGI_FORMAT_BC4_TYPELESS:
    case DXGI_FORMAT_BC5_TYPELESS:
    case DXGI_FORMAT_BC6H_TYPELESS:
    case DXGI_FORMAT_BC7_TYPELESS:
        return DXGI_FORMAT_UNKNOWN;
    default:
        // Typed GPU copy/SRV/compute intermediates need no prior RTV
        // color evidence. Keep the original native postpass fast path.
        return allocation;
    }
}
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UNORM) ==
    DXGI_FORMAT_R8G8B8A8_UNORM);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R16G16B16A16_TYPELESS, DXGI_FORMAT_R16G16B16A16_FLOAT) ==
    DXGI_FORMAT_R16G16B16A16_FLOAT);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_B8G8R8A8_TYPELESS, DXGI_FORMAT_B8G8R8A8_UNORM_SRGB) ==
    DXGI_FORMAT_B8G8R8A8_UNORM_SRGB);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UINT) ==
    DXGI_FORMAT_UNKNOWN);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_B8G8R8A8_UNORM) ==
    DXGI_FORMAT_UNKNOWN);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R32_TYPELESS, DXGI_FORMAT_D32_FLOAT) ==
    DXGI_FORMAT_UNKNOWN);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_UNKNOWN) ==
    DXGI_FORMAT_UNKNOWN);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R8G8B8A8_UNORM, DXGI_FORMAT_UNKNOWN) ==
    DXGI_FORMAT_R8G8B8A8_UNORM);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_BC1_TYPELESS, DXGI_FORMAT_UNKNOWN) ==
    DXGI_FORMAT_UNKNOWN);
} // namespace outrun::vr::dx11
