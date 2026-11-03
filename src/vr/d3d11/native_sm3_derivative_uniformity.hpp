#pragma once
// D3D9 SM3 bool IF/ELSE branches are quad-uniform: DEFB and live b# values
// are immutable across pixels of the same game Draw. D3D11 implicit texture
// derivatives are therefore valid within those branches. IFC branches read
// pixel-varying float operands and remain fail-closed for implicit sampling.
// Predicated texture instructions remain excluded by the caller.
#include <array>

namespace outrun::vr::dx11 {

enum class NativeSm3IfcScalarOrigin : unsigned char {
    PixelDependent,
    DrawFloatConstant
};

// Only a directly validated scalar D3D9 c# operand is quad-uniform.
// Do not infer TEMP provenance from prior writes: a varying value may have
// reached it through earlier shader instructions. D3D9 relative constants
// must be rejected independently before classifying a source as c#.
[[nodiscard]] constexpr bool native_sm3_ifc_is_quad_uniform(
    NativeSm3IfcScalarOrigin first,
    NativeSm3IfcScalarOrigin second) noexcept {
    return first == NativeSm3IfcScalarOrigin::DrawFloatConstant &&
           second == NativeSm3IfcScalarOrigin::DrawFloatConstant;
}

class NativeSm3DerivativeUniformity final {
public:
    [[nodiscard]] bool begin(bool uniformCondition) noexcept {
        if (depth_ == states_.size()) return false;
        states_[depth_++] = uniformCondition;
        if (!uniformCondition) ++varying_;
        return true;
    }
    [[nodiscard]] bool end() noexcept {
        if (!depth_) return false;
        if (!states_[--depth_]) --varying_;
        return true;
    }
    [[nodiscard]] bool implicit_sampling_safe() const noexcept {
        return varying_ == 0u;
    }
    [[nodiscard]] bool empty() const noexcept { return depth_ == 0u; }
private:
    std::array<bool, 8u> states_{};
    unsigned depth_ = 0u;
    unsigned varying_ = 0u;
};
} // namespace outrun::vr::dx11
