#pragma once
// D3D9 SM3 shader-owned DEFI/REP/ENDREP for live native Draw programs.
// Keep the full structural nesting order and reject unbounded / dynamic
// repetition before the D3D11 shader compiler or original game Draw.
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace outrun::vr::dx11 {

// Static DEFI literals and per-Draw device i# values have separate owners.
// Dynamic REP is emitted as HLSL uniform control flow only when the game's
// current count passes validation before native GPU mutation.
// The bounded count and nested product protect live menu/race shader work.
[[nodiscard]] inline bool native_sm3_static_repeat_count(
    const std::array<std::uint32_t, 4>& literal,
    unsigned& count) noexcept {
    count = 0u;
    if (literal[0] == 0u || literal[0] > 16u) return false;
    count = literal[0];
    return true;
}

// The D3D9 game owns 16 i# registers, each int4. Only i#.x controls REP.
// Reject invalid counts instead of clamping into a different native draw.
[[nodiscard]] inline bool native_sm3_live_repeat_payload_valid(
    const std::array<int, 16u * 4u>& registers,
    std::uint16_t requiredMask) noexcept {
    for (unsigned reg = 0u; reg < 16u; ++reg) {
        if ((requiredMask & (1u << reg)) == 0u) continue;
        const int count = registers[reg * 4u];
        if (count < 1 || count > 16) return false;
    }
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

    using Temps = std::array<unsigned, 32>;
    using Outputs = std::array<unsigned, 16>;

    // A BREAK can leave the loop before an instruction writes a TEMP or
    // output. Intersect uncertain writes with the pre-loop state at ENDREP.
    bool begin_repeat(unsigned count, const Temps& temps,
                      const Outputs& outputs) {
        if (!begin_repeat(count)) return false;
        Frame& frame = frames_.back();
        frame.entryTemps = temps;
        frame.entryOutputs = outputs;
        frame.tracksWrites = true;
        return true;
    }

    // Live counts can change every Draw; conservative loop writes remain
    // unproven after ENDREP, including when BREAK skips the first write.
    bool begin_live_repeat(const Temps& temps, const Outputs& outputs) {
        if (!begin_repeat(16u, temps, outputs)) return false;
        frames_.back().hasBreak = true;
        return true;
    }

    bool record_break() noexcept {
        for (auto it = frames_.rbegin(); it != frames_.rend(); ++it) {
            if (it->kind == 2u) {
                if (!it->tracksWrites) return false;
                it->hasBreak = true;
                return true;
            }
        }
        return false;
    }

    bool end_repeat(Temps& temps, Outputs& outputs) noexcept {
        if (frames_.empty() || frames_.back().kind != 2u ||
            !frames_.back().tracksWrites) return false;
        const Frame& frame = frames_.back();
        if (frame.hasBreak) {
            for (unsigned i = 0u; i < temps.size(); ++i)
                temps[i] &= frame.entryTemps[i];
            for (unsigned i = 0u; i < outputs.size(); ++i)
                outputs[i] &= frame.entryOutputs[i];
        }
        frames_.pop_back();
        return true;
    }

    // Structural-only legacy mode cannot authorize a BREAK.
    bool end_repeat() noexcept {
        if (frames_.empty() || frames_.back().kind != 2u ||
            frames_.back().tracksWrites) return false;
        frames_.pop_back();
        return true;
    }

    [[nodiscard]] bool empty() const noexcept { return frames_.empty(); }

private:
    struct Frame {
        unsigned kind;
        unsigned count;
        bool hasElse;
        bool tracksWrites = false;
        bool hasBreak = false;
        Temps entryTemps{};
        Outputs entryOutputs{};
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

inline bool append_native_sm3_live_repeat_begin(
    std::string& translated, unsigned reg, unsigned ordinal) {
    if (reg >= 16u || ordinal >= 512u) return false;
    const std::string index = "r283_repeat_" + std::to_string(ordinal);
    translated += "    [loop] for (int " + index + " = 0; " + index +
                  " < r283_i[" + std::to_string(reg) + "].x; ++" + index + ") {\n";
    return true;
}

inline bool append_native_sm3_break(std::string& translated,
                                    const std::string& condition) {
    if (condition.empty())
        translated += "    break;\n";
    else
        translated += "    if (" + condition + ") break;\n";
    return true;
}

} // namespace outrun::vr::dx11
