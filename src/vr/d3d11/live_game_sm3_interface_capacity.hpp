#pragma once
// D3D9 SM3 shader register limits and D3D11 IA element limit for genuine
// intercepted menu/vehicle/race draws. This header is portable and has no
// device state; unsupported signatures keep the original D3D9 renderer.
#include <cstddef>

namespace outrun::vr::dx11 {
[[nodiscard]] constexpr bool native_sm3_interface_decl_capacity(
    bool vertexStage, std::size_t inputs, std::size_t outputs,
    std::size_t systemInputs = 0u) noexcept {
    // ps_3_0 has ten interpolated v# registers PLUS rasterizer-provided
    // vPos/vFace (neither consumes a v# slot); vs_3_0 has no misc inputs.
    if (inputs == 0u || systemInputs > inputs || systemInputs > 2u)
        return false;
    return vertexStage
        ? (systemInputs == 0u && inputs <= 16u &&
           outputs != 0u && outputs <= 12u)
        : (inputs - systemInputs <= 10u && outputs == 0u);
}
[[nodiscard]] constexpr bool native_sm3_ia_element_capacity(
    std::size_t elements) noexcept {
    // D3D11_IA_VERTEX_INPUT_STRUCTURE_ELEMENT_COUNT (D3D11 spec).
    return elements != 0u && elements <= 32u;
}
static_assert(native_sm3_interface_decl_capacity(true, 16u, 12u));
static_assert(native_sm3_interface_decl_capacity(false, 10u, 0u));
static_assert(native_sm3_interface_decl_capacity(false, 12u, 0u, 2u));
static_assert(native_sm3_interface_decl_capacity(false, 2u, 0u, 2u));
static_assert(!native_sm3_interface_decl_capacity(false, 13u, 0u, 2u));
static_assert(!native_sm3_interface_decl_capacity(false, 3u, 0u, 3u));
static_assert(!native_sm3_interface_decl_capacity(true, 3u, 1u, 1u));
static_assert(!native_sm3_interface_decl_capacity(true, 17u, 12u));
static_assert(!native_sm3_interface_decl_capacity(true, 16u, 13u));
static_assert(!native_sm3_interface_decl_capacity(false, 11u, 0u));
static_assert(!native_sm3_interface_decl_capacity(false, 10u, 1u));
static_assert(native_sm3_ia_element_capacity(32u));
static_assert(!native_sm3_ia_element_capacity(33u));
} // namespace outrun::vr::dx11
