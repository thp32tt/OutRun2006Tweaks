#include "native_sm3_aux_color_output.hpp"
#include <array>
#include <cassert>
#include <string>
using outrun::vr::dx11::native_sm3_aux_color_destination;
using outrun::vr::dx11::append_native_sm3_ignored_mrt_locals;

int main() {
    // Real ps_3_0 oC1, oC2 and oC3 can be compiled when their RTs
    // are provably inert, without promoting them to the primary RTV.
    static_assert(native_sm3_aux_color_destination(false, 1u, 15u));
    static_assert(native_sm3_aux_color_destination(false, 2u, 7u));
    static_assert(native_sm3_aux_color_destination(false, 3u, 8u));
    static_assert(!native_sm3_aux_color_destination(true, 1u, 15u));
    static_assert(!native_sm3_aux_color_destination(false, 0u, 15u));
    static_assert(!native_sm3_aux_color_destination(false, 4u, 15u));
    static_assert(!native_sm3_aux_color_destination(false, 1u, 0u));
    static_assert(!native_sm3_aux_color_destination(false, 2u, 16u));
    std::string hlsl = "float4 main() : SV_Target0 {\n";
    const std::array<bool,4> onlyAux{{false, true, false, true}};
    append_native_sm3_ignored_mrt_locals(hlsl, onlyAux);
    assert(hlsl.find("float4 r283_oC1 = float4") != std::string::npos);
    assert(hlsl.find("float4 r283_oC2") == std::string::npos);
    assert(hlsl.find("float4 r283_oC3 = float4") != std::string::npos);
    assert(hlsl.find("SV_Target1") == std::string::npos);
    assert(hlsl.find("r283_color") == std::string::npos);
    const auto initialSize = hlsl.size();
    append_native_sm3_ignored_mrt_locals(hlsl, {{false,false,false,false}});
    assert(hlsl.size() == initialSize);
}
