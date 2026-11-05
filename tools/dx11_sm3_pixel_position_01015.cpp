// Authentic ps_3_0 dcl vPos native pixel-coordinate acceptance boundary.
#include "native_sm3_interface_channels.hpp"
#include "native_sm3_arithmetic_codegen.hpp"
using namespace outrun::vr::dx11;
static_assert(native_sm3_pixel_position_declaration(false, 0u, 0x0fu));
static_assert(!native_sm3_pixel_position_declaration(true, 0u, 0x0fu));
static_assert(!native_sm3_pixel_position_declaration(false, 1u, 0x0fu));
static_assert(native_sm3_pixel_position_declaration(false, 0u, 0x03u));
static_assert(native_sm3_pixel_position_declaration(false, 0u, 0x01u));
static_assert(native_sm3_pixel_position_declaration(false, 0u, 0x02u));
static_assert(!native_sm3_pixel_position_declaration(false, 0u, 0x07u));
static_assert(native_sm3_pixel_position_source(0x01u));
static_assert(native_sm3_pixel_position_source(0x03u));
static_assert(!native_sm3_pixel_position_source(0u));
static_assert(!native_sm3_pixel_position_source(0x04u));
static_assert(!native_sm3_pixel_position_source(0x08u));
static_assert(native_sm3_pixel_position_source(
    native_sm3_swizzled_components(0x03u, 0xe4u)));
static_assert(!native_sm3_pixel_position_source(
    native_sm3_swizzled_components(0x01u, 0xaau)));
static_assert(!native_sm3_pixel_position_source(
    native_sm3_swizzled_components(
        native_sm3_source_modifier_components(0x03u, 9u), 0xe4u)));
#include <string_view>
static_assert(std::string_view(native_sm3_pixel_position_hlsl()).find(
    "float4(0.5f, 0.5f, 0.0f, 0.0f)") != std::string_view::npos);
int main() { return 0; }
