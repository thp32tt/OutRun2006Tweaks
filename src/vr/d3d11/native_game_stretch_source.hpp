#pragma once
#include <cstdint>
#include <array>

namespace outrun::vr::dx11 {

// Selection for an actual game-authored scaled/cropped GPU StretchRect.
// A texture postpass samples its source through an SRV and renders into the
// native eye RTV. Source and destination formats may differ: the D3D11
// shader performs their supported typed conversion during rasterization.
// Unsupported sources must leave the original D3D9 game path intact.
enum class NativeGameStretchSourceTransfer : std::uint8_t {
    Reject, DirectSample, CopyToSampled, ResolveToSampled
};

[[nodiscard]] constexpr NativeGameStretchSourceTransfer
native_game_stretch_source_transfer(
    std::uint32_t mipLevels, std::uint32_t sampleCount,
    std::uint32_t sampleQuality, bool sourceRenderTarget,
    bool sourceShaderResource, bool sourceSampleable,
    bool eyeRenderable, bool formatSupportsResolve) noexcept
{
    if (!mipLevels || !sampleCount || !sourceSampleable ||
        !eyeRenderable || (!sourceRenderTarget && !sourceShaderResource))
        return NativeGameStretchSourceTransfer::Reject;
    // D3D11 multisampled textures have exactly one mip, and only a
    // render-target source with format resolve support can be sampled as 2D.
    if (sampleCount > 1u) {
        return mipLevels == 1u && sourceRenderTarget &&
               formatSupportsResolve && sampleCount <= 32u
            ? NativeGameStretchSourceTransfer::ResolveToSampled
            : NativeGameStretchSourceTransfer::Reject;
    }
    if (sampleQuality != 0u)
        return NativeGameStretchSourceTransfer::Reject;
    return sourceShaderResource
        ? NativeGameStretchSourceTransfer::DirectSample
        : NativeGameStretchSourceTransfer::CopyToSampled;
}
// Region packing for the real menu/vehicle/race GPU postpass HLSL.
 // A cropped StretchRect samples only texels inside the game-authored box:
 // linear filtering at the first/last destination pixel must not bleed
 // neighbouring images from the source texture atlas.
struct NativeGameStretchUvRegion {
    std::array<float, 8> constants{}; // uvRegion.xyzw, uvClamp.xyzw
    bool valid{};
};
[[nodiscard]] constexpr NativeGameStretchUvRegion native_game_stretch_uv_region(
    std::uint32_t width, std::uint32_t height,
    std::uint32_t left, std::uint32_t top,
    std::uint32_t right, std::uint32_t bottom) noexcept {
    if (!width || !height || left >= right || top >= bottom ||
        right > width || bottom > height) return {};
    const float invW = 1.0f / static_cast<float>(width);
    const float invH = 1.0f / static_cast<float>(height);
    return {{
        float(left) * invW, float(top) * invH,
        float(right - left) * invW, float(bottom - top) * invH,
        (float(left) + 0.5f) * invW, (float(top) + 0.5f) * invH,
        (float(right) - 0.5f) * invW, (float(bottom) - 0.5f) * invH}, true};
}
} // namespace outrun::vr::dx11
