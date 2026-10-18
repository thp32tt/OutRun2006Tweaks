// Focused portable native SM3 alpha-test regression (not HMD evidence).
#include "../src/vr/d3d11/live_game_sm3_alpha_test.hpp"
#include <string>

int main() {
    using namespace outrun::vr::dx11;
    for (unsigned mode = 0u; mode <= 8u; ++mode) {
        for (unsigned alpha : {0u, 127u, 128u, 255u}) {
            for (unsigned ref : {0u, 127u, 128u, 255u}) {
                const bool expected =
                    mode == 0u || mode == 8u ? true :
                    mode == 1u ? false :
                    mode == 2u ? alpha < ref :
                    mode == 3u ? alpha == ref :
                    mode == 4u ? alpha <= ref :
                    mode == 5u ? alpha > ref :
                    mode == 6u ? alpha != ref : alpha >= ref;
                if (native_sm3_alpha_pass(mode, alpha, ref) != expected)
                    return 1;
            }
        }
        std::string shader = "float4 main() : SV_Target0 {\n"
                             "    float4 r283_color = float4(1,1,1,1);\n"
                             "    return r283_color;\n}\n";
        if (!append_native_sm3_alpha_test(shader, mode)) return 2;
        if ((shader.find("register(b1)") != std::string::npos) !=
            (mode != 0u)) return 3;
        if ((shader.find("discard;") != std::string::npos) !=
            (mode != 0u)) return 4;
    }
    std::string bad = "not-a-shader";
    if (append_native_sm3_alpha_test(bad, 9u) ||
        append_native_sm3_alpha_test(bad, 3u) ||
        native_sm3_alpha_pass(3u, 256u, 1u))
        return 5;
    return 0;
}
