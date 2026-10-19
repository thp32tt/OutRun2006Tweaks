#pragma once
// SM3 p0 predicate provenance for real VS/PS SETP and loop BREAKP.
// Branch-only predicates must never become native HLSL control inputs.
#include <string>
#include <vector>

namespace outrun::vr::dx11 {
class NativeSm3PredicateFlow {
public:
    [[nodiscard]] bool ready() const noexcept { return initialized_; }
    void write() noexcept { initialized_ = true; }
    bool begin_if() {
        if (frames_.size() >= 8u) return false;
        frames_.push_back({false, initialized_, false, false});
        return true;
    }
    bool otherwise() noexcept {
        if (frames_.empty() || frames_.back().loop || frames_.back().hasElse)
            return false;
        auto& frame = frames_.back();
        frame.thenInitialized = initialized_;
        initialized_ = frame.entryInitialized;
        frame.hasElse = true;
        return true;
    }
    bool end_if() noexcept {
        if (frames_.empty() || frames_.back().loop) return false;
        const Frame frame = frames_.back();
        frames_.pop_back();
        initialized_ &= frame.hasElse ? frame.thenInitialized : frame.entryInitialized;
        return true;
    }
    bool begin_repeat() {
        if (frames_.size() >= 8u) return false;
        frames_.push_back({true, initialized_, false, false});
        return true;
    }
    bool end_repeat() noexcept {
        if (frames_.empty() || !frames_.back().loop) return false;
        // Conservative on every repeat: BREAK/BREAKC/BREAKP may exit prior
        // to a SETP in a later iteration. A predicate valid on entry remains
        // valid; a predicate first written inside the loop does not escape.
        initialized_ &= frames_.back().entryInitialized;
        frames_.pop_back();
        return true;
    }
    [[nodiscard]] bool empty() const noexcept { return frames_.empty(); }
private:
    struct Frame {
        bool loop;
        bool entryInitialized;
        bool hasElse;
        bool thenInitialized;
    };
    bool initialized_ = false;
    std::vector<Frame> frames_;
};

inline bool append_native_sm3_setp(std::string& hlsl,
                                   const std::string& compareCondition) {
    if (compareCondition.empty()) return false;
    hlsl += "    r283_p0 = (" + compareCondition + ");\n";
    return true;
}
inline bool append_native_sm3_breakp(std::string& hlsl, bool negate) {
    hlsl += negate ? "    if (!r283_p0) break;\n"
                   : "    if (r283_p0) break;\n";
    return true;
}
} // namespace outrun::vr::dx11
