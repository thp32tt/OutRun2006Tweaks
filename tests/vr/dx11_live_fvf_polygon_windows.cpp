#include <cassert>
#include <cstdint>
#include <vector>
#include "vr/d3d11/live_game_fvf_polygon_windows.hpp"

using namespace outrun::vr::dx11::live_game_frame;
int main() {
    // Force multiple native uploads from authentic game D3D9 source fans
    // and point-filled strips, both VB-only and indexed DrawIndexed.
    for (std::uint32_t topology : {5u, 6u}) {
        for (std::uint32_t elements : {3u, 4u, 9u, 18u, 31u}) {
            const auto plan = game_fvf_polygon_window_plan(
                topology, elements, 9u, 64u);
            assert(plan.trianglesPerWindow == 3u);
            assert(plan.windows == (elements - 2u + 2u) / 3u);
            const std::vector<std::uint32_t> source = [&] {
                std::vector<std::uint32_t> v;
                for (std::uint32_t i = 0; i < elements; ++i)
                    v.push_back(elements - 1u - i);
                return v;
            }();
            for (bool indexed : {false, true}) {
                std::vector<std::uint32_t> composed, window;
                for (std::uint32_t first = 0; first < elements - 2u;
                     first += plan.trianglesPerWindow) {
                    const std::uint32_t count =
                        (std::min)(plan.trianglesPerWindow,
                                   elements - 2u - first);
                    assert(game_fvf_build_polygon_window(topology,
                        indexed ? source.data() : nullptr,
                        elements, elements, first, count, 9u, window));
                    assert(window.size() == count * 3u);
                    composed.insert(composed.end(), window.begin(), window.end());
                }
                std::vector<std::uint32_t> expected;
                for (std::uint32_t t = 0; t < elements - 2u; ++t) {
                    const std::uint32_t a =
                        topology == 6u ? 0u : t + (t & 1u);
                    const std::uint32_t b =
                        topology == 6u ? t + 1u : t + 1u - (t & 1u);
                    const auto at = [&](std::uint32_t i) {
                        return indexed ? source[i] : i;
                    };
                    expected.push_back(at(a));
                    expected.push_back(at(b));
                    expected.push_back(at(t + 2u));
                }
                assert(composed == expected);
                assert(composed.size() == (elements - 2u) * 3u);
            }
        }
    }
    // Malformed late IB entries, rejected budgets and unknown source
    // topologies must not clobber previous GPU-window geometry.
    const std::uint32_t bad[]{0u, 1u, 2u, 3u, 99u};
    std::vector<std::uint32_t> prior{7u, 8u};
    assert(!game_fvf_build_polygon_window(
        6u, bad, 5u, 5u, 1u, 2u, 6u, prior));
    assert((prior == std::vector<std::uint32_t>{7u,8u}));
    assert(!game_fvf_build_polygon_window(
        5u, bad, 5u, 5u, 0u, 3u, 6u, prior));
    assert(!game_fvf_build_polygon_window(
        6u, nullptr, 5u, 5u, 2u, 2u, 12u, prior));
    assert(!game_fvf_build_polygon_window(
        4u, nullptr, 5u, 5u, 0u, 1u, 12u, prior));
    assert((prior == std::vector<std::uint32_t>{7u,8u}));
    assert(game_fvf_polygon_window_plan(6u, 50u, 6u, 3u).windows == 0u);
    assert(game_fvf_polygon_window_plan(5u, 5u, 2u, 16u).windows == 0u);
    assert(game_fvf_polygon_window_plan(4u, 5u, 99u, 16u).windows == 0u);
}
