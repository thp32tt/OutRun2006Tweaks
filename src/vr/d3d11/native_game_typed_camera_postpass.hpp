#pragma once
#include <dxgiformat.h>
#include <array>

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

    
// A TYPELESS allocation can have multiple *legal* RTV interpretations.
// Preflight runs before the real per-eye camera Draw/Clear has provided its
// typed RTV provenance, so it may only validate whether a compatible typed
// GPU sample path exists. The encoder later requires the EXACT observed RTV
// format from that eye/mip; this list alone never authenticates camera color.
[[nodiscard]] constexpr std::array<DXGI_FORMAT, 3u>
native_game_typed_camera_preflight_formats(DXGI_FORMAT allocation) noexcept {
    using F = DXGI_FORMAT;
    switch (allocation) {
    case F::DXGI_FORMAT_R8G8B8A8_TYPELESS:
        return {F::DXGI_FORMAT_R8G8B8A8_UNORM,
                F::DXGI_FORMAT_R8G8B8A8_UNORM_SRGB, F::DXGI_FORMAT_UNKNOWN};
    case F::DXGI_FORMAT_B8G8R8A8_TYPELESS:
        return {F::DXGI_FORMAT_B8G8R8A8_UNORM,
                F::DXGI_FORMAT_B8G8R8A8_UNORM_SRGB, F::DXGI_FORMAT_UNKNOWN};
    case F::DXGI_FORMAT_B8G8R8X8_TYPELESS:
        return {F::DXGI_FORMAT_B8G8R8X8_UNORM,
                F::DXGI_FORMAT_B8G8R8X8_UNORM_SRGB, F::DXGI_FORMAT_UNKNOWN};
    case F::DXGI_FORMAT_R16G16B16A16_TYPELESS:
        return {F::DXGI_FORMAT_R16G16B16A16_FLOAT,
                F::DXGI_FORMAT_R16G16B16A16_UNORM,
                F::DXGI_FORMAT_R16G16B16A16_SNORM};
    case F::DXGI_FORMAT_R10G10B10A2_TYPELESS:
        return {F::DXGI_FORMAT_R10G10B10A2_UNORM,
                F::DXGI_FORMAT_UNKNOWN, F::DXGI_FORMAT_UNKNOWN};
    case F::DXGI_FORMAT_R16G16_TYPELESS:
        return {F::DXGI_FORMAT_R16G16_FLOAT,
                F::DXGI_FORMAT_R16G16_UNORM,
                F::DXGI_FORMAT_R16G16_SNORM};
    case F::DXGI_FORMAT_R32G32B32A32_TYPELESS:
        return {F::DXGI_FORMAT_R32G32B32A32_FLOAT,
                F::DXGI_FORMAT_UNKNOWN, F::DXGI_FORMAT_UNKNOWN};
    case F::DXGI_FORMAT_R8G8_TYPELESS:
        return {F::DXGI_FORMAT_R8G8_UNORM, F::DXGI_FORMAT_R8G8_SNORM,
                F::DXGI_FORMAT_UNKNOWN};
    case F::DXGI_FORMAT_R8_TYPELESS:
        return {F::DXGI_FORMAT_R8_UNORM, F::DXGI_FORMAT_R8_SNORM,
                F::DXGI_FORMAT_UNKNOWN};
    case F::DXGI_FORMAT_R16_TYPELESS:
        return {F::DXGI_FORMAT_R16_FLOAT, F::DXGI_FORMAT_R16_UNORM,
                F::DXGI_FORMAT_R16_SNORM};
    case F::DXGI_FORMAT_R32_TYPELESS:
        return {F::DXGI_FORMAT_R32_FLOAT,
                F::DXGI_FORMAT_UNKNOWN, F::DXGI_FORMAT_UNKNOWN};
    default:
        // Typed camera textures retain their original interpretation.
        // Unknown/depth/BC typeless families may not be guessed as color.
        return native_game_typed_camera_shader_format(
            allocation, F::DXGI_FORMAT_UNKNOWN) == F::DXGI_FORMAT_UNKNOWN
            ? std::array<F, 3u>{F::DXGI_FORMAT_UNKNOWN,
                                 F::DXGI_FORMAT_UNKNOWN, F::DXGI_FORMAT_UNKNOWN}
            : std::array<F, 3u>{allocation, F::DXGI_FORMAT_UNKNOWN,
                                 F::DXGI_FORMAT_UNKNOWN};
    }
}
static_assert(native_game_typed_camera_preflight_formats(
    DXGI_FORMAT_B8G8R8A8_TYPELESS)[1] ==
    DXGI_FORMAT_B8G8R8A8_UNORM_SRGB);
static_assert(native_game_typed_camera_preflight_formats(
    DXGI_FORMAT_R16G16B16A16_TYPELESS)[2] ==
    DXGI_FORMAT_R16G16B16A16_SNORM);
static_assert(native_game_typed_camera_preflight_formats(
    DXGI_FORMAT_R32_TYPELESS)[0] == DXGI_FORMAT_R32_FLOAT);
static_assert(native_game_typed_camera_preflight_formats(
    DXGI_FORMAT_R24G8_TYPELESS)[0] == DXGI_FORMAT_UNKNOWN);
static_assert(native_game_typed_camera_preflight_formats(
    DXGI_FORMAT_BC1_TYPELESS)[0] == DXGI_FORMAT_UNKNOWN);
static_assert(native_game_typed_camera_preflight_formats(
    DXGI_FORMAT_R8G8B8A8_UNORM)[0] == DXGI_FORMAT_R8G8B8A8_UNORM);

} // namespace outrun::vr::dx11
