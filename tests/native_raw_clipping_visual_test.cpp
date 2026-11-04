#include "../src/vr/d3d11/native_game_raw_clipping_visual.hpp"
#include <cassert>
#include <cstdint>
#include <initializer_list>

using namespace outrun::vr::dx11;
constexpr auto choose = native_game_clipping_mode;
static_assert(choose(1u, false) == NativeGameClippingMode::Exact);
static_assert(choose(1u, true) == NativeGameClippingMode::Exact);
static_assert(choose(0u, false) == NativeGameClippingMode::Reject);
static_assert(choose(0u, true) == NativeGameClippingMode::RawDiagnostic);
static_assert(choose(2u, true) == NativeGameClippingMode::Reject);
static_assert(choose(0xffffffffu, true) == NativeGameClippingMode::Reject);
// Source plane mask stays exact unless a deliberately incomplete RAW tile
// has authenticated CLIPPING=FALSE; no plane read is inferred from a probe.
static_assert(native_game_user_clip_mask(0x3fu, NativeGameClippingMode::Exact) == 0x3fu);
static_assert(native_game_user_clip_mask(0x3fu, NativeGameClippingMode::RawDiagnostic) == 0u);
static_assert(native_game_user_clip_mask(0u, NativeGameClippingMode::RawDiagnostic) == 0u);
static_assert(native_game_user_clip_mask(0x80000000u, NativeGameClippingMode::Exact) == 0x80000000u);
int main() {
    // Source BOOL state and explicit opt-in must both be authentic. Full-frame
    // and standard DX11 modes never admit D3D9 CLIPPING=FALSE.
    for (std::uint32_t source : {0u, 1u, 2u, 0xffffffffu}) {
        const auto ordinary = choose(source, false);
        assert(ordinary != NativeGameClippingMode::RawDiagnostic);
        const auto raw = choose(source, true);
        assert((raw == NativeGameClippingMode::RawDiagnostic) ==
               (source == 0u));
    }
}
