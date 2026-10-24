#pragma once
#include <cstdint>
#include <limits>
namespace outrun::vr::dx11 {
// D3D9 ColorFill ignores source Draw viewport/scissor. Clip to target only.
struct NativeGameColorFillClip {
    bool valid{}, empty{}, full{};
    std::uint32_t left{}, top{}, right{}, bottom{};
};
[[nodiscard]] constexpr NativeGameColorFillClip native_game_color_fill_clip(
    std::uint32_t width,std::uint32_t height,bool hasRect,
    std::int64_t left=0,std::int64_t top=0,
    std::int64_t right=0,std::int64_t bottom=0) noexcept {
    if (!width || !height ||
        width>static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) ||
        height>static_cast<std::uint32_t>((std::numeric_limits<std::int32_t>::max)()) ||
        (hasRect && (right<left || bottom<top))) return {};
    if (!hasRect) return {true,false,true,0u,0u,width,height};
    const auto clamp=[](std::int64_t value,std::uint32_t bound) constexpr {
        return value<=0 ? 0u : value>=static_cast<std::int64_t>(bound)
            ? bound : static_cast<std::uint32_t>(value);
    };
    NativeGameColorFillClip out{};
    out.valid=true;
    out.left=clamp(left,width);out.top=clamp(top,height);
    out.right=clamp(right,width);out.bottom=clamp(bottom,height);
    out.empty=out.left>=out.right || out.top>=out.bottom;
    out.full=!out.empty && !out.left && !out.top &&
        out.right==width && out.bottom==height;
    return out;
}
static_assert(native_game_color_fill_clip(3440,1440,false).full);
static_assert(native_game_color_fill_clip(3440,1440,true,-5,-5,3500,1500).full);
static_assert(native_game_color_fill_clip(3440,1440,true,3500,0,3600,100).empty);
static_assert(!native_game_color_fill_clip(3440,1440,true,100,0,10,100).valid);
} // namespace outrun::vr::dx11
