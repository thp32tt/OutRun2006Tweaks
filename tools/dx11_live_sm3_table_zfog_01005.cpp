#include "live_game_sm3_table_fog.hpp"
#include <cassert>
#include <cmath>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    NativeSm3TableFog fog{};
    // Genuine exponential, squared-exponential and linear game fog inputs.
    for (unsigned mode : {1u, 2u, 3u}) {
        assert(native_sm3_table_zfog_admission(
            true, mode, 0u, false, false, true, false,
            0xff204080u, 0.2f, 0.8f, 1.0f, fog));
        assert(fog.enabled && fog.controls[3] == float(mode));
        assert(std::fabs(fog.rgba[0] - 32.0f/255.0f) < 0.0001f);
    }
    assert(std::fabs(native_sm3_table_zfog_factor(3u, 0.5f, 0.2f, 0.8f, 1.0f)
                     - 0.5f) < 0.0001f);
    assert(std::fabs(native_sm3_table_zfog_factor(1u, 1.0f, 0.0f, 1.0f, 1.0f)
                     - std::exp(-1.0f)) < 0.0001f);
    assert(std::fabs(native_sm3_table_zfog_factor(2u, 1.0f, 0.0f, 1.0f, 1.0f)
                     - std::exp(-1.0f)) < 0.0001f);
    for (unsigned mode : {1u, 2u, 3u}) {
        for (unsigned problem=0;problem<5;++problem) {
            bool ok = native_sm3_table_zfog_admission(
                true, mode, problem==0 ? 1u : 0u,
                problem==1, problem==2, problem!=3, problem==4,
                0u, 0.2f, 0.8f, 1.0f, fog);
            assert(!ok && !fog.enabled);
        }
    }
    assert(!native_sm3_table_zfog_admission(
        true, 3u, 0u, false, false, true, false,
        0u, 0.9f, 0.3f, 1.0f, fog));
    assert(!native_sm3_table_zfog_admission(
        true, 2u, 0u, false, false, true, false,
        0u, 0.0f, 1.0f, -1.0f, fog));
    assert(native_sm3_table_zfog_admission(
        true, 0u, 0u, false, false, true, false,
        0u, 0.0f, 1.0f, 1.0f, fog) && !fog.enabled);
    assert(native_sm3_table_zfog_admission(
        false, 3u, 1u, true, true, false, true,
        0u, 0.0f, 1.0f, -1.0f, fog) && !fog.enabled);
    std::string ps = "float4 main(R283Input input) : SV_Target0 {\n"
                     "    float4 r283_color = float4(0,0,0,0);\n"
                     "    return r283_color;\n}\n";
    assert(append_native_sm3_table_zfog(ps, true));
    assert(ps.find("register(b4)") != std::string::npos);
    assert(ps.find("r283_fogPosition : SV_Position") != std::string::npos);
    assert(ps.find("r283_color.rgb = lerp(") != std::string::npos);
    assert(ps.find("return r283_color;") != std::string::npos);
    assert(!append_native_sm3_table_zfog(ps, true)); // no duplicate injection
    return 0;
}
