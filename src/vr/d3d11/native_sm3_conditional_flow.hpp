#pragma once
// Real D3D9 SM3 IFC/ELSE/ENDIF register initialization merge.
// All paths must initialize a component before it can feed a native shader.
#include <array>
#include <vector>
#include <string>
#include "native_sm3_arithmetic_codegen.hpp"

namespace outrun::vr::dx11 {

inline constexpr const char* native_sm3_ifc_comparison(unsigned code) noexcept {
    switch (code) {
    case 1u: return ">";
    case 2u: return "==";
    case 3u: return ">=";
    case 4u: return "<";
    case 5u: return "!=";
    case 6u: return "<=";
    default: return nullptr;
    }
}

// Dynamic SM3 scalar compares consume the post-swizzle X lane. DZ/DW
// additionally require physical Z/W denominator lanes, even though IFC,
// BREAKC and SETP themselves read only one resulting scalar component.
// A reserved modifier must never become a native conditional branch.
[[nodiscard]] constexpr unsigned native_sm3_scalar_condition_required_components(
    unsigned swizzle, unsigned modifier) noexcept {
    if (swizzle > 255u || modifier > 12u) return 0u;
    return native_sm3_swizzled_components(
        native_sm3_source_modifier_components(1u, modifier), swizzle);
}

inline bool append_native_sm3_scalar_condition_operand(
    std::string& value, unsigned swizzle, unsigned modifier) {
    if (value.empty() ||
        native_sm3_scalar_condition_required_components(swizzle, modifier) == 0u)
        return false;
    static constexpr char kLanes[] = "xyzw";
    std::string operand = value + ".";
    for (unsigned lane = 0u; lane < 4u; ++lane)
        operand += kLanes[(swizzle >> (lane * 2u)) & 3u];
    if (!append_native_sm3_source_modifier(operand, modifier)) return false;
    value = "(" + operand + ").x";
    return true;
}

class NativeSm3ConditionalFlow {
public:
    using Temps = std::array<unsigned, 32>;
    using Outputs = std::array<unsigned, 16>;

    bool begin(const Temps& temps, const Outputs& outputs) {
        if (frames_.size() >= 8u) return false;
        frames_.push_back({temps, outputs, {}, {}, false});
        return true;
    }

    bool otherwise(Temps& temps, Outputs& outputs) noexcept {
        if (frames_.empty() || frames_.back().hasElse) return false;
        auto& frame = frames_.back();
        frame.thenTemps = temps;
        frame.thenOutputs = outputs;
        temps = frame.entryTemps;
        outputs = frame.entryOutputs;
        frame.hasElse = true;
        return true;
    }

    bool end(Temps& temps, Outputs& outputs) noexcept {
        if (frames_.empty()) return false;
        const auto frame = frames_.back();
        frames_.pop_back();
        const auto& otherTemps = frame.hasElse
            ? frame.thenTemps : frame.entryTemps;
        const auto& otherOutputs = frame.hasElse
            ? frame.thenOutputs : frame.entryOutputs;
        for (unsigned i = 0u; i < temps.size(); ++i)
            temps[i] &= otherTemps[i];
        for (unsigned i = 0u; i < outputs.size(); ++i)
            outputs[i] &= otherOutputs[i];
        return true;
    }

    [[nodiscard]] bool empty() const noexcept { return frames_.empty(); }

private:
    struct Frame {
        Temps entryTemps;
        Outputs entryOutputs;
        Temps thenTemps;
        Outputs thenOutputs;
        bool hasElse;
    };
    std::vector<Frame> frames_;
};

} // namespace outrun::vr::dx11
