#pragma once
#include <cstdint>
#include <limits>

namespace outrun::vr::dx11::live_game_stereo {
// D3D9 full-TARGET rectangles are real full-eye GPU Clears, not partial
// ClearView operations. D3D11.0 ClearRenderTargetView supports these without
// requiring ID3D11DeviceContext1; only bounded regions need D3D11.1.
[[nodiscard]] constexpr bool full_eye_target_rect(
    std::int64_t left, std::int64_t top,
    std::int64_t right, std::int64_t bottom,
    std::uint32_t eyeWidth, std::uint32_t eyeHeight) noexcept {
    return eyeWidth != 0u && eyeHeight != 0u &&
        left == 0 && top == 0 &&
        right == static_cast<std::int64_t>(eyeWidth) &&
        bottom == static_cast<std::int64_t>(eyeHeight);
}
static_assert(full_eye_target_rect(0, 0, 1920, 1080, 1920u, 1080u));
static_assert(!full_eye_target_rect(0, 0, 1920, 1079, 1920u, 1080u));
static_assert(!full_eye_target_rect(1, 0, 1920, 1080, 1920u, 1080u));
static_assert(!full_eye_target_rect(0, 0, 0, 1080, 0u, 1080u));

enum class NativeColorClearRoute : std::uint8_t {
    Reject, FullRtv, ClearView, ShaderRaster
};
// A cropped, game-authored TARGET clear still needs an actual native GPU
// pixel write on D3D11.0. Select a private full-screen triangle raster only
// for supported 8-bit eye targets when the D3D11.1 ClearView is unavailable.
// Reject invalid rectangles before recording either eye; never widen to
// ClearRenderTargetView and erase the rest of a menu/race frame.
[[nodiscard]] constexpr NativeColorClearRoute color_clear_route(
    bool hasRegion, std::int64_t left, std::int64_t top,
    std::int64_t right, std::int64_t bottom,
    std::uint32_t eyeWidth, std::uint32_t eyeHeight,
    bool clearViewAvailable, bool shaderRasterSupported) noexcept {
    if (!eyeWidth || !eyeHeight) return NativeColorClearRoute::Reject;
    if (!hasRegion) return NativeColorClearRoute::FullRtv;
    if (left < 0 || top < 0 || right <= left || bottom <= top ||
        right > static_cast<std::int64_t>(eyeWidth) ||
        bottom > static_cast<std::int64_t>(eyeHeight))
        return NativeColorClearRoute::Reject;
    if (full_eye_target_rect(left, top, right, bottom, eyeWidth, eyeHeight))
        return NativeColorClearRoute::FullRtv;
    if (clearViewAvailable) return NativeColorClearRoute::ClearView;
    return shaderRasterSupported ? NativeColorClearRoute::ShaderRaster
                                 : NativeColorClearRoute::Reject;
}
static_assert(color_clear_route(true, 4, 5, 80, 90, 1920u, 1080u,
    false, true) == NativeColorClearRoute::ShaderRaster);
static_assert(color_clear_route(true, 4, 5, 80, 90, 1920u, 1080u,
    true, false) == NativeColorClearRoute::ClearView);
static_assert(color_clear_route(true, 0, 0, 1920, 1080, 1920u, 1080u,
    false, false) == NativeColorClearRoute::FullRtv);
static_assert(color_clear_route(true, -1, 0, 80, 90, 1920u, 1080u,
    false, true) == NativeColorClearRoute::Reject);

// D3D9 Z/stencil Clears with an explicit whole-eye RECT must use the real
// D3D11.0 ClearDepthStencilView, just like an implicit whole-surface Clear.
// Sending those through the partial rectangle rasterizer consumes an extra
// shader Draw per eye and can fail when d3dcompiler_47 is absent. Keep cropped
// HUD/menu clears confined to their game-authored rectangle instead.
enum class NativeDepthClearRoute : std::uint8_t { Reject, FullDsv, PartialRaster };
[[nodiscard]] constexpr NativeDepthClearRoute depth_clear_route(
    bool hasRegion, std::int64_t left, std::int64_t top,
    std::int64_t right, std::int64_t bottom,
    std::uint32_t eyeWidth, std::uint32_t eyeHeight) noexcept {
    if (!eyeWidth || !eyeHeight) return NativeDepthClearRoute::Reject;
    if (!hasRegion) return NativeDepthClearRoute::FullDsv;
    if (left < 0 || top < 0 || right <= left || bottom <= top ||
        right > static_cast<std::int64_t>(eyeWidth) ||
        bottom > static_cast<std::int64_t>(eyeHeight))
        return NativeDepthClearRoute::Reject;
    return full_eye_target_rect(left, top, right, bottom, eyeWidth, eyeHeight)
        ? NativeDepthClearRoute::FullDsv : NativeDepthClearRoute::PartialRaster;
}
static_assert(depth_clear_route(false, 0, 0, 0, 0, 1920u, 1080u) ==
    NativeDepthClearRoute::FullDsv);
static_assert(depth_clear_route(true, 0, 0, 1920, 1080, 1920u, 1080u) ==
    NativeDepthClearRoute::FullDsv);
static_assert(depth_clear_route(true, 0, 0, 1919, 1080, 1920u, 1080u) ==
    NativeDepthClearRoute::PartialRaster);
static_assert(depth_clear_route(true, 0, 0, 0, 0, 1920u, 1080u) ==
    NativeDepthClearRoute::Reject);
static_assert(depth_clear_route(true, 0, 0, 1921, 1080, 1920u, 1080u) ==
    NativeDepthClearRoute::Reject);
// Hardware instancing is a single source-authored command/clear ordinal.
// A zero-instance call writes no pixels and cannot establish an XR eye.
[[nodiscard]] constexpr bool may_issue_instanced(
    std::uint32_t elementsPerInstance, std::uint32_t instanceCount,
    std::uint64_t issuedCommands) noexcept {
    return elementsPerInstance != 0u && instanceCount != 0u &&
        issuedCommands != (std::numeric_limits<std::uint64_t>::max)();
}
// D3D11 occlusion predicates can suppress a submitted GPU Draw without
// an API failure. Never claim that draw as color evidence for native stereo.
// The shared native XR eye ring uses a single-sample RTV. D3D11's OM
// SampleMask bit zero is the ONLY sample that can write that RTV: a nonzero
// high bit (for example 0xfffffffe) must never certify a blank stereo eye.
// Preserve the Draw itself for D3D9 chronology/depth and fallback.
[[nodiscard]] constexpr bool single_sample_eye_color_write(
    std::uint32_t sampleMask) noexcept {
    return (sampleMask & 1u) != 0u;
}
static_assert(!single_sample_eye_color_write(0u));
static_assert(!single_sample_eye_color_write(0xfffffffeu));
static_assert(single_sample_eye_color_write(1u));
static_assert(single_sample_eye_color_write(0xffffffffu));
// A real D3D11 Draw can be successfully enqueued while every fragment is
// guaranteed rejected by the active game depth/stencil state. Do not treat
// that depth-only/occlusion command as an eye color source just because VS/PS
// and an OM color mask are present. One-sided stencil NEVER is NOT enough:
// the opposite winding may still reach the native eye.
[[nodiscard]] constexpr bool fragment_can_reach_eye_color(
    bool depthEnabled, bool depthNever,
    bool stencilEnabled, bool frontStencilNever,
    bool backStencilNever) noexcept {
    return !(depthEnabled && depthNever) &&
           !(stencilEnabled && frontStencilNever && backStencilNever);
}
static_assert(fragment_can_reach_eye_color(false, true, false, true, true));
static_assert(fragment_can_reach_eye_color(true, false, true, true, false));
static_assert(fragment_can_reach_eye_color(true, false, true, false, true));
static_assert(!fragment_can_reach_eye_color(true, true, false, false, false));
static_assert(!fragment_can_reach_eye_color(false, false, true, true, true));

// Actual D3D11 eye color must CHANGE, not merely pass the sample mask.
// ZERO*source + ONE*destination preserves the destination for ADD and
// REV_SUBTRACT; a full-identity menu/vehicle HUD draw still advances the
// genuine geometry ordinal but must not certify a newly rendered XR eye.
// RGB and alpha independently retain an actual writable lane; MIN/MAX
// and unknown blending factors remain eligible for the renderer.
[[nodiscard]] constexpr bool blended_eye_color_may_change(
    bool blendEnabled, std::uint32_t writeMask,
    std::uint32_t srcRgb, std::uint32_t dstRgb, std::uint32_t opRgb,
    std::uint32_t srcAlpha, std::uint32_t dstAlpha,
    std::uint32_t opAlpha) noexcept {
    constexpr std::uint32_t kZero = 1u, kOne = 2u;
    constexpr std::uint32_t kAdd = 1u, kReverseSubtract = 3u;
    const auto identity = [](std::uint32_t src, std::uint32_t dst,
                             std::uint32_t op) constexpr {
        return src == kZero && dst == kOne &&
               (op == kAdd || op == kReverseSubtract);
    };
    if ((writeMask & 15u) == 0u) return false;
    if (!blendEnabled) return true; // replacement still writes a target
    return ((writeMask & 7u) != 0u && !identity(srcRgb, dstRgb, opRgb)) ||
           ((writeMask & 8u) != 0u && !identity(srcAlpha, dstAlpha, opAlpha));
}
static_assert(!blended_eye_color_may_change(true, 15, 1,2,1, 1,2,1));
static_assert(!blended_eye_color_may_change(true, 15, 1,2,3, 1,2,3));
static_assert(blended_eye_color_may_change(true, 15, 1,2,1, 2,2,1));
static_assert(blended_eye_color_may_change(true, 15, 2,2,1, 1,2,1));
static_assert(blended_eye_color_may_change(false, 15, 1,2,1, 1,2,1));
static_assert(!blended_eye_color_may_change(false, 0, 2,2,1, 2,2,1));

// The native eye can receive a real full TARGET Clear either directly from
// the game callback or through an ordered SourceClear timeline. Both routes
// erase prior color Draw/Copy/Stretch evidence: a later GPU Clear cannot be
// certified by pixels written before it. A scissor/viewport-clipped Clear
// must leave chronology intact and never fabricate a new geometry ordinal.
struct NativeEyeColorHistory {
    std::uint64_t colorDraws{};
    std::uint32_t colorPostpasses{};
    std::uint32_t fullTargetClears{};
    std::uint64_t lastFullClearDrawOrdinal{};
};
[[nodiscard]] constexpr NativeEyeColorHistory after_target_clear(
    NativeEyeColorHistory before, bool physicalFullClear,
    std::uint64_t currentGameDrawOrdinal) noexcept {
    if (!physicalFullClear) return before;
    before.colorDraws = 0u;
    before.colorPostpasses = 0u;
    if (before.fullTargetClears !=
        (std::numeric_limits<std::uint32_t>::max)())
        ++before.fullTargetClears;
    before.lastFullClearDrawOrdinal = currentGameDrawOrdinal;
    return before;
}
static_assert(after_target_clear({5u, 2u, 1u, 3u}, true, 5u).colorDraws == 0u);
static_assert(after_target_clear({5u, 2u, 1u, 3u}, true, 5u).colorPostpasses == 0u);
static_assert(after_target_clear({5u, 2u, 1u, 3u}, true, 5u).fullTargetClears == 2u);
static_assert(after_target_clear({5u, 2u, 1u, 3u}, false, 5u).colorDraws == 5u);

[[nodiscard]] constexpr bool color_certifiable(
    bool colorWritable, bool noActivePredicate) noexcept {
    return colorWritable && noActivePredicate;
}
// A completed game-authored Copy/Stretch can be the final visible color
// source for a depth-only on-eye Draw (offscreen menu/car/race composition).
// Still require at least one real geometry Draw and the existing independently
// validated view/pose evidence; postpasses do NOT fabricate Draw ordinals.
[[nodiscard]] constexpr bool authored_color_output_ready(
    std::uint64_t geometryDraws, std::uint64_t directColorDraws,
    std::uint32_t authoredColorPostpasses,
    std::uint32_t authoredFullColorClears = 0u,
    std::uint64_t lastFullClearDrawOrdinal = 0u) noexcept {
    // A genuine game TARGET clear provides eye color even if later
    // menu/car/race geometry writes only depth. A real draw AFTER the
    // latest full clear is needed: a blank or stale cleared frame is not
    // game geometry evidence. A later GPU postpass is independently valid.
    return geometryDraws != 0u &&
           (directColorDraws != 0u || authoredColorPostpasses != 0u ||
            (authoredFullColorClears != 0u &&
             geometryDraws > lastFullClearDrawOrdinal));
}
static_assert(authored_color_output_ready(2u, 0u, 1u));
static_assert(authored_color_output_ready(1u, 1u, 0u));
static_assert(!authored_color_output_ready(0u, 0u, 1u));
static_assert(!authored_color_output_ready(4u, 0u, 0u));
static_assert(authored_color_output_ready(2u, 0u, 0u, 1u, 0u));
static_assert(authored_color_output_ready(3u, 0u, 0u, 1u, 2u));
static_assert(!authored_color_output_ready(0u, 0u, 0u, 1u, 0u));
static_assert(!authored_color_output_ready(2u, 0u, 0u, 1u, 2u));
static_assert(authored_color_output_ready(2u, 0u, 1u, 1u, 2u));
} // namespace outrun::vr::dx11::live_game_stereo
