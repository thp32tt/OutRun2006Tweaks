#pragma once
// Live game ps_3_0 blending is translated only for exact RGB+alpha pairs.
// D3D9: BLEND_ONE=2, SRCALPHA=5, INVSRCALPHA=6, BLENDOP_ADD=1.
// Unsupported operators, separate alpha and unrecognized factors retain D3D9.
#include <cstdint>

namespace outrun::vr::dx11::live_game_frame {
enum class LiveSm3Blend : std::uint8_t {
    disabled,
    straight_alpha,
    additive,
    source_alpha_add,
    premultiplied_alpha,
    unsupported
};

[[nodiscard]] constexpr LiveSm3Blend live_sm3_blend(
    bool enabled, std::uint32_t source, std::uint32_t destination,
    std::uint32_t operation, bool separateAlpha) noexcept {
    if (!enabled) return LiveSm3Blend::disabled;
    if (separateAlpha || operation != 1u)
        return LiveSm3Blend::unsupported;
    if (source == 5u && destination == 6u)
        return LiveSm3Blend::straight_alpha;
    if (source == 2u && destination == 2u)
        return LiveSm3Blend::additive;
    if (source == 5u && destination == 2u)
        return LiveSm3Blend::source_alpha_add;
    if (source == 2u && destination == 6u)
        return LiveSm3Blend::premultiplied_alpha;
    return LiveSm3Blend::unsupported;
}

// D3D9 BOTH* source factors override the stored D3DRS_DESTBLEND.
// This portable dependency is shared by real-game state admission and
// the native D3D11 output-merger descriptor. Values are SDK-asserted there.
[[nodiscard]] constexpr std::uint32_t live_sm3_effective_dest_factor(
    std::uint32_t src, std::uint32_t dst) noexcept {
    return src == 12u ? 6u : src == 13u ? 5u : dst;
}
[[nodiscard]] constexpr bool live_sm3_needs_dynamic_blend_factor(
    bool enabled, std::uint32_t src, std::uint32_t dst, bool separateAlpha,
    std::uint32_t alphaSrc, std::uint32_t alphaDst) noexcept {
    constexpr auto needs = [](std::uint32_t f) constexpr noexcept {
        return f == 14u || f == 15u;
    };
    return enabled && (needs(src) ||
        needs(live_sm3_effective_dest_factor(src, dst)) ||
        (separateAlpha && (needs(alphaSrc) || needs(alphaDst))));
}
static_assert(live_sm3_effective_dest_factor(12u, 14u) == 6u &&
              live_sm3_effective_dest_factor(13u, 15u) == 5u &&
              live_sm3_effective_dest_factor(2u, 14u) == 14u);
static_assert(!live_sm3_needs_dynamic_blend_factor(true, 12u, 14u, false, 0u, 0u) &&
              !live_sm3_needs_dynamic_blend_factor(true, 13u, 15u, false, 0u, 0u) &&
              live_sm3_needs_dynamic_blend_factor(true, 12u, 14u, true, 14u, 2u) &&
              live_sm3_needs_dynamic_blend_factor(true, 2u, 14u, false, 0u, 0u) &&
              !live_sm3_needs_dynamic_blend_factor(false, 14u, 15u, true, 14u, 15u));

static_assert(live_sm3_blend(false, 0, 0, 0, false) ==
              LiveSm3Blend::disabled);
static_assert(live_sm3_blend(true, 5, 6, 1, false) ==
              LiveSm3Blend::straight_alpha);
static_assert(live_sm3_blend(true, 2, 2, 1, false) ==
              LiveSm3Blend::additive);
static_assert(live_sm3_blend(true, 5, 2, 1, false) ==
              LiveSm3Blend::source_alpha_add);
static_assert(live_sm3_blend(true, 2, 6, 1, false) ==
              LiveSm3Blend::premultiplied_alpha);
static_assert(live_sm3_blend(true, 5, 6, 2, false) ==
              LiveSm3Blend::unsupported);
static_assert(live_sm3_blend(true, 5, 6, 1, true) ==
              LiveSm3Blend::unsupported);
static_assert(live_sm3_blend(true, 1, 6, 1, false) ==
              LiveSm3Blend::unsupported);
} // namespace outrun::vr::dx11::live_game_frame
