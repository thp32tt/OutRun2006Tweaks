#include "state_translation.hpp"

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
    case D3DBLEND_SRCCOLOR2: return {D3D11_BLEND_SRC1_COLOR, true};
    case D3DBLEND_INVSRCCOLOR2: return {D3D11_BLEND_INV_SRC1_COLOR, true};
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
    case D3DPT_TRIANGLEFAN: return {D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED, false};
    default: return {D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED, false};
    }
}

} // namespace outrun::vr::dx11
