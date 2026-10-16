#pragma once
#include <cstdint>

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
} // namespace outrun::vr::dx11
