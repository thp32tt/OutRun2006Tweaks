#pragma once
// D3D9 SM3 shader-owned DEFI/REP/ENDREP for live native Draw programs.
// Keep the full structural nesting order and reject unbounded / dynamic
// repetition before the D3D11 shader compiler or original game Draw.
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace outrun::vr::dx11 {

// A verified DEFI literal is the only integer source supported by REP.
// x is the loop count; never interpret a dynamic i# as a compile-time value.
// The bounded count and nested product protect live menu/race shader work.
[[nodiscard]] inline bool native_sm3_static_repeat_count(
    const std::array<std::uint32_t, 4>& literal,
    unsigned& count) noexcept {
    count = 0u;
    if (literal[0] == 0u || literal[0] > 16u) return false;
    count = literal[0];
    return true;
}

class NativeSm3StructuredFlow {
public:
    bool begin_if() {
        if (frames_.size() >= 8u) return false;
        frames_.push_back({1u, 0u, false});
        return true;
    }

    bool otherwise() noexcept {
        if (frames_.empty() || frames_.back().kind != 1u ||
            frames_.back().hasElse) return false;
        frames_.back().hasElse = true;
        return true;
    }

    bool end_if() noexcept {
        if (frames_.empty() || frames_.back().kind != 1u) return false;
        frames_.pop_back();
        return true;
    }

    bool begin_repeat(unsigned count) {
        if (count == 0u || count > 16u || frames_.size() >= 8u)
            return false;
        unsigned copies = count;
        for (const Frame& frame : frames_) {
            if (frame.kind != 2u) continue;
            if (copies > 64u / frame.count) return false;
            copies *= frame.count;
        }
        frames_.push_back({2u, count, false});
        return true;
    }

    bool end_repeat() noexcept {
        if (frames_.empty() || frames_.back().kind != 2u) return false;
        frames_.pop_back();
        return true;
    }

    [[nodiscard]] bool empty() const noexcept { return frames_.empty(); }

private:
    struct Frame {
        unsigned kind;
        unsigned count;
        bool hasElse;
    };
    std::vector<Frame> frames_;
};

inline bool append_native_sm3_repeat_begin(
    std::string& translated, unsigned count, unsigned ordinal) {
    if (count == 0u || count > 16u || ordinal >= 512u) return false;
    const std::string index = "r283_repeat_" + std::to_string(ordinal);
    translated += "    [loop] for (int " + index + " = 0; " + index +
                  " < " + std::to_string(count) + "; ++" + index + ") {\n";
    return true;
}

} // namespace outrun::vr::dx11
