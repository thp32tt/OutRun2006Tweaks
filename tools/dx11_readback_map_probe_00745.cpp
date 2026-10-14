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
static_assert(map_publication_contract(), "Map failure must not publish game frame");
int main() { assert(map_publication_contract()); }
