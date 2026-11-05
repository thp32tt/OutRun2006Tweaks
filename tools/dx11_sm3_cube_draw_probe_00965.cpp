// Real game SM3 CubeTexture sample HLSL and source-register provenance.
#include "../src/vr/d3d11/native_sm3_texture_codegen.hpp"
#include <string>
int main() {
    using namespace outrun::vr::dx11;
    using Mode = NativeSm3Texture2DMode;
    if (native_sm3_cube_source_components(Mode::Implicit, 0u) != 7u ||
        native_sm3_cube_source_components(Mode::Bias, 0u) != 15u ||
        native_sm3_cube_source_components(Mode::ExplicitLod, 0u) != 15u ||
        native_sm3_cube_source_components(Mode::Gradients, 2u) != 7u ||
        native_sm3_cube_source_components(Mode::Gradients, 3u) != 7u ||
        native_sm3_cube_source_components(Mode::Projected, 0u) != 0u ||
        !native_sm3_cube_modifier_supported(Mode::Gradients, 2u, 12u) ||
        native_sm3_cube_modifier_supported(Mode::Gradients, 2u, 13u)) return 1;
    std::string source;
    if (!append_native_sm3_texturecube_declarations(source, 4u) ||
        !append_native_sm3_texturecube_sample(source, "r283_color", 15u,
            "r283_t0", 4u, 7u, Mode::Gradients, "r283_t1", "r283_t2") ||
        source.find("TextureCube<float4> r283_texture4") == std::string::npos ||
        source.find("SampleGrad(r283_sampler4, (r283_t0).xyz, (r283_t1).xyz, (r283_t2).xyz)") == std::string::npos) return 2;
    if (!append_native_sm3_texturecube_sample(source, "r283_color", 7u,
            "r283_t0", 4u, 8u, Mode::ExplicitLod, "", "") ||
        source.find("SampleLevel(r283_sampler4, (r283_t0).xyz, (r283_t0).w)") == std::string::npos) return 3;
    const auto old = source;
    if (append_native_sm3_texturecube_sample(source, "r283_color", 15u,
            "r283_t0", 4u, 9u, Mode::Projected, "", "") ||
        append_native_sm3_texturecube_sample(source, "r283_color", 15u,
            "r283_t0", 4u, 9u, Mode::Gradients, "", "") ||
        append_native_sm3_texturecube_declarations(source, 16u) ||
        source != old) return 4;
    return 0;
}
