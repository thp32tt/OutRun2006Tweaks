#include "../src/vr/d3d11/live_game_cull_state.hpp"
#include <cassert>
#include <initializer_list>
using outrun::vr::dx11::live_game_frame::GameNativeCullAdmission;
using outrun::vr::dx11::live_game_frame::game_native_cull_admission;
int main() {
    GameNativeCullAdmission c{};
    for (unsigned kind : {4u, 5u, 6u})
        for (unsigned mode : {1u, 2u, 3u})
            assert(game_native_cull_admission(mode,kind,c) && c.d3d9Mode==mode);
    for (unsigned kind : {1u, 2u, 3u})
        for (unsigned mode : {1u, 2u, 3u})
            assert(game_native_cull_admission(mode,kind,c) && c.d3d9Mode==1u);
    const auto retained=c.d3d9Mode;
    for (unsigned invalid : {0u, 4u, 0xffffffffu})
        assert(!game_native_cull_admission(invalid,4u,c) && c.d3d9Mode==retained);
    for (unsigned invalid : {0u, 7u, 0xffffffffu})
        assert(!game_native_cull_admission(2u,invalid,c) && c.d3d9Mode==retained);
    return 0;
}
