#include "native_game_frame_batch.hpp"
#include <cassert>
#include <cstdint>
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
int main() {
    GameNativeFrameBatch b{};
    assert(!b.accepts(0,2,false) && b.accepts(2,2,false));
    assert(b.first_draw() && b.clear_depth());
    b.succeeded(false);
    assert(!b.first_draw() && b.clear_depth() && !b.accepts(3,2,false));
    b.reset();
    assert(!b.accepts(4,5,true) && b.accepts(5,5,true));
    b.succeeded(false);
    assert(b.clear_depth());
    b.succeeded(true);
    assert(!b.clear_depth());
    b.reset();
    for (std::uint32_t i=5; i<5+GameNativeFrameBatch::kMaxDraws; ++i) {
        assert(b.accepts(i,5,true));
        b.succeeded(i==6u);
    }
    assert(!b.accepts(13,5,true) && b.submitted==8u && !b.clear_depth());
    b.reset();
    b.succeeded(true); b.abort();
    assert(!b.accepts(1,0,true));
    b.reset();
    assert(b.accepts(0,0,true) && b.first_draw() && b.clear_depth());
    return 0;
}
