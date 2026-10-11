#include "../src/vr/d3d11/live_game_primitive_span.hpp"
#include <cassert>
#include <cstdint>
#include <vector>

int main() {
    using outrun::vr::dx11::live_game_frame::game_primitive_element_count;
    std::uint32_t elements = 0xdeadbeefu;
    assert(game_primitive_element_count(false, 1, elements) && elements == 3);
    assert(game_primitive_element_count(true, 1, elements) && elements == 3);
    assert(game_primitive_element_count(false, 2, elements) && elements == 6);
    assert(game_primitive_element_count(true, 2, elements) && elements == 4);
    assert(game_primitive_element_count(false, 512, elements) && elements == 1536);
    assert(game_primitive_element_count(true, 512, elements) && elements == 514);
    const auto last = elements;
    assert(!game_primitive_element_count(false, 0, elements) && elements == last);
    assert(!game_primitive_element_count(true, 0, elements) && elements == last);
    assert(!game_primitive_element_count(false, 513, elements) && elements == last);
    assert(!game_primitive_element_count(true, 513, elements) && elements == last);
    using outrun::vr::dx11::live_game_frame::game_fan_to_triangle_list;
    std::vector<std::uint32_t> fan;
    assert(game_fan_to_triangle_list(1, nullptr, 0, 3, fan));
    assert((fan == std::vector<std::uint32_t>{0, 1, 2}));
    assert(game_fan_to_triangle_list(2, nullptr, 0, 4, fan));
    assert((fan == std::vector<std::uint32_t>{0, 1, 2, 0, 2, 3}));
    const std::uint32_t indexed[] = {3, 0, 2, 1};
    assert(game_fan_to_triangle_list(2, indexed, 4, 4, fan));
    assert((fan == std::vector<std::uint32_t>{3, 0, 2, 3, 2, 1}));
    const auto preserved = fan;
    assert(!game_fan_to_triangle_list(2, indexed, 3, 4, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(2, indexed, 4, 3, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(2, nullptr, 0, 3, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(0, nullptr, 0, 0, fan) && fan == preserved);
    assert(!game_fan_to_triangle_list(513, nullptr, 0, 515, fan) && fan == preserved);
    return 0;
}
