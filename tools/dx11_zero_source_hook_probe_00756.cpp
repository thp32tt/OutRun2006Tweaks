#include "../src/vr/d3d11/live_game_primitive_span.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
constexpr bool zero_source_contract() noexcept {
    for (std::uint32_t mode=1u; mode<=6u; ++mode)
        if (!game_native_empty_primitive_type(mode)) return false;
    if (game_native_empty_primitive_type(0u) ||
        game_native_empty_primitive_type(7u)) return false;
    std::uint32_t elements=999u;
    if (game_native_primitive_element_count(4u,0u,elements)) return false;
    GameNativeFrameBatch frame{};
    if (frame.absorb_empty_source_draw(0u) ||
        !frame.accepts_full_seeded(0u,true)) return false;
    frame.succeeded(true);
    frame.record_source_draw(0u);
    // Four captured live VB/IB/UP zero-count variants, each no GPU Draw.
    for (std::uint64_t n=1u; n<=4u; ++n)
        if (!frame.absorb_empty_source_draw(n)) return false;
    if (!frame.accepts_full_seeded(5u,false) ||
        frame.publishable_full(true,4u)) return false;
    frame.succeeded(true);
    frame.record_source_draw(5u);
    if (!frame.publishable_full(true,6u) ||
        frame.publishable_full(false,6u) ||
        frame.absorb_empty_source_draw(7u)) return false;
    // Failed D3D9 HRESULT/unsupported source invalidates original scene.
    frame.abort();
    if (frame.absorb_empty_source_draw(6u) ||
        frame.publishable_full(true,6u)) return false;
    frame.reset();
    return !frame.absorb_empty_source_draw(0u);
}
static_assert(zero_source_contract(), "live full-frame zero source callback");
int main() { return zero_source_contract() ? 0 : 1; }
