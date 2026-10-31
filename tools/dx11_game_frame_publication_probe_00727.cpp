#include "../src/vr/d3d11/native_game_frame_publication.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include "../src/vr/d3d11/native_game_readback_provenance.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;

constexpr bool publication_contract() {
    GameNativeFrameBatch frame{};
    if (!frame.accepts_full(0u)) return false;
    frame.succeeded(false);
    frame.record_source_draw(0u);
    GameReadbackProvenance provenance{17u, 1u, 0x123u, 2u};
    // Real game scene covers full screen, pixel sentinel unchanged: publish
    // only from a complete source batch and a current-Present GPU fence.
    if (!frame.publishable_full(true, 1u) ||
        !provenance.may_present(17u, true) ||
        !GameNativeFramePublication::should_upload(true, true, true, 0u))
        return false;
    if (provenance.may_present(18u, true) ||
        GameNativeFramePublication::should_upload(true, false, true, 800u) ||
        GameNativeFramePublication::should_upload(true, true, false, 800u))
        return false;
    // Legacy delayed inset still needs non-sentinel color evidence.
    if (GameNativeFramePublication::should_upload(false, true, true, 0u) ||
        !GameNativeFramePublication::should_upload(false, true, true, 1u))
        return false;
    if (!GameNativeFramePublication::valid_readback_pitch(1920u, 7680u) ||
        GameNativeFramePublication::valid_readback_pitch(1920u, 7679u) ||
        GameNativeFramePublication::valid_readback_pitch(0u, 7680u) ||
        !GameNativeFramePublication::valid_upload_pitch(1920u, 7680) ||
        GameNativeFramePublication::valid_upload_pitch(1920u, -7680) ||
        GameNativeFramePublication::valid_upload_pitch(1920u, 7679) ||
        GameNativeFramePublication::valid_readback_pitch(0xffffffffu, 0xffffffffu))
        return false;
    frame.abort();
    return !frame.publishable_full(true, 1u);
}
static_assert(publication_contract(), "Full frame publishing/fallback policy regression");
int main() { assert(publication_contract()); return 0; }
