#pragma once
#include <cstdint>

namespace outrun::vr::dx11 {
// Admission for each *additional* genuine game camera color attachment.
// RT1..RT7 may be bound during a real menu/car/race offscreen Draw; they are
// not OpenXR eye targets. All attachments must be private, same-device,
// same raster extent/sample mode. Never import a shared eye or foreign RT.
[[nodiscard]] constexpr bool native_game_offscreen_mrt_slot_compatible(
    std::uint32_t primaryWidth, std::uint32_t primaryHeight,
    std::uint32_t primarySamples, std::uint32_t primaryQuality,
    std::uint32_t otherWidth, std::uint32_t otherHeight,
    std::uint32_t otherSamples, std::uint32_t otherQuality,
    bool localDefaultRenderTarget, bool sameDevice,
    bool distinctFromEyeAndDepth) noexcept {
    return primaryWidth != 0u && primaryHeight != 0u &&
        primarySamples != 0u && primarySamples <= 32u &&
        primaryWidth == otherWidth && primaryHeight == otherHeight &&
        primarySamples == otherSamples && primaryQuality == otherQuality &&
        localDefaultRenderTarget && sameDevice && distinctFromEyeAndDepth;
}
static_assert(native_game_offscreen_mrt_slot_compatible(
    1920,1080,1,0,1920,1080,1,0,true,true,true));
static_assert(native_game_offscreen_mrt_slot_compatible(
    1280,720,4,0,1280,720,4,0,true,true,true));
static_assert(!native_game_offscreen_mrt_slot_compatible(
    1920,1080,1,0,256,144,1,0,true,true,true));
static_assert(!native_game_offscreen_mrt_slot_compatible(
    1920,1080,1,0,1920,1080,1,0,false,true,true));
static_assert(!native_game_offscreen_mrt_slot_compatible(
    1920,1080,1,0,1920,1080,1,0,true,false,true));
static_assert(!native_game_offscreen_mrt_slot_compatible(
    1920,1080,1,0,1920,1080,1,0,true,true,false));
} // namespace outrun::vr::dx11
