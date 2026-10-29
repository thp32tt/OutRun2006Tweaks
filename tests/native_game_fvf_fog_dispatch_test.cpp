#include "src/vr/d3d11/native_game_fvf_fog_dispatch.hpp"
#include <cassert>
#include <string>
using outrun::vr::dx11::native_fvf_fog_wrapper;
using outrun::vr::dx11::native_fvf_specular_wrapper;
using outrun::vr::dx11::native_fvf_vertex_specular_shade_admitted;
int main() {
    static_assert(native_fvf_vertex_specular_shade_admitted(2u),
                  "D3D9 Gouraud FVF SPECULAR must remain source-equivalent");
    for (const unsigned unsupported : {0u, 1u, 3u, 0xffffffffu})
        assert(!native_fvf_vertex_specular_shade_admitted(unsupported));
    // Real native stage-0, stage-1 and complex blend shader compositions
    // receive pixel fog AFTER source RGB/alpha/clip, not before blending.
    for (const char* name : {"PS", "PSTextured", "PSStage1Add",
                              "PSTextureBlendTextureAlphaPMModulateAlpha",
                              "PSTextureBlendFactorModulate4XAlpha"}) {
        const std::string wrapper = native_fvf_fog_wrapper(name);
        assert(wrapper.find(std::string("FvfApplyTableFog(v, ") + name +
                            "(v))") != std::string::npos);
        assert(wrapper.find("PSFvfTableFogVariant(VOut v)") != std::string::npos);
        assert(wrapper.find("SV_Target") != std::string::npos);
        const std::string specular = native_fvf_specular_wrapper(name);
        assert(specular.find(std::string("float4 color = ") + name + "(v)") !=
               std::string::npos);
        assert(specular.find("saturate(color.rgb + v.specular.rgb)") !=
               std::string::npos);
        assert(specular.find("return color;") != std::string::npos);
        assert(specular.find("FvfApplyTableFog") == std::string::npos);
    }
    // A failed lookup, malicious or unknown string cannot enter HLSL JIT.
    for (const char* bad : {"", "P", "not_a_PS", "PSFvfTableFogDiffuse",
                            "PS(v); discard; //", "PS\\n", "PS-foo"}) {
        assert(native_fvf_fog_wrapper(bad).empty());
        assert(native_fvf_specular_wrapper(bad).empty());
    }
    assert(native_fvf_fog_wrapper(std::string(97u, 'P')).empty());
    assert(native_fvf_specular_wrapper(std::string(97u, 'P')).empty());
    return 0;
}
