#pragma once
// Real D3D9 SM3 IFC/ELSE/ENDIF register initialization merge.
// All paths must initialize a component before it can feed a native shader.
#include <array>
#include <vector>

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
