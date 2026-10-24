#pragma once
#include <dxgiformat.h>

namespace outrun::vr::dx11 {

// Pixel shader float4 Clear for real D3D9 game camera/HUD RTVs.
// Integer targets need a uint/sint output shader, typeless storage needs
// an explicit typed RTV, and depth/stencil must never be treated as color.
// Actual device CheckFormatSupport(RENDER_TARGET) remains mandatory.
[[nodiscard]] constexpr bool native_game_partial_color_shader_format(
    DXGI_FORMAT format) noexcept {
    switch (format) {
    case DXGI_FORMAT_R8G8B8A8_UNORM:
    case DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:
    case DXGI_FORMAT_R8G8B8A8_SNORM:
    case DXGI_FORMAT_B8G8R8A8_UNORM:
    case DXGI_FORMAT_B8G8R8A8_UNORM_SRGB:
    case DXGI_FORMAT_B8G8R8X8_UNORM:
    case DXGI_FORMAT_B8G8R8X8_UNORM_SRGB:
    case DXGI_FORMAT_R10G10B10A2_UNORM:
    case DXGI_FORMAT_R16G16B16A16_UNORM:
    case DXGI_FORMAT_R16G16B16A16_SNORM:
    case DXGI_FORMAT_R16G16B16A16_FLOAT:
    case DXGI_FORMAT_R32G32B32A32_FLOAT:
    case DXGI_FORMAT_R11G11B10_FLOAT:
    case DXGI_FORMAT_R32G32_FLOAT:
    case DXGI_FORMAT_R16G16_FLOAT:
    case DXGI_FORMAT_R16G16_UNORM:
    case DXGI_FORMAT_R16G16_SNORM:
    case DXGI_FORMAT_R8G8_UNORM:
    case DXGI_FORMAT_R8G8_SNORM:
    case DXGI_FORMAT_R32_FLOAT:
    case DXGI_FORMAT_R16_FLOAT:
    case DXGI_FORMAT_R16_UNORM:
    case DXGI_FORMAT_R16_SNORM:
    case DXGI_FORMAT_R8_UNORM:
    case DXGI_FORMAT_R8_SNORM:
    case DXGI_FORMAT_A8_UNORM:
    case DXGI_FORMAT_B5G6R5_UNORM:
    case DXGI_FORMAT_B5G5R5A1_UNORM:
        return true;
    default:
        return false;
    }
}
static_assert(native_game_partial_color_shader_format(DXGI_FORMAT_R8_UNORM));
static_assert(native_game_partial_color_shader_format(DXGI_FORMAT_R16G16_FLOAT));
static_assert(native_game_partial_color_shader_format(DXGI_FORMAT_R32G32B32A32_FLOAT));
static_assert(native_game_partial_color_shader_format(DXGI_FORMAT_R8G8B8A8_UNORM_SRGB));
static_assert(native_game_partial_color_shader_format(DXGI_FORMAT_B8G8R8A8_UNORM));
static_assert(!native_game_partial_color_shader_format(DXGI_FORMAT_R8G8B8A8_UINT));
static_assert(!native_game_partial_color_shader_format(DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS));
static_assert(!native_game_partial_color_shader_format(DXGI_FORMAT_D24_UNORM_S8_UINT));
static_assert(!native_game_partial_color_shader_format(DXGI_FORMAT_R16G16B16A16_TYPELESS));
} // namespace outrun::vr::dx11
