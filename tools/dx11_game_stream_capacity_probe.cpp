#include "../src/vr/d3d11/native_game_stream_capacity.hpp"
#include "../src/vr/d3d11/native_game_frame_batch.hpp"
#include <array>
#include <cassert>
#include <cstdint>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    GameNativeFrameBatch batch{};
    std::array<std::uint32_t, GameNativeFrameBatch::kMaxDraws> capacity{};
    for (unsigned i=0; i<GameNativeFrameBatch::kMaxDraws; ++i) {
        assert(batch.accepts(i, 0u, true));
        const auto next=next_native_stream_capacity((i+1u)*384u,capacity[i]);
        assert(next >= (i+1u)*384u);
        capacity[i]=next;
        batch.succeeded(false);
    }
    assert(!batch.accepts(8u,0u,true));
    batch.reset();
    assert(batch.accepts(0u,0u,true));
    for (auto bytes:capacity) assert(next_native_stream_capacity(64u,bytes)==bytes);
    assert(next_native_stream_capacity(0u,0u)==0u);
}
