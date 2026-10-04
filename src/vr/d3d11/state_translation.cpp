#include "state_translation.hpp"

#include <cstring>
#include <limits>
#include "vr/game/disasm_render_contract.hpp"

static_assert(OutRunVR::DisasmContract::WvpVsRegister == 64u);
static_assert(OutRunVR::DisasmContract::WvpVsRegisterCount == 4u);

namespace outrun::vr::dx11 {

TranslationResult<D3D11_BLEND> translate_blend(D3DBLEND value) noexcept {
    switch (value) {
    case D3DBLEND_ZERO: return {D3D11_BLEND_ZERO, true};
    case D3DBLEND_ONE: return {D3D11_BLEND_ONE, true};
    case D3DBLEND_SRCCOLOR: return {D3D11_BLEND_SRC_COLOR, true};
    case D3DBLEND_INVSRCCOLOR: return {D3D11_BLEND_INV_SRC_COLOR, true};
    case D3DBLEND_SRCALPHA: return {D3D11_BLEND_SRC_ALPHA, true};
    case D3DBLEND_INVSRCALPHA: return {D3D11_BLEND_INV_SRC_ALPHA, true};
    case D3DBLEND_DESTALPHA: return {D3D11_BLEND_DEST_ALPHA, true};
    case D3DBLEND_INVDESTALPHA: return {D3D11_BLEND_INV_DEST_ALPHA, true};
    case D3DBLEND_DESTCOLOR: return {D3D11_BLEND_DEST_COLOR, true};
    case D3DBLEND_INVDESTCOLOR: return {D3D11_BLEND_INV_DEST_COLOR, true};
    case D3DBLEND_SRCALPHASAT: return {D3D11_BLEND_SRC_ALPHA_SAT, true};
    case D3DBLEND_BLENDFACTOR: return {D3D11_BLEND_BLEND_FACTOR, true};
    case D3DBLEND_INVBLENDFACTOR: return {D3D11_BLEND_INV_BLEND_FACTOR, true};
    // D3D11 has matching SRC1 blend enums, but the current native fixed-
    // function pixel-shader prototype emits only SV_Target0. Until a second
    // color output and its linkage are proven, dual-source blend must remain
    // fail-closed rather than being counted as exact activation evidence.
    case D3DBLEND_SRCCOLOR2: return {D3D11_BLEND_SRC1_COLOR, false};
    case D3DBLEND_INVSRCCOLOR2: return {D3D11_BLEND_INV_SRC1_COLOR, false};
    case D3DBLEND_BOTHSRCALPHA: return {D3D11_BLEND_SRC_ALPHA, false};
    case D3DBLEND_BOTHINVSRCALPHA: return {D3D11_BLEND_INV_SRC_ALPHA, false};
    default: return {D3D11_BLEND_ONE, false};
    }
}

TranslationResult<D3D11_BLEND_OP> translate_blend_op(D3DBLENDOP value) noexcept {
    switch (value) {
    case D3DBLENDOP_ADD: return {D3D11_BLEND_OP_ADD, true};
    case D3DBLENDOP_SUBTRACT: return {D3D11_BLEND_OP_SUBTRACT, true};
    case D3DBLENDOP_REVSUBTRACT: return {D3D11_BLEND_OP_REV_SUBTRACT, true};
    case D3DBLENDOP_MIN: return {D3D11_BLEND_OP_MIN, true};
    case D3DBLENDOP_MAX: return {D3D11_BLEND_OP_MAX, true};
    default: return {D3D11_BLEND_OP_ADD, false};
    }
}

TranslationResult<D3D11_COMPARISON_FUNC> translate_compare(D3DCMPFUNC value) noexcept {
    switch (value) {
    case D3DCMP_NEVER: return {D3D11_COMPARISON_NEVER, true};
    case D3DCMP_LESS: return {D3D11_COMPARISON_LESS, true};
    case D3DCMP_EQUAL: return {D3D11_COMPARISON_EQUAL, true};
    case D3DCMP_LESSEQUAL: return {D3D11_COMPARISON_LESS_EQUAL, true};
    case D3DCMP_GREATER: return {D3D11_COMPARISON_GREATER, true};
    case D3DCMP_NOTEQUAL: return {D3D11_COMPARISON_NOT_EQUAL, true};
    case D3DCMP_GREATEREQUAL: return {D3D11_COMPARISON_GREATER_EQUAL, true};
    case D3DCMP_ALWAYS: return {D3D11_COMPARISON_ALWAYS, true};
    default: return {D3D11_COMPARISON_LESS_EQUAL, false};
    }
}

TranslationResult<D3D11_STENCIL_OP> translate_stencil_op(D3DSTENCILOP value) noexcept {
    switch (value) {
    case D3DSTENCILOP_KEEP: return {D3D11_STENCIL_OP_KEEP, true};
    case D3DSTENCILOP_ZERO: return {D3D11_STENCIL_OP_ZERO, true};
    case D3DSTENCILOP_REPLACE: return {D3D11_STENCIL_OP_REPLACE, true};
    case D3DSTENCILOP_INCRSAT: return {D3D11_STENCIL_OP_INCR_SAT, true};
    case D3DSTENCILOP_DECRSAT: return {D3D11_STENCIL_OP_DECR_SAT, true};
    case D3DSTENCILOP_INVERT: return {D3D11_STENCIL_OP_INVERT, true};
    case D3DSTENCILOP_INCR: return {D3D11_STENCIL_OP_INCR, true};
    case D3DSTENCILOP_DECR: return {D3D11_STENCIL_OP_DECR, true};
    default: return {D3D11_STENCIL_OP_KEEP, false};
    }
}

TranslationResult<D3D11_CULL_MODE> translate_cull(D3DCULL value) noexcept {
    switch (value) {
    case D3DCULL_NONE: return {D3D11_CULL_NONE, true};
    case D3DCULL_CW: return {D3D11_CULL_FRONT, true};
    case D3DCULL_CCW: return {D3D11_CULL_BACK, true};
    default: return {D3D11_CULL_BACK, false};
    }
}

TranslationResult<D3D11_PRIMITIVE_TOPOLOGY> translate_primitive(D3DPRIMITIVETYPE value) noexcept {
    switch (value) {
    case D3DPT_POINTLIST: return {D3D11_PRIMITIVE_TOPOLOGY_POINTLIST, true};
    case D3DPT_LINELIST: return {D3D11_PRIMITIVE_TOPOLOGY_LINELIST, true};
    case D3DPT_LINESTRIP: return {D3D11_PRIMITIVE_TOPOLOGY_LINESTRIP, true};
    case D3DPT_TRIANGLELIST: return {D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST, true};
    case D3DPT_TRIANGLESTRIP: return {D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP, true};
    // A fan is exact only after its source elements are expanded into an
    // explicit triangle-list index stream. Direct topology translation stays
    // fail-closed so census/activation gates cannot treat the fan as ready.
    case D3DPT_TRIANGLEFAN: return {D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED, false};
    default: return {D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED, false};
    }
}

TriangleFanExpansionPlan translate_triangle_fan_expansion(
    UINT primitiveCount) noexcept
{
    TriangleFanExpansionPlan out{};
    out.topology = D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST;

    if (primitiveCount == 0u)
    {
        out.exact = true;
        return out;
    }

    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    if (primitiveCount > maxValue / 3u)
        return out;

    out.sourceElementCount = primitiveCount + 2u;
    out.expandedIndexCount = primitiveCount * 3u;
    out.exact = true;
    return out;
}

bool triangle_fan_source_element(
    UINT primitiveCount,
    UINT expandedIndex,
    UINT& sourceElement) noexcept
{
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    if (!expansion.exact || expandedIndex >= expansion.expandedIndexCount)
        return false;

    const UINT triangle = expandedIndex / 3u;
    const UINT corner = expandedIndex % 3u;
    sourceElement = corner == 0u ? 0u : triangle + corner;
    return true;
}

bool materialize_triangle_fan_vertex_indices(
    UINT primitiveCount,
    UINT baseVertex,
    UINT* expandedIndices,
    UINT expandedIndexCapacity) noexcept
{
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    if (!expansion.exact)
        return false;
    if (expansion.expandedIndexCount == 0u)
        return true;
    if (!expandedIndices ||
        expandedIndexCapacity < expansion.expandedIndexCount)
        return false;

    const UINT maxValue = (std::numeric_limits<UINT>::max)();
    if (baseVertex >
        maxValue - (expansion.sourceElementCount - 1u))
        return false;

    for (UINT expandedIndex = 0u;
         expandedIndex < expansion.expandedIndexCount;
         ++expandedIndex)
    {
        UINT sourceElement = 0u;
        if (!triangle_fan_source_element(
                primitiveCount, expandedIndex, sourceElement))
            return false;
        expandedIndices[expandedIndex] = baseVertex + sourceElement;
    }
    return true;
}

bool materialize_indexed_triangle_fan_indices(
    UINT primitiveCount,
    D3DFORMAT sourceIndexFormat,
    UINT startIndex,
    const void* sourceIndices,
    UINT sourceIndexCount,
    UINT* expandedIndices,
    UINT expandedIndexCapacity) noexcept
{
    const auto expansion = translate_triangle_fan_expansion(primitiveCount);
    if (!expansion.exact)
        return false;
    if (sourceIndexFormat != D3DFMT_INDEX16 &&
        sourceIndexFormat != D3DFMT_INDEX32)
        return false;
    if (expansion.expandedIndexCount == 0u)
        return true;
    if (!sourceIndices || !expandedIndices ||
        expandedIndexCapacity < expansion.expandedIndexCount)
        return false;
    if (startIndex > sourceIndexCount ||
        expansion.sourceElementCount > sourceIndexCount - startIndex)
        return false;

    const auto* sourceBytes =
        static_cast<const unsigned char*>(sourceIndices);
    const UINT sourceStride =
        sourceIndexFormat == D3DFMT_INDEX16
            ? static_cast<UINT>(sizeof(WORD))
            : static_cast<UINT>(sizeof(DWORD));

    for (UINT expandedIndex = 0u;
         expandedIndex < expansion.expandedIndexCount;
         ++expandedIndex)
    {
        UINT sourceElement = 0u;
        if (!triangle_fan_source_element(
                primitiveCount, expandedIndex, sourceElement))
            return false;

        UINT sourceIndex = 0u;
        if (sourceIndexFormat == D3DFMT_INDEX16)
        {
            WORD value = 0;
            std::memcpy(
                &value,
                sourceBytes +
                    static_cast<std::size_t>(startIndex + sourceElement) *
                        sourceStride,
                sizeof(value));
            sourceIndex = value;
        }
        else
        {
            DWORD value = 0;
            std::memcpy(
                &value,
                sourceBytes +
                    static_cast<std::size_t>(startIndex + sourceElement) *
                        sourceStride,
                sizeof(value));
            sourceIndex = value;
        }
        expandedIndices[expandedIndex] = sourceIndex;
    }
    return true;
}

} // namespace outrun::vr::dx11