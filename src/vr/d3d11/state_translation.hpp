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
[[nodiscard]] TranslationResult<D3D11_STENCIL_OP> translate_stencil_op(D3DSTENCILOP value) noexcept;
[[nodiscard]] TranslationResult<D3D11_CULL_MODE> translate_cull(D3DCULL value) noexcept;
[[nodiscard]] TranslationResult<D3D11_PRIMITIVE_TOPOLOGY> translate_primitive(D3DPRIMITIVETYPE value) noexcept;

// D3D11 has no triangle-fan topology. This plan describes the exact
// triangle-list index stream a future native draw caller must materialize.
// Keeping this separate from translate_primitive() prevents readiness work
// from silently promoting TRIANGLEFAN before a caller consumes the expansion.
struct TriangleFanExpansionPlan {
    D3D11_PRIMITIVE_TOPOLOGY topology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    UINT sourceElementCount = 0;
    UINT expandedIndexCount = 0;
    bool exact = false;
};

[[nodiscard]] TriangleFanExpansionPlan translate_triangle_fan_expansion(
    UINT primitiveCount) noexcept;
[[nodiscard]] bool triangle_fan_source_element(
    UINT primitiveCount,
    UINT expandedIndex,
    UINT& sourceElement) noexcept;

// R121 materializes the exact non-indexed D3D9 triangle-fan vertex order as a
// D3D11 triangle-list index stream. This is a dormant translation primitive:
// callers still must own/upload an index buffer before native Draw* can use it.
[[nodiscard]] bool materialize_triangle_fan_vertex_indices(
    UINT primitiveCount,
    UINT baseVertex,
    UINT* expandedIndices,
    UINT expandedIndexCapacity) noexcept;

// R123 expands an indexed D3D9 triangle fan while preserving the source index
// values exactly. The caller retains D3D9 BaseVertexIndex separately as the
// future D3D11 DrawIndexed BaseVertexLocation; StartIndex is consumed here
// against the original index buffer. The R32_UINT output only rewrites fan
// ordering into a triangle-list stream and never activates native Draw*.
[[nodiscard]] bool materialize_indexed_triangle_fan_indices(
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    const void* sourceIndices,
    UINT sourceIndexCount,
    UINT* expandedIndices,
    UINT expandedIndexCapacity) noexcept;

} // namespace outrun::vr::dx11
