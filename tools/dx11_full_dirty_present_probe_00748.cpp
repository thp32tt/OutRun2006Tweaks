#include "../src/vr/d3d11/native_game_dirty_region.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
using outrun::vr::dx11::live_game_frame::GameNativeDirtyRegionCoverage;
static constexpr bool check(std::uint32_t count, std::uint32_t bytes,
                            std::int64_t bl, std::int64_t bt,
                            std::int64_t br, std::int64_t bb,
                            std::int64_t rl, std::int64_t rt,
                            std::int64_t rr, std::int64_t rb) {
    return GameNativeDirtyRegionCoverage::covers_full_backbuffer(
        1920u, 1080u, count, bytes, bl, bt, br, bb, rl, rt, rr, rb);
}
static_assert(check(1, 16, 0, 0, 1920, 1080, 0, 0, 1920, 1080));
static_assert(!check(0, 16, 0, 0, 1920, 1080, 0, 0, 1920, 1080));
static_assert(!check(2, 32, 0, 0, 1920, 1080, 0, 0, 1920, 1080));
static_assert(!check(1, 15, 0, 0, 1920, 1080, 0, 0, 1920, 1080));
static_assert(!check(1, 16, 0, 0, 1920, 1080, 0, 0, 1919, 1080));
static_assert(!check(1, 16, 0, 0, 1920, 1080, 0, 1, 1920, 1080));
static_assert(!check(1, 16, 1, 0, 1920, 1080, 0, 0, 1920, 1080));
static_assert(!check(1, 16, 0, 0, 1920, 1079, 0, 0, 1920, 1080));
static_assert(!GameNativeDirtyRegionCoverage::covers_full_backbuffer(
    0, 1080, 1, 16, 0, 0, 0, 1080, 0, 0, 0, 1080));
static_assert(!GameNativeDirtyRegionCoverage::covers_full_backbuffer(
    (std::numeric_limits<std::uint32_t>::max)(), 1080, 1, 16,
    0, 0, 4294967295LL, 1080, 0, 0, 4294967295LL, 1080));
int main() {
    assert(check(1, 64, 0, 0, 1920, 1080, 0, 0, 1920, 1080));
    assert(!check(1, 16, 0, 0, 1920, 1080, 0, 0, 1920, 500));
}
