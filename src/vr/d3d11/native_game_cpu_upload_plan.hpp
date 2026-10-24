#pragma once
#include <cstdint>
#include "native_game_present_region.hpp"
namespace outrun::vr::dx11::live_game_frame {
// Exact backbuffer region that UpdateSurface can partially overwrite.
struct NativeGameCpuUploadPlan {
    GameNativePresentRegion region{};
    bool valid = false;
    [[nodiscard]] static constexpr NativeGameCpuUploadPlan select(
        std::uint32_t width, std::uint32_t height,
        bool cropped, bool partial, bool multi,
        GameNativePresentRegion present, GameNativePresentRegion dirty,
        GameNativePresentRegion multiBounds) noexcept {
        if (!present.full_frame_placement(width,height,width,height).valid ||
            unsigned(cropped) + unsigned(partial) + unsigned(multi) > 1u)
            return {};
        const GameNativePresentRegion whole{0,0,width,height};
        const GameNativePresentRegion affected = multi ? multiBounds :
            partial ? dirty : cropped ? present : whole;
        if (!affected.full_frame_placement(width,height,width,height).valid ||
            affected.left < present.left || affected.top < present.top ||
            affected.right > present.right || affected.bottom > present.bottom)
            return {};
        return {affected,true};
    }
};
} // namespace outrun::vr::dx11::live_game_frame
