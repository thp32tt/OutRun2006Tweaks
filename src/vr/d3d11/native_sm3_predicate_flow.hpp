#pragma once
// SM3 p0 predicate provenance for real VS/PS SETP and loop BREAKP.
// Branch-only predicates must never become native HLSL control inputs.
#include <array>
#include <string>
#include <vector>

namespace outrun::vr::dx11 {
// Real SM3 SETP comparison provenance for implicit predicated TEX on a
// game-authored Draw. Initialized p0 is not necessarily quad-uniform.
// A later varying or conditional SETP must discard its uniform origin.
// A predicated implicit texture operation may execute only when the actual
// SETP p0 result is invariant over the pixel quad. Branch arms must join their
// provenance: the last parsed arm is NOT the last executed arm. An IFC driven
// by varying pixel registers can select a different predicate per pixel,
// even if each arm independently uses draw constants.
class NativeSm3DrawUniformPredicate final {
public:
    void write(bool bothSourcesDrawUniform, bool straightLine) noexcept {
        // Record writes in every enclosing scope, including nested branches.
        // A varying IF or a breakable REP/LOOP cannot promote a changed p0
        // merely because its final arm happens to be draw-uniform.
        for (unsigned i = 0u; i < depth_; ++i)
            frames_[i].wrotePredicate = true;
        uniform_ = bothSourcesDrawUniform && straightLine && uniform_flow();
    }
    [[nodiscard]] bool begin_if(bool uniformCondition) noexcept {
        if (depth_ == frames_.size()) return false;
        Frame& frame = frames_[depth_++];
        frame = {};
        frame.loop = false;
        frame.uniformCondition = uniformCondition;
        frame.entryUniform = uniform_;
        return true;
    }
    [[nodiscard]] bool otherwise() noexcept {
        if (!depth_ || frames_[depth_ - 1u].loop ||
            frames_[depth_ - 1u].hasElse) return false;
        Frame& frame = frames_[depth_ - 1u];
        frame.thenUniform = uniform_;
        frame.hasElse = true;
        uniform_ = frame.entryUniform;
        return true;
    }
    [[nodiscard]] bool end_if() noexcept {
        if (!depth_ || frames_[depth_ - 1u].loop) return false;
        const Frame frame = frames_[--depth_];
        const bool thenUniform = frame.hasElse ? frame.thenUniform : uniform_;
        const bool otherwiseUniform = frame.hasElse ? uniform_ : frame.entryUniform;
        // Draw-uniform b#/c# selects the same arm for the whole primitive:
        // both possible arms must retain p0's scalar uniform provenance.
        // A varying IFC is safe only when p0 was unchanged on every path.
        uniform_ = frame.uniformCondition
            ? (thenUniform && otherwiseUniform)
            : (frame.entryUniform && !frame.wrotePredicate);
        return true;
    }
    [[nodiscard]] bool begin_loop() noexcept {
        if (depth_ == frames_.size()) return false;
        Frame& frame = frames_[depth_++];
        frame = {};
        frame.loop = true;
        frame.entryUniform = uniform_;
        return true;
    }
    [[nodiscard]] bool end_loop() noexcept {
        if (!depth_ || !frames_[depth_ - 1u].loop) return false;
        const Frame frame = frames_[--depth_];
        // A BREAK/BREAKP, variable count, or zero effective iterations
        // can leave p0 from before the loop. Preserve only an untouched p0.
        uniform_ = frame.entryUniform && !frame.wrotePredicate;
        return true;
    }
    [[nodiscard]] bool uniform_flow() const noexcept {
        for (unsigned i = 0u; i < depth_; ++i)
            if (frames_[i].loop || !frames_[i].uniformCondition)
                return false;
        return true;
    }
    [[nodiscard]] bool empty() const noexcept { return depth_ == 0u; }
    [[nodiscard]] constexpr bool implicit_sampling_safe(
        bool predicated) const noexcept {
        return !predicated || uniform_;
    }
private:
    struct Frame {
        bool loop = false;
        bool uniformCondition = false;
        bool entryUniform = false;
        bool thenUniform = false;
        bool hasElse = false;
        bool wrotePredicate = false;
    };
    std::array<Frame, 8u> frames_{};
    unsigned depth_ = 0u;
    bool uniform_ = false;
};

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
