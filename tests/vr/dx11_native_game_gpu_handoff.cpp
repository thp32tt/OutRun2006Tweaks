// Portable native game GPU producer admission regression.
// clang++ -std=c++17 -Wall -Wextra -pedantic tests/vr/dx11_native_game_gpu_handoff.cpp
#include "../../src/vr/d3d11/native_game_gpu_handoff.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::GameNativeGpuHandoff;
int main() {
    auto admitted = [](bool full, bool complete, bool writable,
        bool owner, bool gpu, bool sink, unsigned w, unsigned h, unsigned gen) {
        return GameNativeGpuHandoff::may_offer(
            full,complete,writable,owner,gpu,sink,w,h,gen);
    };
    assert(admitted(true,true,true,true,true,true,3440,1440,2));
    assert(!admitted(false,true,true,true,true,true,256,144,2));
    assert(!admitted(true,false,true,true,true,true,3440,1440,2));
    assert(!admitted(true,true,false,true,true,true,3440,1440,2));
    assert(!admitted(true,true,true,false,true,true,3440,1440,2));
    assert(!admitted(true,true,true,true,false,true,3440,1440,2));
    assert(!admitted(true,true,true,true,true,false,3440,1440,2));
    assert(!admitted(true,true,true,true,true,true,0,1440,2));
    assert(!admitted(true,true,true,true,true,true,3440,0,2));
    assert(!admitted(true,true,true,true,true,true,3440,1440,0));
}
