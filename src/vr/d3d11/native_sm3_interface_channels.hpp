#pragma once

namespace outrun::vr::dx11 {

// SM3 DCL usage ordinals must agree with the live D3D9 declaration -> DX11 IA.
// Only vertex inputs may carry skinning and tangent-basis semantics.
[[nodiscard]] constexpr const char* native_sm3_interface_semantic(
    unsigned usage, bool vertexStage, bool output, unsigned index) noexcept {
    if (index > 15u || (output && !vertexStage)) return nullptr;
    switch (usage) {
    case 0u:
        if (!vertexStage) return nullptr;
        if (output && index != 0u) return nullptr;
        return output ? "SV_Position" : "POSITION";
    case 1u: return vertexStage && !output ? "BLENDWEIGHT" : nullptr;
    case 2u: return vertexStage && !output ? "BLENDINDICES" : nullptr;
    case 3u: return vertexStage ? "NORMAL" : nullptr;
    case 5u: return "TEXCOORD";
    case 6u: return vertexStage && !output ? "TANGENT" : nullptr;
    case 7u: return vertexStage && !output ? "BINORMAL" : nullptr;
    case 10u: return "COLOR";
    default: return nullptr;
    }
}

// ps_3_0 dcl vPos is a rasterizer system input, not an interpolated v#.
// D3D9 defines only xy; z/w and vFace never become synthetic game data.
[[nodiscard]] constexpr bool native_sm3_pixel_position_declaration(
    bool vertexStage, unsigned registerIndex, unsigned mask) noexcept {
    return !vertexStage && registerIndex == 0u &&
           ((mask != 0u && (mask & ~0x03u) == 0u) || mask == 0x0fu);
}
// D3D9 ps_3_0 dcl vFace is a full-mask declaration for one scalar sign.
// It is only a compare operand (IFC/BREAKC/SETP), never a varying or a
// synthetic color value. D3D11's rasterizer supplies SV_IsFrontFace.
[[nodiscard]] constexpr bool native_sm3_face_declaration(
    bool vertexStage, unsigned registerIndex, unsigned mask) noexcept {
    return !vertexStage && registerIndex == 1u && mask == 0x0fu;
}
[[nodiscard]] constexpr bool native_sm3_face_scalar_source(
    unsigned physicalReadMask) noexcept {
    return physicalReadMask == 0x01u;
}
[[nodiscard]] constexpr const char* native_sm3_face_compare_hlsl() noexcept {
    return "float4((input.r283_frontface ? 1.0f : -1.0f), 0.0f, 0.0f, 0.0f)";
}

// SV_Position uses D3D10+ pixel centers (+0.5) while D3D9 VPOS is
// integer pixel-centered. Offset only xy; leave unsupported zw unread.
[[nodiscard]] constexpr const char* native_sm3_pixel_position_hlsl() noexcept {
    return "(input.r283_vpos - float4(0.5f, 0.5f, 0.0f, 0.0f))";
}
[[nodiscard]] constexpr bool native_sm3_pixel_position_source(
    unsigned physicalReadMask) noexcept {
    return physicalReadMask != 0u && (physicalReadMask & ~0x03u) == 0u;
}

// Reject any physical source lane that D3D9 did not declare. A native HLSL
// float4 with zero-initialized missing channels is NOT input provenance.
[[nodiscard]] constexpr bool native_sm3_declared_components_cover(
    unsigned declaredMask, unsigned requiredMask) noexcept {
    return declaredMask != 0u && requiredMask != 0u &&
           (declaredMask & ~15u) == 0u &&
           (requiredMask & ~15u) == 0u &&
           (declaredMask & requiredMask) == requiredMask;
}

[[nodiscard]] constexpr bool native_sm3_declared_output_complete(
    unsigned declaredMask, unsigned writtenMask) noexcept {
    return declaredMask != 0u && (declaredMask & ~15u) == 0u &&
           writtenMask == declaredMask;
}

} // namespace outrun::vr::dx11
