#pragma once
// Bounded resampling of genuine source Draws for opt-in partial GPU preview.
// Never authorizes native full-game publication.
#include <cstdint>
#include <limits>
namespace outrun::vr::dx11 {
class NativeRawSourceProbeSchedule final {
public:
    static constexpr std::uint32_t kMaxAttemptsPerFrame = 4u;
    static constexpr std::uint64_t kMinimumSourceDrawGap = 96u;
    // Rotate real source Draw samples across the previous Present population.
    // Never promote a sampled partial Draw into full-frame coverage.
    void finish_present(std::uint64_t sourceDraws) noexcept {
        previousSourceDraws_ = sourceDraws;
        restart_epoch();
    }
    // A whole TARGET Clear starts a new source epoch, not a new game Present.
    void restart_epoch() noexcept { attempts_ = 0u; nextOrdinal_ = 0u; }
    // Reset/owner loss discards stale per-game population history.
    void reset() noexcept { restart_epoch(); previousSourceDraws_ = 0u; }
    [[nodiscard]] bool should_attempt(std::uint64_t sourceOrdinal,
                                      std::uint64_t presentSerial) const noexcept {
        if (attempts_ >= kMaxAttemptsPerFrame) return false;
        const std::uint64_t first = first_ordinal(presentSerial);
        return sourceOrdinal >= first && sourceOrdinal >= nextOrdinal_;
    }
    void record_attempt(std::uint64_t sourceOrdinal) noexcept {
        if (attempts_ >= kMaxAttemptsPerFrame) return;
        ++attempts_;
        constexpr auto maximum = (std::numeric_limits<std::uint64_t>::max)();
        nextOrdinal_ = sourceOrdinal > maximum - kMinimumSourceDrawGap
            ? maximum : sourceOrdinal + kMinimumSourceDrawGap;
    }
    [[nodiscard]] std::uint32_t attempts() const noexcept { return attempts_; }
    [[nodiscard]] std::uint64_t next_ordinal() const noexcept { return nextOrdinal_; }
    [[nodiscard]] std::uint64_t previous_source_draws() const noexcept {
        return previousSourceDraws_;
    }
private:
    [[nodiscard]] std::uint64_t first_ordinal(
        std::uint64_t presentSerial) const noexcept {
        constexpr std::uint64_t kPhases = 24u;
        const auto phase = presentSerial % kPhases;
        if (!previousSourceDraws_) return phase * 64u; // first-frame fallback
        // Overflow-safe ceiling division without (count + 23) wrap.
        const auto step = previousSourceDraws_ / kPhases +
            (previousSourceDraws_ % kPhases != 0u ? 1u : 0u);
        const auto first = phase * step; // phase <= 23, safely bounded
        return first < previousSourceDraws_
            ? first : previousSourceDraws_ - 1u;
    }
    std::uint32_t attempts_ = 0u;
    std::uint64_t nextOrdinal_ = 0u;
    std::uint64_t previousSourceDraws_ = 0u;
};
} // namespace outrun::vr::dx11
