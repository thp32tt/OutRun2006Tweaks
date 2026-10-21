#pragma once
// D3D9 SM3 shader register limits and D3D11 IA element limit for genuine
// intercepted menu/vehicle/race draws. This header is portable and has no
// device state; unsupported signatures keep the original D3D9 renderer.
#include <cstddef>

namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_interface_decl_capacity(
    bool vertexStage, std::size_t inputs, std::size_t outputs) noexcept {
    // vs_3_0 has 16 input and 12 output registers; ps_3_0 has ten
    // interpolated inputs and an implicit color output (not a DCL).
    return inputs != 0u && inputs <= (vertexStage ? 16u : 10u) &&
           (vertexStage ? (outputs != 0u && outputs <= 12u)
                        : outputs == 0u);
}
[[nodiscard]] constexpr bool native_sm3_ia_element_capacity(
    std::size_t elements) noexcept {
    // D3D11_IA_VERTEX_INPUT_STRUCTURE_ELEMENT_COUNT (D3D11 spec).
    return elements != 0u && elements <= 32u;
}
static_assert(native_sm3_interface_decl_capacity(true, 16u, 12u));
static_assert(native_sm3_interface_decl_capacity(false, 10u, 0u));
static_assert(!native_sm3_interface_decl_capacity(true, 17u, 12u));
static_assert(!native_sm3_interface_decl_capacity(true, 16u, 13u));
static_assert(!native_sm3_interface_decl_capacity(false, 11u, 0u));
static_assert(!native_sm3_interface_decl_capacity(false, 10u, 1u));
static_assert(native_sm3_ia_element_capacity(32u));
static_assert(!native_sm3_ia_element_capacity(33u));
} // namespace outrun::vr::dx11
