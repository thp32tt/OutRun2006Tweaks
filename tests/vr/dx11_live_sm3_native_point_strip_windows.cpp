#include <algorithm>
#include <cassert>
#include <cstdint>
#include <vector>
#include "vr/d3d11/live_game_fvf_polygon_windows.hpp"

// Native SM3 indexed TRIANGLESTRIP POINT mode keeps the original game VB and
// translates each authentic indexed triangle corner into a D3D11 point draw.
// Exercise GPU-window boundaries, source index repetition, global winding
// parity, late corruption and the fail-closed no-partial-window contract.
using namespace outrun::vr::dx11::live_game_frame;

int main() {
    constexpr std::uint32_t gpuIndices = 9u;
    for (std::uint32_t sourceCount : {8u, 11u, 27u, 43u}) {
        std::vector<std::uint32_t> source(sourceCount);
        for (std::uint32_t i = 0; i < sourceCount; ++i)
            source[i] = (i * 7u + 3u) % 13u; // real IB repeats & nonsequential order
        const auto plan = game_fvf_polygon_window_plan(5u, sourceCount,
                                                        gpuIndices, 128u);
        assert(plan.windows > 1u);
        assert(plan.trianglesPerWindow == gpuIndices / 3u);
        std::vector<std::uint32_t> composed, window;
        for (std::uint32_t batch = 0; batch < plan.windows; ++batch) {
            const auto first = batch * plan.trianglesPerWindow;
            const auto triangles = (std::min)(
                plan.trianglesPerWindow, sourceCount - 2u - first);
            assert(game_fvf_build_polygon_window(
                5u, source.data(), sourceCount, 13u, first,
                triangles, gpuIndices, window));
            assert(window.size() == triangles * 3u);
            composed.insert(composed.end(), window.begin(), window.end());
        }
        std::vector<std::uint32_t> expected;
        for (std::uint32_t t = 0; t < sourceCount - 2u; ++t) {
            expected.push_back(source[t + (t & 1u)]);
            expected.push_back(source[t + 1u - (t & 1u)]);
            expected.push_back(source[t + 2u]);
        }
        assert(composed == expected);
        // Out-of-range late D3D9 IB is preflighted before native GPU mutation;
        // even the transactional helper never replaces a prior valid window.
        const auto saved = window;
        source.back() = 13u;
        assert(!game_fvf_build_polygon_window(
            5u, source.data(), sourceCount, 13u,
            sourceCount - 4u, 2u, gpuIndices, window));
        assert(window == saved);
    }
    // Unsupported topology, invalid GPU budget and excessively fragmented
    // source never silently skip input corners to produce a partial frame.
    assert(game_fvf_polygon_window_plan(4u, 25u, gpuIndices, 128u).windows == 0u);
    assert(game_fvf_polygon_window_plan(5u, 25u, 2u, 128u).windows == 0u);
    assert(game_fvf_polygon_window_plan(5u, 65u, gpuIndices, 2u).windows == 0u);
    return 0;
}
