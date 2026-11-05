// A real native game Draw's paired GPU copies should be visible in the SAME
// opt-in RAW D3D9 Present when the asynchronous D3D11 event completes within
// the bounded wait, without weakening device-loss or stalled-GPU fallback.
#include "../src/vr/d3d11/native_game_raw_gpu_wait.hpp"
#include <cassert>
#include <cstdint>

using namespace outrun::vr::dx11;
int main() {
    using R = NativeRawGpuWaitResult;
    unsigned probes = 0u, yields = 0u;
    const auto immediate = native_raw_wait_gpu_copy(
        [&] { ++probes; return R::Complete; },
        [] { return std::uint64_t{0}; }, [&] { ++yields; }, 24000u);
    assert(immediate == R::Complete && probes == 1u && yields == 0u);

    probes = yields = 0u;
    const auto completed = native_raw_wait_gpu_copy(
        [&] { return ++probes >= 4u ? R::Complete : R::Pending; },
        [&] { return std::uint64_t{yields} * 1000u; },
        [&] { ++yields; }, 24000u);
    assert(completed == R::Complete && probes == 4u && yields == 3u);

    probes = yields = 0u;
    const auto timeout = native_raw_wait_gpu_copy(
        [&] { ++probes; return R::Pending; },
        [&] { return std::uint64_t{yields} * 6000u; },
        [&] { ++yields; }, 24000u);
    assert(timeout == R::Pending && probes == 5u && yields == 4u);

    probes = yields = 0u;
    const auto failure = native_raw_wait_gpu_copy(
        [&] { ++probes; return R::Failed; },
        [] { return std::uint64_t{0}; }, [&] { ++yields; }, 24000u);
    assert(failure == R::Failed && probes == 1u && yields == 0u);

    probes = yields = 0u;
    const auto stuckClock = native_raw_wait_gpu_copy(
        [&] { ++probes; return R::Pending; },
        [] { return std::uint64_t{0}; },
        [&] { ++yields; }, 24000u, 3u);
    assert(stuckClock == R::Pending && probes == 3u && yields == 3u);

    probes = yields = 0u;
    const auto zeroBudget = native_raw_wait_gpu_copy(
        [&] { ++probes; return R::Pending; },
        [] { return std::uint64_t{0}; },
        [&] { ++yields; }, 0u);
    assert(zeroBudget == R::Pending && probes == 1u && yields == 0u);
}
