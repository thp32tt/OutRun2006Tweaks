#include <algorithm>
#include <cassert>
#include <cstdint>
#include <vector>
#include "vr/d3d11/live_game_fvf_polygon_windows.hpp"
#include "vr/d3d11/live_game_primitive_span.hpp"

// Native SM3 indexed TRIANGLESTRIP POINT mode keeps the original game VB and
// translates each authentic indexed triangle corner into a D3D11 point draw.
// Exercise GPU-window boundaries, source index repetition, global winding
// parity, late corruption and the fail-closed no-partial-window contract.
using namespace outrun::vr::dx11::live_game_frame;

int main() {
    constexpr std::uint32_t gpuIndices = 9u;
    std::uint32_t admitted = 0u;
    // End-to-end source admission for native full-game FVF + real SM3.
    // Previously both 2049+ strip triangles failed BEFORE the existing
    // multi-window GPU submit could run, making that implementation dormant.
    assert(game_native_primitive_element_count(
        5u, kMaxNativeGameStripPrimitives, admitted));
    assert(admitted == kMaxNativeGameStripPrimitives + 2u);
    assert(!game_native_primitive_element_count(
        5u, kMaxNativeGameStripPrimitives + 1u, admitted));
    assert(!game_native_primitive_element_count(
        4u, kMaxNativeGamePrimitives + 1u, admitted));
    // This fan limit was independently extended by 01097: the original
    // connected center/rim source fits while D3D11 splits native GPU indices.
    assert(game_native_primitive_element_count(
        6u, kMaxNativeGamePrimitives + 1u, admitted));
    assert(admitted == kMaxNativeGamePrimitives + 3u);
    assert(game_native_primitive_element_count(
        6u, kMaxNativeGameFanPrimitives, admitted));
    assert(admitted == kMaxNativeGameFanPrimitives + 2u);
    assert(!game_native_primitive_element_count(
        6u, kMaxNativeGameFanPrimitives + 1u, admitted));
    // The real GPU budget stays 6144 indices; oversized point strips must
    // use at least two DrawIndexed windows in both FVF and shader-bound paths.
    constexpr std::uint32_t nativeGpuIndices = kMaxNativeGameVertices;
    for (std::uint32_t primitiveCount :
         {kMaxNativeGamePrimitives + 1u, kMaxNativeGameStripPrimitives}) {
        std::uint32_t inputElements = 0u;
        assert(game_native_primitive_element_count(5u, primitiveCount, inputElements));
        const auto plan = game_fvf_polygon_window_plan(
            5u, inputElements, nativeGpuIndices, 128u);
        assert(plan.windows >= 2u);
        assert(plan.trianglesPerWindow == nativeGpuIndices / 3u);
        std::vector<std::uint32_t> source(inputElements);
        for (std::uint32_t i = 0u; i < inputElements; ++i)
            source[i] = (i * 7u + 3u) % inputElements;
        std::vector<std::uint32_t> composed, window;
        for (std::uint32_t batch = 0u; batch < plan.windows; ++batch) {
            const auto first = batch * plan.trianglesPerWindow;
            const auto count = (std::min)(plan.trianglesPerWindow,
                                          primitiveCount - first);
            assert(game_fvf_build_polygon_window(
                5u, source.data(), inputElements, inputElements, first,
                count, nativeGpuIndices, window));
            composed.insert(composed.end(), window.begin(), window.end());
        }
        assert(composed.size() == std::size_t(primitiveCount) * 3u);
        for (std::uint32_t triangle = 0u; triangle < primitiveCount; ++triangle) {
            const auto position = std::size_t(triangle) * 3u;
            assert(composed[position] == source[triangle + (triangle & 1u)]);
            assert(composed[position + 1u] ==
                   source[triangle + 1u - (triangle & 1u)]);
            assert(composed[position + 2u] == source[triangle + 2u]);
        }
        // A bad final original IB entry can never produce a valid tail
        // (the production renderer scans ALL source indices before Draw 0).
        const auto saved = window;
        source.back() = inputElements;
        assert(!game_fvf_build_polygon_window(
            5u, source.data(), inputElements, inputElements,
            primitiveCount - 1u, 1u, nativeGpuIndices, window));
        assert(window == saved);
    }
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
