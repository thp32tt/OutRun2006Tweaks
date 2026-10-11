#include "../src/vr/d3d11/live_game_primitive_span.hpp"
#include <cassert>
#include <cstdint>

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
    return 0;
}
