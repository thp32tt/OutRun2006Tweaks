#pragma once
// D3D9 INDEXEDDATA/INSTANCEDATA addressing for the game's original
// secondary VB shadows. This is source-slot planning, not GPU admission.
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
struct GameNativeInstanceStreamCapture {
    std::uint32_t sourceSlots = 0;
    bool instanceRate = false;
    bool valid = false;
};
[[nodiscard]] constexpr GameNativeInstanceStreamCapture
    game_native_instance_stream_capture(std::uint32_t streamZeroFrequency,
                                        std::uint32_t secondaryFrequency,
                                        std::uint32_t gameVertexSlots) noexcept {
    constexpr std::uint32_t kFlags = 0xc0000000u;
    constexpr std::uint32_t kCount = 0x3fffffffu;
    constexpr std::uint32_t kIndexedData = 0x40000000u;
    constexpr std::uint32_t kInstanceData = 0x80000000u;
    if (!gameVertexSlots) return {};
    const bool indexed = (streamZeroFrequency & kFlags) == kIndexedData &&
        (streamZeroFrequency & kCount) != 0u;
    if (!indexed && streamZeroFrequency != 1u) return {};
    // With no INSTANCEDATA flag, secondary attributes advance per source
    // vertex, retaining the same sparse order as stream zero.
    if (secondaryFrequency == 1u)
        return {gameVertexSlots, false, true};
    if (!indexed || (secondaryFrequency & kFlags) != kInstanceData ||
        (secondaryFrequency & kCount) == 0u)
        return {};
    const auto instances = streamZeroFrequency & kCount;
    const auto step = secondaryFrequency & kCount;
    // D3D9 per-instance stream addresses 0 .. ceil(instances / step)-1;
    // reusing the original vertex indices here reads the WRONG VB records.
    return {1u + (instances - 1u) / step, true, true};
}
} // namespace outrun::vr::dx11::live_game_frame
