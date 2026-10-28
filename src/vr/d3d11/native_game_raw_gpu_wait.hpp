#pragma once
// A bounded SAME-Present D3D11 GPU readback wait for explicitly opted-in RAW
// game pixel diagnostics. Production native and D3D9Ex rendering never wait.
#include <cstdint>

namespace outrun::vr::dx11 {
enum class NativeRawGpuWaitResult { Complete, Pending, Failed };

template <class Probe, class ElapsedMicros, class Yield>
[[nodiscard]] NativeRawGpuWaitResult native_raw_wait_gpu_copy(
    Probe&& probe, ElapsedMicros&& elapsedMicros, Yield&& yield,
    std::uint64_t budgetMicros, std::uint32_t maxPolls = 65536u) {
    // Always probe at least once, including zero-budget calls. A fixed poll
    // cap protects a broken/stalled clock in addition to the time budget.
    for (std::uint32_t i = 0u; i < maxPolls; ++i) {
        const auto status = probe();
        if (status != NativeRawGpuWaitResult::Pending) return status;
        if (elapsedMicros() >= budgetMicros) return NativeRawGpuWaitResult::Pending;
        yield();
    }
    return NativeRawGpuWaitResult::Pending;
}
} // namespace outrun::vr::dx11
