#pragma once

#include <d3d9.h>
#include <d3d11.h>

namespace outrun::vr::dx11 {

template <typename T>
struct TranslationResult {
    T value{};
    bool exact = false;
};

[[nodiscard]] TranslationResult<D3D11_BLEND> translate_blend(D3DBLEND value) noexcept;
[[nodiscard]] TranslationResult<D3D11_BLEND_OP> translate_blend_op(D3DBLENDOP value) noexcept;
[[nodiscard]] TranslationResult<D3D11_COMPARISON_FUNC> translate_compare(D3DCMPFUNC value) noexcept;
[[nodiscard]] TranslationResult<D3D11_CULL_MODE> translate_cull(D3DCULL value) noexcept;
[[nodiscard]] TranslationResult<D3D11_PRIMITIVE_TOPOLOGY> translate_primitive(D3DPRIMITIVETYPE value) noexcept;

} // namespace outrun::vr::dx11
