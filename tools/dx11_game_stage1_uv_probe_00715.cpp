#include "../src/vr/d3d11/live_game_stage1_uv.hpp"
#include "../src/vr/d3d11/live_game_fvf_layout.hpp"
#include "../src/vr/d3d11/live_game_stage1_dual_texture.hpp"
#include <cassert>
#include <cmath>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    GameFvfLayout fvf{};
    assert(game_fvf_layout(kGameFvfXyzRhw | kGameFvfDiffuse | kGameFvfTex2, fvf));
    assert(fvf.texcoordCount == 2u);
    GameFvfSample game{};
    game.uv[0] = .125f; game.uv[1] = .25f;
    game.uv1[0] = .75f; game.uv1[1] = .875f;
    float primary[2]{}, secondary[2]{};
    assert(game_fvf_select_uv(game, fvf, 0u, primary));
    assert(game_fvf_select_uv(game, fvf, 1u, secondary));
    assert(primary[0] != secondary[0] && primary[1] != secondary[1]);
    assert(stage1_game_uv_supported(1u, fvf.texcoordCount, 2u));
    // D3D9 row-vector COUNT2 UV transform: (u,v,1,0) * matrix.
    const float u = secondary[0] * 2.0f + .125f;
    const float v = secondary[1] * 3.0f - .25f;
    assert(std::fabs(u - 1.625f) < 0.00001f);
    assert(std::fabs(v - 2.375f) < 0.00001f);
    assert(stage1_dual_texture_compatible(true, true, true, true, true, true));
    assert(!stage1_game_uv_supported(2u, fvf.texcoordCount, 0u));
    assert(!stage1_game_uv_supported(0x10000u, fvf.texcoordCount, 0u));
    assert(!stage1_game_uv_supported(1u, fvf.texcoordCount, 0x100u));
    assert(!stage1_game_uv_supported(1u, fvf.texcoordCount, 3u));
    return 0;
}
