#pragma once
#include <cstdint>
namespace outrun::vr::dx11::live_game_frame {
struct GameNativeGpuHandoff {
    // A fully rendered D3D11 game texture has its own GPU producer output.
    // D3D9 CPU UpdateSurface, backbuffer MSAA/format and dirty-region upload
    // restrictions apply ONLY to the optional desktop fallback. The native
    // copy sink can consume a complete real game frame even when those CPU
    // restrictions prohibit writing into the original D3D9 backbuffer.
    // Never use a synthetic inset, unknown output/crop, or stereo-suppressed
    // mono source to claim native frame publication.
    [[nodiscard]] static constexpr bool gpu_frame_output_ready(
        bool monoPublicationAllowed, bool outputKnown,
        bool nativeExtentMatches, bool fullPlacementValid) noexcept {
        return monoPublicationAllowed && outputKnown &&
               nativeExtentMatches && fullPlacementValid;
    }
    // Disallow partial game Draw coverage, foreign/cropped output, unbound
    // producer source, zero generation and inset-only diagnostic frames.
    [[nodiscard]] static constexpr bool may_offer(
        bool full, bool complete, bool writable, bool sameOwner,
        bool gpuReady, bool registered, std::uint32_t width,
        std::uint32_t height, std::uint32_t generation) noexcept {
        return full && complete && writable && sameOwner &&
            gpuReady && registered && width && height && generation;
    }
};
static_assert(GameNativeGpuHandoff::gpu_frame_output_ready(
    true,true,true,true));
static_assert(!GameNativeGpuHandoff::gpu_frame_output_ready(
    false,true,true,true));
static_assert(GameNativeGpuHandoff::may_offer(
    true,true,true,true,true,true,1920,1080,1));
static_assert(!GameNativeGpuHandoff::may_offer(
    false,true,true,true,true,true,256,144,1));
} // namespace outrun::vr::dx11::live_game_frame
