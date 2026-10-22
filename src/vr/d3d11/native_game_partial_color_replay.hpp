#pragma once
// Exact D3D9 partial TARGET/ColorFill replay route for the live native
// mono backbuffer. No ClearView means use an owned D3D11.0 shader raster
// ONLY for color-only writes; depth combined writes remain fail-closed.
namespace outrun::vr::dx11::live_game_frame {
enum class PartialColorReplayRoute { reject, clear_view, raster };
[[nodiscard]] constexpr PartialColorReplayRoute partial_game_color_replay_route(
    bool hasClearView, bool colorOnly, bool shaderTargetSupported) noexcept {
    if (hasClearView) return PartialColorReplayRoute::clear_view;
    return colorOnly && shaderTargetSupported
        ? PartialColorReplayRoute::raster
        : PartialColorReplayRoute::reject;
}
static_assert(partial_game_color_replay_route(false, true, true) ==
              PartialColorReplayRoute::raster);
static_assert(partial_game_color_replay_route(true, false, true) ==
              PartialColorReplayRoute::clear_view);
static_assert(partial_game_color_replay_route(false, false, true) ==
              PartialColorReplayRoute::reject);
static_assert(partial_game_color_replay_route(false, true, false) ==
              PartialColorReplayRoute::reject);
} // namespace outrun::vr::dx11::live_game_frame
