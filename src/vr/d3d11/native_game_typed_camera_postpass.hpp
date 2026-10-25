#pragma once
#include <dxgiformat.h>
#include <array>

namespace outrun::vr::dx11 {
// A real D3D9 camera can be backed by a DXGI TYPELESS allocation whose
// native D3D11 RTV uses a specific float/UNORM color interpretation.
// Reuse ONLY that observed RTV interpretation when the GPU postpass later
// samples the exact source mip/array. Never reinterpret integer/depth pixels
// as float4 or infer a view for an unobserved camera.
// The GPU game postpass uses Texture2D<float4>, not an integer or depth
// Texture2D. A typed UINT/SINT, depth, video or block-compressed allocation
// cannot be silently fed into that pixel shader merely because it advertises
// generic DXGI SHADER_SAMPLE support. Preserve the real game's D3D9 output
// rather than publish a blank/wrong-colored native menu/race eye.
[[nodiscard]] constexpr bool native_game_float4_camera_sample_format(
    DXGI_FORMAT format) noexcept {
    switch (format) {
    case DXGI_FORMAT_R32G32B32A32_FLOAT:
    case DXGI_FORMAT_R32G32B32_FLOAT:
    case DXGI_FORMAT_R32G32_FLOAT:
    case DXGI_FORMAT_R32_FLOAT:
    case DXGI_FORMAT_R16G16B16A16_FLOAT:
    case DXGI_FORMAT_R16G16B16A16_UNORM:
    case DXGI_FORMAT_R16G16B16A16_SNORM:
    case DXGI_FORMAT_R16G16_FLOAT:
    case DXGI_FORMAT_R16G16_UNORM:
    case DXGI_FORMAT_R16G16_SNORM:
    case DXGI_FORMAT_R16_FLOAT:
    case DXGI_FORMAT_R16_UNORM:
    case DXGI_FORMAT_R16_SNORM:
    case DXGI_FORMAT_R11G11B10_FLOAT:
    case DXGI_FORMAT_R10G10B10A2_UNORM:
    case DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM:
    case DXGI_FORMAT_R9G9B9E5_SHAREDEXP:
    case DXGI_FORMAT_R8G8B8A8_UNORM:
    case DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:
    case DXGI_FORMAT_R8G8B8A8_SNORM:
    case DXGI_FORMAT_R8G8_UNORM:
    case DXGI_FORMAT_R8G8_SNORM:
    case DXGI_FORMAT_R8_UNORM:
    case DXGI_FORMAT_R8_SNORM:
    case DXGI_FORMAT_B8G8R8A8_UNORM:
    case DXGI_FORMAT_B8G8R8A8_UNORM_SRGB:
    case DXGI_FORMAT_B8G8R8X8_UNORM:
    case DXGI_FORMAT_B8G8R8X8_UNORM_SRGB:
    case DXGI_FORMAT_B5G6R5_UNORM:
    case DXGI_FORMAT_B5G5R5A1_UNORM:
    case DXGI_FORMAT_B4G4R4A4_UNORM:
        return true;
    default:
        return false;
    }
}
static_assert(native_game_float4_camera_sample_format(DXGI_FORMAT_B8G8R8A8_UNORM));
static_assert(native_game_float4_camera_sample_format(DXGI_FORMAT_R16G16B16A16_FLOAT));
static_assert(!native_game_float4_camera_sample_format(DXGI_FORMAT_R8G8B8A8_UINT));
static_assert(!native_game_float4_camera_sample_format(DXGI_FORMAT_R8G8B8A8_SINT));
static_assert(!native_game_float4_camera_sample_format(DXGI_FORMAT_D32_FLOAT));
static_assert(!native_game_float4_camera_sample_format(DXGI_FORMAT_D24_UNORM_S8_UINT));
static_assert(!native_game_float4_camera_sample_format(DXGI_FORMAT_NV12));
static_assert(!native_game_float4_camera_sample_format(DXGI_FORMAT_BC1_UNORM));

[[nodiscard]] constexpr DXGI_FORMAT native_game_typed_camera_shader_format(
    DXGI_FORMAT allocation, DXGI_FORMAT renderedView) noexcept {
    if (allocation == DXGI_FORMAT_UNKNOWN) return DXGI_FORMAT_UNKNOWN;
    if (allocation == renderedView)
        return native_game_float4_camera_sample_format(allocation)
            ? allocation : DXGI_FORMAT_UNKNOWN;
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
        // Preserve sampled typed game-color intermediates, but never let
        // integer/depth/video formats masquerade as float4 camera color.
        return native_game_float4_camera_sample_format(allocation)
            ? allocation : DXGI_FORMAT_UNKNOWN;
    }
}
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_R8G8B8A8_UINT, DXGI_FORMAT_UNKNOWN) == DXGI_FORMAT_UNKNOWN);
static_assert(native_game_typed_camera_shader_format(
    DXGI_FORMAT_D32_FLOAT, DXGI_FORMAT_UNKNOWN) == DXGI_FORMAT_UNKNOWN);
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

 // A real TYPELESS camera may transfer raw color into a typed XR eye only
 // if its exact game Draw/Clear RTV view (physical mip/array) matches that eye.
 // This candidate helper is for BOTH-eye preflight, never pixel proof.
 [[nodiscard]] constexpr bool native_game_raw_camera_copy_candidate(
     DXGI_FORMAT allocation, DXGI_FORMAT eyeFormat) noexcept {
     if (eyeFormat == DXGI_FORMAT_UNKNOWN || allocation == eyeFormat)
         return false;
     for (const auto typed :
          native_game_typed_camera_preflight_formats(allocation))
         if (typed == eyeFormat &&
             native_game_typed_camera_shader_format(allocation, typed) == typed)
             return true;
     return false;
 }
 [[nodiscard]] constexpr bool native_game_raw_camera_copy_format(
     DXGI_FORMAT allocation, DXGI_FORMAT eyeFormat,
     DXGI_FORMAT observedView) noexcept {
     return observedView == eyeFormat &&
            native_game_raw_camera_copy_candidate(allocation, eyeFormat);
 }

 // The source game chooses the physical TYPELESS RTV during replay, AFTER
 // camera preflight. A candidate direct GPU Copy can therefore turn into a
 // GPU shader conversion when that Draw uses another legal color RTV.
 // Preflight both possible routes before either stereo eye queues a write.
 [[nodiscard]] constexpr bool native_game_camera_copy_needs_shader_fallback(
     DXGI_FORMAT allocation, DXGI_FORMAT eyeFormat) noexcept {
     if (!native_game_raw_camera_copy_candidate(allocation, eyeFormat))
         return false;
     for (const auto typed :
          native_game_typed_camera_preflight_formats(allocation))
         if (typed != DXGI_FORMAT_UNKNOWN && typed != eyeFormat &&
             native_game_typed_camera_shader_format(allocation, typed) == typed)
             return true;
     return false;
 }

 enum class NativeGameCameraCopyRoute {
     Reject, DirectGpuCopy, ShaderConvert
 };
 // Actual Copy/Resolve needs this eye's game-written mip/array RTV, not a
 // speculative preflight candidate. Nonmatching observed color views use
 // the existing GPU shader Stretch conversion (never CPU readback).
 [[nodiscard]] constexpr NativeGameCameraCopyRoute native_game_camera_copy_route(
     DXGI_FORMAT allocation, DXGI_FORMAT eyeFormat,
     DXGI_FORMAT observedView) noexcept {
     if (allocation == DXGI_FORMAT_UNKNOWN || eyeFormat == DXGI_FORMAT_UNKNOWN)
         return NativeGameCameraCopyRoute::Reject;
     if (allocation == eyeFormat ||
         native_game_raw_camera_copy_format(allocation, eyeFormat, observedView))
         return NativeGameCameraCopyRoute::DirectGpuCopy;
     return native_game_typed_camera_shader_format(allocation, observedView) !=
                    DXGI_FORMAT_UNKNOWN
         ? NativeGameCameraCopyRoute::ShaderConvert
         : NativeGameCameraCopyRoute::Reject;
 }
 static_assert(native_game_camera_copy_needs_shader_fallback(
     DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UNORM));
 static_assert(native_game_camera_copy_needs_shader_fallback(
     DXGI_FORMAT_R16G16B16A16_TYPELESS, DXGI_FORMAT_R16G16B16A16_FLOAT));
 static_assert(!native_game_camera_copy_needs_shader_fallback(
     DXGI_FORMAT_R10G10B10A2_TYPELESS, DXGI_FORMAT_R10G10B10A2_UNORM));
 static_assert(native_game_camera_copy_route(
     DXGI_FORMAT_B8G8R8A8_TYPELESS, DXGI_FORMAT_B8G8R8A8_UNORM,
     DXGI_FORMAT_B8G8R8A8_UNORM) == NativeGameCameraCopyRoute::DirectGpuCopy);
 static_assert(native_game_camera_copy_route(
     DXGI_FORMAT_B8G8R8A8_TYPELESS, DXGI_FORMAT_B8G8R8A8_UNORM,
     DXGI_FORMAT_B8G8R8A8_UNORM_SRGB) == NativeGameCameraCopyRoute::ShaderConvert);
 static_assert(native_game_camera_copy_route(
     DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UNORM,
     DXGI_FORMAT_UNKNOWN) == NativeGameCameraCopyRoute::Reject);
 static_assert(native_game_camera_copy_route(
     DXGI_FORMAT_R24G8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UNORM,
     DXGI_FORMAT_D24_UNORM_S8_UINT) == NativeGameCameraCopyRoute::Reject);
 static_assert(native_game_raw_camera_copy_candidate(
     DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UNORM));
 static_assert(native_game_raw_camera_copy_candidate(
     DXGI_FORMAT_R16G16B16A16_TYPELESS, DXGI_FORMAT_R16G16B16A16_FLOAT));
 static_assert(native_game_raw_camera_copy_format(
     DXGI_FORMAT_B8G8R8A8_TYPELESS, DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,
     DXGI_FORMAT_B8G8R8A8_UNORM_SRGB));
 static_assert(!native_game_raw_camera_copy_format(
     DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UNORM,
     DXGI_FORMAT_UNKNOWN));
 static_assert(!native_game_raw_camera_copy_format(
     DXGI_FORMAT_R8G8B8A8_TYPELESS, DXGI_FORMAT_R8G8B8A8_UNORM,
     DXGI_FORMAT_R8G8B8A8_UNORM_SRGB));
 static_assert(!native_game_raw_camera_copy_candidate(
     DXGI_FORMAT_R24G8_TYPELESS, DXGI_FORMAT_R24_UNORM_X8_TYPELESS));
 static_assert(!native_game_raw_camera_copy_candidate(
     DXGI_FORMAT_BC1_TYPELESS, DXGI_FORMAT_BC1_UNORM));
 static_assert(!native_game_raw_camera_copy_candidate(
     DXGI_FORMAT_R8G8B8A8_UINT, DXGI_FORMAT_R8G8B8A8_UNORM));

} // namespace outrun::vr::dx11
