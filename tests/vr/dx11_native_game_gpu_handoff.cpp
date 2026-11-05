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
    // A supported native full-resolution GPU sink is independent of a
    // physically unwritable D3D9 CPU upload target (e.g. MSAA/format/tiles).
    // The game retains its original D3D9 Present and controller path.
    const bool cpuD3D9UploadWritable = false;
    const bool nativeGpuOutput = GameNativeGpuHandoff::gpu_frame_output_ready(
        true, true, true, true);
    assert(nativeGpuOutput && !cpuD3D9UploadWritable);
    assert(admitted(true,true,nativeGpuOutput,true,true,true,3440,1440,2));
    assert(!admitted(true,true,cpuD3D9UploadWritable,true,true,true,3440,1440,2));
    assert(!GameNativeGpuHandoff::gpu_frame_output_ready(false,true,true,true));
    assert(!GameNativeGpuHandoff::gpu_frame_output_ready(true,false,true,true));
    assert(!GameNativeGpuHandoff::gpu_frame_output_ready(true,true,false,true));
    assert(!GameNativeGpuHandoff::gpu_frame_output_ready(true,true,true,false));
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
