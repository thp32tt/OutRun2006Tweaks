#include "../src/vr/d3d11/native_game_masked_draw.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_scissor_clip.hpp"
#include <cassert>
#include <cstdint>

using namespace outrun::vr::dx11::live_game_frame;

constexpr bool noWrite(bool full, bool cleared, std::uint32_t mask,
                       bool depth, bool depthWrite, bool stencil,
                       bool mrt) {
    return GameNativeMaskedDraw::no_target_write_source_draw(
        full, cleared, mask, depth, depthWrite, stencil, mrt);
}
// A real full-frame menu setup Draw with no possible writes is an admitted
// zero-output source event, not a dropped native draw or invented GPU pixels.
static_assert(noWrite(true, true, 0, false, true, false, false));
static_assert(noWrite(true, true, 0, true, false, false, false));
static_assert(!noWrite(false, true, 0, false, false, false, false));
static_assert(!noWrite(true, false, 0, false, false, false, false));
static_assert(!noWrite(true, true, 1, false, false, false, false));
static_assert(!noWrite(true, true, 8, false, false, false, false));
static_assert(!noWrite(true, true, 0, true, true, false, false));
static_assert(!noWrite(true, true, 0, false, false, true, false));
static_assert(!noWrite(true, true, 0, false, false, false, true));

// Draw and DrawIndexed share one exact source-ordinal stream. Skipped setup
// Draws must not certify a GPU frame themselves or corrupt following draws.
constexpr bool menuCarRaceSequence() {
    GameNativeFrameBatch b{};
    if (!b.absorb_empty_source_draw(0, true) ||
        b.publishable_full(true, 1) ||
        !b.accepts_full_seeded(1, true)) return false;
    b.succeeded(false);
    b.record_source_draw(1); // live native Draw
    if (!b.absorb_empty_source_draw(2, true) ||
        !b.accepts_full_seeded(3, true)) return false;
    b.succeeded(false);
    b.record_source_draw(3); // live native DrawIndexed
    return b.publishable_full(true, 4) && !b.publishable_full(true, 5);
}
static_assert(menuCarRaceSequence());

constexpr bool noClearCannotRescue() {
    GameNativeFrameBatch b{};
    return !b.absorb_empty_source_draw(0, false) && !b.publishable_full(true, 1);
}
static_assert(noClearCannotRescue());

// A successful, completely clipped game DrawIndexed can lack a usable VB/IB
// shadow without introducing any invisible geometry into the native frame.
// The next real Draw must still clear and draw at its exact source ordinal.
constexpr bool missingShadowClippedSourceContinues() {
    if (!GameNativeScissorClip::excludes_viewport(
            0u, 0u, 1920u, 1080u, 1920, 0, 2100, 100) ||
        GameNativeScissorClip::excludes_viewport(
            0u, 0u, 1920u, 1080u, 1919, 0, 2100, 100) ||
        GameNativeScissorClip::excludes_viewport(
            0u, 0u, 1920u, 1080u, 2100, 0, 2000, 100))
        return false;
    GameNativeFrameBatch b{};
    if (!b.absorb_empty_source_draw(0u, true) || // harmless setup Draw
        !b.absorb_empty_source_draw(1u, true) || // clipped missing-IB Draw
        b.publishable_full(true, 2u) ||
        !b.accepts_full_seeded(2u, true)) return false;
    b.succeeded(false);
    b.record_source_draw(2u); // real game native DrawIndexed
    return b.publishable_full(true, 3u) &&
        !b.absorb_empty_source_draw(4u, true);
}
static_assert(missingShadowClippedSourceContinues());

int main() {
    assert(missingShadowClippedSourceContinues());
    assert(menuCarRaceSequence());
    assert(noClearCannotRescue());
}
