#pragma once
#include <cstdint>
#include <array>
#include <algorithm>
#include <limits>

namespace outrun::vr::dx11 {

// Selection for an actual game-authored scaled/cropped GPU StretchRect.
// A texture postpass samples its source through an SRV and renders into the
// native eye RTV. Source and destination formats may differ: the D3D11
// shader performs their supported typed conversion during rasterization.
// DEFAULT GPU CopyResource outputs with no bind flags can be copied to a
// private sampled texture without a CPU round-trip or changing game input.
// Unsupported sources must leave the original D3D9 game path intact.
enum class NativeGameStretchSourceTransfer : std::uint8_t {
    Reject, DirectSample, CopyToSampled, ResolveToSampled
};

[[nodiscard]] constexpr NativeGameStretchSourceTransfer
native_game_stretch_source_transfer(
    std::uint32_t mipLevels, std::uint32_t sampleCount,
    std::uint32_t sampleQuality, bool sourceRenderTarget,
    bool sourceShaderResource, bool sourceSampleable,
    bool eyeRenderable, bool formatSupportsResolve,
    bool sourceGpuCopyOnly = false) noexcept
{
    if (!mipLevels || !sampleCount || !sourceSampleable ||
        !eyeRenderable ||
        (!sourceRenderTarget && !sourceShaderResource && !sourceGpuCopyOnly))
        return NativeGameStretchSourceTransfer::Reject;
    // D3D11 multisampled textures have exactly one mip, and only a
    // render-target source with format resolve support can be sampled as 2D.
    if (sampleCount > 1u) {
        return mipLevels == 1u && sourceRenderTarget &&
               formatSupportsResolve && sampleCount <= 32u
            ? NativeGameStretchSourceTransfer::ResolveToSampled
            : NativeGameStretchSourceTransfer::Reject;
    }
    if (sampleQuality != 0u || (sourceGpuCopyOnly && sampleCount != 1u))
        return NativeGameStretchSourceTransfer::Reject;
    return sourceShaderResource
        ? NativeGameStretchSourceTransfer::DirectSample
        : NativeGameStretchSourceTransfer::CopyToSampled;
}
static_assert(native_game_stretch_source_transfer(
    1u, 1u, 0u, false, false, true, true, false, true) ==
    NativeGameStretchSourceTransfer::CopyToSampled);
static_assert(native_game_stretch_source_transfer(
    1u, 4u, 0u, false, false, true, true, true, true) ==
    NativeGameStretchSourceTransfer::Reject);
static_assert(native_game_stretch_source_transfer(
    1u, 1u, 0u, false, false, true, true, false) ==
    NativeGameStretchSourceTransfer::Reject);

// A game-authored GPU Copy/Stretch can use an RT/SRV, a single-sample
// compute UAV, or a DEFAULT copy-only texture with no bind flags. The last
// two cases require a private sampled D3D11 intermediate for format-converting
// point/linear postpasses; admitting them is NOT mono-to-stereo duplication.
// Source format/owner/mip/array/crop and MSAA resolve are checked separately.
[[nodiscard]] constexpr bool native_game_postpass_gpu_source(
    std::uint32_t flags, std::uint32_t samples,
    std::uint32_t rtv, std::uint32_t srv, std::uint32_t uav) noexcept {
    if (samples == 0u || samples > 32u) return false;
    if ((flags & (rtv | srv)) != 0u) return true;
    return samples == 1u && (flags == 0u || (flags & uav) != 0u);
}
static_assert(native_game_postpass_gpu_source(0u,1u,0x20u,0x8u,0x80u));
static_assert(native_game_postpass_gpu_source(0x80u,1u,0x20u,0x8u,0x80u));
static_assert(native_game_postpass_gpu_source(0x20u,4u,0x20u,0x8u,0x80u));
static_assert(!native_game_postpass_gpu_source(0u,4u,0x20u,0x8u,0x80u));
static_assert(!native_game_postpass_gpu_source(0x80u,8u,0x20u,0x8u,0x80u));
static_assert(!native_game_postpass_gpu_source(0u,0u,0x20u,0x8u,0x80u));
static_assert(!native_game_postpass_gpu_source(0x2u,1u,0x20u,0x8u,0x80u));

// A temporary GPU SRV or MSAA-resolve texture may be reused between
// sequential, ordered left/right game postpasses on the SAME immediate
// context. Device identity is verified by the caller; dimension, format and
// binding must also match. Never reuse a differently typed camera surface.
struct NativeGamePostpassScratchKey {
    std::uint32_t width{}, height{}, format{}, bindFlags{};
};
[[nodiscard]] constexpr bool native_game_postpass_scratch_matches(
    NativeGamePostpassScratchKey cached,
    NativeGamePostpassScratchKey requested) noexcept {
    return requested.width != 0u && requested.height != 0u &&
        cached.width == requested.width &&
        cached.height == requested.height &&
        cached.format == requested.format &&
        cached.bindFlags == requested.bindFlags;
}
static_assert(native_game_postpass_scratch_matches(
    {1920u, 1080u, 87u, 8u}, {1920u, 1080u, 87u, 8u}));
static_assert(!native_game_postpass_scratch_matches(
    {1920u, 1080u, 87u, 8u}, {1920u, 1080u, 87u, 0u}));

// Game-authored Copy/Resolve may start off the LEFT/TOP as well as extend
// beyond the RIGHT/BOTTOM edge during menu and car transitions. D3D11's
// destination is unsigned: move the source box by exactly the negative
// destination offset and emit a nonnegative eye destination. No scaling.
// Use signed 64-bit input so unsigned legacy callers cannot wrap to a
// plausible negative coordinate; reject fully invisible transfers.
struct NativeGameCopyClippedRegion {
    std::uint32_t sourceLeft{}, sourceTop{}, sourceRight{}, sourceBottom{};
    std::uint32_t destX{}, destY{};
    bool valid{};
};
[[nodiscard]] constexpr NativeGameCopyClippedRegion
native_game_copy_clipped_region(
    std::uint32_t sourceWidth, std::uint32_t sourceHeight,
    std::uint32_t sourceLeft, std::uint32_t sourceTop,
    std::uint32_t sourceRight, std::uint32_t sourceBottom,
    std::uint32_t targetWidth, std::uint32_t targetHeight,
    std::int64_t destX, std::int64_t destY) noexcept
{
    if (!sourceWidth || !sourceHeight || !targetWidth || !targetHeight ||
        sourceLeft >= sourceRight || sourceTop >= sourceBottom ||
        sourceRight > sourceWidth || sourceBottom > sourceHeight)
        return {};
    const std::uint32_t width = sourceRight - sourceLeft;
    const std::uint32_t height = sourceBottom - sourceTop;
    // Compare before negating to guard INT64_MIN, and before converting
    // an unsigned game coordinate back into an eye destination.
    if (destX <= -static_cast<std::int64_t>(width) ||
        destY <= -static_cast<std::int64_t>(height) ||
        destX >= static_cast<std::int64_t>(targetWidth) ||
        destY >= static_cast<std::int64_t>(targetHeight))
        return {};
    const auto trimLeft = destX < 0 ? static_cast<std::uint32_t>(-destX) : 0u;
    const auto trimTop = destY < 0 ? static_cast<std::uint32_t>(-destY) : 0u;
    const auto eyeX = destX < 0 ? 0u : static_cast<std::uint32_t>(destX);
    const auto eyeY = destY < 0 ? 0u : static_cast<std::uint32_t>(destY);
    const auto visibleWidth = (std::min)(width - trimLeft, targetWidth - eyeX);
    const auto visibleHeight = (std::min)(height - trimTop, targetHeight - eyeY);
    if (!visibleWidth || !visibleHeight) return {};
    return {sourceLeft + trimLeft, sourceTop + trimTop,
            sourceLeft + trimLeft + visibleWidth,
            sourceTop + trimTop + visibleHeight,
            eyeX, eyeY, true};
}
static_assert(native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u, 62, 61).sourceRight == 4u);
static_assert(native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u, 62, 61).sourceBottom == 6u);
static_assert(!native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u, 64, 61).valid);
static_assert(native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u, -3, -4).sourceLeft == 5u);
static_assert(native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u, -3, -4).sourceTop == 7u);
static_assert(native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u, -3, -4).destX == 0u);
static_assert(!native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u, -8, 12).valid);
static_assert(!native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u,
    (std::numeric_limits<std::int64_t>::min)(), 12).valid);
