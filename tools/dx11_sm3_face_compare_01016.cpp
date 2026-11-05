// ps_3_0 dcl vFace -> scalar IFC/BREAKC/SETP -> D3D11 SV_IsFrontFace.
#include "native_sm3_interface_channels.hpp"
#include "native_sm3_conditional_flow.hpp"
#include "live_game_sm3_interface_capacity.hpp"
#include <cassert>
#include <string>
#include <string_view>
using namespace outrun::vr::dx11;
static_assert(native_sm3_face_declaration(false, 1u, 15u));
static_assert(!native_sm3_face_declaration(false, 1u, 1u));
static_assert(!native_sm3_face_declaration(true, 1u, 15u));
static_assert(!native_sm3_face_declaration(false, 0u, 15u));
static_assert(!native_sm3_face_declaration(false, 2u, 15u));
static_assert(native_sm3_face_scalar_source(1u));
static_assert(!native_sm3_face_scalar_source(2u));
static_assert(!native_sm3_face_scalar_source(3u));
static_assert(!native_sm3_face_scalar_source(0u));
static_assert(native_sm3_interface_decl_capacity(false, 12u, 0u, 2u));
static_assert(!native_sm3_interface_decl_capacity(false, 13u, 0u, 2u));
static_assert(native_sm3_scalar_condition_required_components(0x00u, 0u) == 1u);
static_assert(native_sm3_scalar_condition_required_components(0xe4u, 0u) == 1u);
static_assert(native_sm3_scalar_condition_required_components(0x55u, 0u) == 2u);
static_assert(std::string_view(native_sm3_face_compare_hlsl()).find(
    "input.r283_frontface ? 1.0f : -1.0f") != std::string_view::npos);
int main() {
    for (unsigned swizzle : {0x00u, 0xe4u, 0x55u}) {
        const auto required = native_sm3_scalar_condition_required_components(
            swizzle, 0u);
        std::string condition = native_sm3_face_compare_hlsl();
        const bool accepted = native_sm3_face_scalar_source(required) &&
            append_native_sm3_scalar_condition_operand(condition, swizzle, 0u);
        assert(accepted == (swizzle != 0x55u));
        if (accepted)
            assert(condition.find("r283_frontface") != std::string::npos);
    }
}
