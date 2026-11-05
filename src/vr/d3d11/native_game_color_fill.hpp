#pragma once
#include <array>
#include <cstdint>
#include <limits>
namespace outrun::vr::dx11 {
// A full D3D9 ColorFill AFTER GPU geometry erases the scene's color,
// so the prior Draw count can no longer certify a published game frame.
// Until a retained per-pixel draw epoch is available, fail closed to the
// original D3D9 output instead of publishing a cleared DX11 scene.
[[nodiscard]] constexpr bool native_game_color_fill_retires_draw_batch(
    bool wholeSurface, bool nativeDrawAlreadySubmitted) noexcept {
    return wholeSurface && nativeDrawAlreadySubmitted;
}

// Convert an actual D3D9 ARGB color for either the live native RTV or one
// authored stereo-eye RTV. X8R8G8B8 has no alpha storage: D3D11 must seed
// an opaque destination alpha to preserve later DESTALPHA blending.
[[nodiscard]] constexpr std::array<float, 4> native_game_color_fill_rgba(
    std::uint32_t argb, bool opaqueDestinationAlpha) noexcept {
    constexpr float byteScale = 1.0f / 255.0f;
    return {
        static_cast<float>((argb >> 16u) & 255u) * byteScale,
        static_cast<float>((argb >> 8u) & 255u) * byteScale,
        static_cast<float>(argb & 255u) * byteScale,
        opaqueDestinationAlpha ? 1.0f :
            static_cast<float>((argb >> 24u) & 255u) * byteScale
    };
}
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
