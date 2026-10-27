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
    void reset() noexcept { attempts_ = 0u; nextOrdinal_ = 0u; }
    [[nodiscard]] bool should_attempt(std::uint64_t sourceOrdinal,
                                      std::uint64_t presentSerial) const noexcept {
        if (attempts_ >= kMaxAttemptsPerFrame) return false;
        const std::uint64_t first = (presentSerial % 24u) * 64u;
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
private:
    std::uint32_t attempts_ = 0u;
    std::uint64_t nextOrdinal_ = 0u;
};
} // namespace outrun::vr::dx11