static_assert(!native_game_copy_clipped_region(
    16u, 16u, 2u, 3u, 10u, 11u, 64u, 64u,
    (std::numeric_limits<std::uint32_t>::max)(), 12).valid);

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

 
// Translate a game-authored StretchRect which crosses the native eye edges.
// D3D11 viewports may not use negative top-left coordinates. Clipping ONLY
// the viewport without advancing the source UV incorrectly stretches a
// partial menu/car/race sprite across the remaining pixels. Retain the
// original destination-to-source affine and the source crop's texel clamp.
struct NativeGameStretchClippedRegion {
    std::uint32_t left{}, top{}, right{}, bottom{};
    NativeGameStretchUvRegion uv{};
    bool valid{};
};
[[nodiscard]] constexpr NativeGameStretchClippedRegion
native_game_stretch_clipped_region(
    std::uint32_t sourceWidth, std::uint32_t sourceHeight,
    std::uint32_t srcLeft, std::uint32_t srcTop,
    std::uint32_t srcRight, std::uint32_t srcBottom,
    std::uint32_t targetWidth, std::uint32_t targetHeight,
    std::int32_t destLeft, std::int32_t destTop,
    std::int32_t destRight, std::int32_t destBottom) noexcept
{
    const auto uv = native_game_stretch_uv_region(
        sourceWidth, sourceHeight, srcLeft, srcTop, srcRight, srcBottom);
    if (!uv.valid || !targetWidth || !targetHeight ||
        targetWidth > static_cast<std::uint32_t>(
            (std::numeric_limits<std::int32_t>::max)()) ||
        targetHeight > static_cast<std::uint32_t>(
            (std::numeric_limits<std::int32_t>::max)()) ||
        destRight <= destLeft || destBottom <= destTop)
        return {};
    const std::int64_t x0 = destLeft < 0 ? 0 : destLeft;
    const std::int64_t y0 = destTop < 0 ? 0 : destTop;
    const std::int64_t x1 = destRight > static_cast<std::int64_t>(targetWidth)
        ? targetWidth : destRight;
    const std::int64_t y1 = destBottom > static_cast<std::int64_t>(targetHeight)
        ? targetHeight : destBottom;
    if (x0 >= x1 || y0 >= y1) return {};
    const float invWidth = 1.0f /
        static_cast<float>(static_cast<std::int64_t>(destRight) - destLeft);
    const float invHeight = 1.0f /
        static_cast<float>(static_cast<std::int64_t>(destBottom) - destTop);
    const float u0 = static_cast<float>(x0 - destLeft) * invWidth;
    const float u1 = static_cast<float>(x1 - destLeft) * invWidth;
    const float v0 = static_cast<float>(y0 - destTop) * invHeight;
    const float v1 = static_cast<float>(y1 - destTop) * invHeight;
    // Very large source rectangles can collapse sub-pixel spans in float;
    // fail closed instead of issuing a zero-width UV mapping.
    if (!(u1 > u0 && v1 > v0)) return {};
    NativeGameStretchClippedRegion result{};
    result.left = static_cast<std::uint32_t>(x0);
    result.top = static_cast<std::uint32_t>(y0);
    result.right = static_cast<std::uint32_t>(x1);
    result.bottom = static_cast<std::uint32_t>(y1);
    result.uv = uv;
    result.uv.constants[0] += u0 * uv.constants[2];
    result.uv.constants[1] += v0 * uv.constants[3];
    result.uv.constants[2] *= u1 - u0;
    result.uv.constants[3] *= v1 - v0;
    result.valid = true;
    return result;
}
} // namespace outrun::vr::dx11
