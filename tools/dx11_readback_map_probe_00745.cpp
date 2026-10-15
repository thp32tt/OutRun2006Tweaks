#include "../src/vr/d3d11/native_game_frame_publication.hpp"
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
constexpr std::int32_t kStillDrawing = static_cast<std::int32_t>(0x887a000au);
constexpr bool map_publication_contract() {
    using M = GameNativeReadbackMap;
    constexpr auto classify = GameNativeFramePublication::classify_map;
    return classify(0, kStillDrawing, true, 1920, 7680) == M::Ready &&
           classify(0, kStillDrawing, true, 1920, 8192) == M::Ready &&
           classify(kStillDrawing, kStillDrawing, false, 1920, 0) == M::Pending &&
           classify(-1, kStillDrawing, true, 1920, 7680) == M::Failed &&
           classify(1, kStillDrawing, true, 1920, 7680) == M::Failed &&
           classify(0, kStillDrawing, false, 1920, 7680) == M::Failed &&
           classify(0, kStillDrawing, true, 1920, 7679) == M::Failed &&
           classify(0, kStillDrawing, true, 0, 7680) == M::Failed;
}

constexpr bool same_present_map_retry_contract() {
    constexpr auto retry = GameNativeFramePublication::retry_same_present_map;
    // 10 MHz clock: at most 2500 ticks / 0.25ms and 128 attempts.
    return retry(true, true, true, 0u, 0u, 10000000u) &&
           retry(true, true, true, 127u, 2499u, 10000000u) &&
           !retry(true, true, true, 128u, 0u, 10000000u) &&
           !retry(true, true, true, 0u, 2500u, 10000000u) &&
           !retry(false, true, true, 0u, 0u, 10000000u) &&
           !retry(true, false, true, 0u, 0u, 10000000u) &&
           !retry(true, true, false, 0u, 0u, 10000000u) &&
           !retry(true, true, true, 0u, 0u, 3999u);
}
static_assert(same_present_map_retry_contract(), "Only current full game Map may retry");
static_assert(map_publication_contract(), "Map failure must not publish game frame");
int main() { assert(map_publication_contract()); assert(same_present_map_retry_contract()); }
