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

// D3D9 loop i#.x/y/z controls count/start/stride, not REP's count-only i#.x.
// This translation deliberately limits native work to 16 iterations; larger
// game loops continue on the authoritative D3D9 renderer.
[[nodiscard]] inline bool native_sm3_static_loop_parameters(
    const std::array<std::uint32_t, 4>& words,
    unsigned& count, int& start, int& stride) noexcept {
    const auto initial = static_cast<std::int32_t>(words[1]);
    const auto step = static_cast<std::int32_t>(words[2]);
    if (words[0] < 1u || words[0] > 16u || initial < 0 ||
        initial > 255 || step < -128 || step > 127 || words[3] != 0u)
        return false;
    const int last = initial + (static_cast<int>(words[0]) - 1) * step;
    if (last < 0 || last > 255) return false;
    count = words[0]; start = initial; stride = step;
    return true;
}
[[nodiscard]] inline bool native_sm3_live_loop_payload_valid(
    const std::array<int, 16u * 4u>& values,
    std::uint16_t loopMask) noexcept {
    for (unsigned i = 0; i < 16u; ++i) {
        if ((loopMask & (1u << i)) == 0u) continue;
        const int count = values[4u * i], start = values[4u * i + 1u],
                  stride = values[4u * i + 2u];
        if (count < 1 || count > 16 || start < 0 || start > 255 ||
            stride < -128 || stride > 127 || values[4u * i + 3u] != 0)
            return false;
        const int last = start + (count - 1) * stride;
        if (last < 0 || last > 255) return false;
    }
    return true;
}

// Enforce the actual game Draw's dynamic SM3 c[base+aL] ranges before
// touching native GPU state. Each nonzero entry is an exclusive aL limit.
[[nodiscard]] inline bool native_sm3_live_loop_indexed_bounds_valid(
    const std::array<int, 16u * 4u>& values,
    const std::array<std::uint16_t, 16>& exclusiveEnds) noexcept {
    for (unsigned reg = 0; reg < 16u; ++reg) {
        const unsigned end = exclusiveEnds[reg];
        if (!end) continue;
        if (end > 256u) return false;
        const int count = values[4u * reg];
        const int start = values[4u * reg + 1u];
        const int stride = values[4u * reg + 2u];
        if (count < 1 || count > 16 || start < 0 || start > 255 ||
            stride < -128 || stride > 127 || values[4u * reg + 3u] != 0)
            return false;
        const int last = start + (count - 1) * stride;
        if (last < 0 || start >= static_cast<int>(end) ||
            last >= static_cast<int>(end))
            return false;
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
            if (frame.kind != 2u && frame.kind != 3u) continue;
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

    // LOOP and REP share the strict nested-work budget and conservative
    // register-provenance merge; LOOP additionally owns an aL scope.
    bool begin_loop(unsigned count, const Temps& temps,
                    const Outputs& outputs, bool dynamic) {
        if (!begin_repeat(count, temps, outputs)) return false;
        frames_.back().kind = 3u;
        frames_.back().hasBreak = dynamic;
        return true;
    }
    bool end_loop(Temps& temps, Outputs& outputs) noexcept {
        if (frames_.empty() || frames_.back().kind != 3u ||
            !frames_.back().tracksWrites) return false;
        const Frame frame = frames_.back();
        if (frame.hasBreak) {
            for (unsigned i = 0; i < temps.size(); ++i)
                temps[i] &= frame.entryTemps[i];
            for (unsigned i = 0; i < outputs.size(); ++i)
                outputs[i] &= frame.entryOutputs[i];
        }
        frames_.pop_back();
        return true;
    }

    bool record_break() noexcept {
        for (auto it = frames_.rbegin(); it != frames_.rend(); ++it) {
            if (it->kind == 2u || it->kind == 3u) {
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

inline bool append_native_sm3_loop_begin(
    std::string& translated, unsigned ordinal, unsigned count,
    int start, int stride, bool dynamic, unsigned registerIndex) {
    if (ordinal >= 512u || count < 1u || count > 16u ||
        (dynamic && registerIndex >= 16u)) return false;
    const auto index = "r283_loop_" + std::to_string(ordinal);
    const auto limit = dynamic ? "r283_i[" + std::to_string(registerIndex) + "].x"
                               : std::to_string(count);
    const auto first = dynamic ? "r283_i[" + std::to_string(registerIndex) + "].y"
                               : std::to_string(start);
    const auto step = dynamic ? "r283_i[" + std::to_string(registerIndex) + "].z"
                              : std::to_string(stride);
    translated += "    [loop] for (int " + index + " = 0; " + index +
                  " < " + limit + "; ++" + index + ") {\n";
    translated += "        int r283_aL = " + first + " + " + index +
                  " * (" + step + ");\n";
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
