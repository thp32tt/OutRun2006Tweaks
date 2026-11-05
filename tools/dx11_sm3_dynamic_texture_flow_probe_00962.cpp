#include "native_sm3_texture_codegen.hpp"
#include <string>
#include <iostream>
#include <initializer_list>
using namespace outrun::vr::dx11;
int main() {
    using Mode = NativeSm3Texture2DMode;
    for (auto mode : {Mode::Implicit, Mode::Projected, Mode::Bias}) {
        if (native_sm3_texture_mode_allowed_in_control_flow(mode, true) ||
            !native_sm3_texture_mode_allowed_in_control_flow(mode, false))
            return 1;
    }
    for (auto mode : {Mode::ExplicitLod, Mode::Gradients})
        if (!native_sm3_texture_mode_allowed_in_control_flow(mode, true) ||
            !native_sm3_texture_mode_allowed_in_control_flow(mode, false))
            return 2;
    if (native_sm3_texture_mode_allowed_in_control_flow(
            static_cast<Mode>(255), true))
        return 3;
    std::string hlsl;
    if (!append_native_sm3_texture2d_declarations(hlsl, 4u) ||
        !append_native_sm3_texture2d_sample(hlsl, "r283_t1", 3u,
                                            "r283_t0", 4u, 0u, Mode::Gradients,
                                            "r283_t2", "r283_t3") ||
        hlsl.find("Texture2D<float4> r283_texture4") == std::string::npos ||
        hlsl.find("r283_texture4.SampleGrad(r283_sampler4") == std::string::npos ||
        hlsl.find("r283_t1.xy = r283_texel_0.xy") == std::string::npos ||
        hlsl.find("(r283_t2).xy, (r283_t3).xy") == std::string::npos)
        return 4;
    std::string explicitLod;
    if (!append_native_sm3_texture2d_sample(
            explicitLod, "r283_t0", 15u, "r283_t1", 2u, 1u, Mode::ExplicitLod) ||
        explicitLod.find(".SampleLevel(") == std::string::npos ||
        explicitLod.find("(r283_t1).w") == std::string::npos)
        return 5;
    std::string rejected;
    if (append_native_sm3_texture2d_sample(
            rejected, "r283_t0", 15u, "r283_t1", 2u, 3u, Mode::Gradients) ||
        !rejected.empty())
        return 6;
    std::cout << "SM3 conditional explicit-gradient/LOD shader GPU codegen passed; real game untested\n";
    return 0;
}
