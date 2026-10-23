#include "live_game_sm3_polygon_raster.hpp"
#include "live_game_sm3_connected_instances.hpp"
#include <cassert>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    std::vector<std::uint32_t> points;
    assert(game_sm3_expand_polygon_points(4u,nullptr,6u,6u,100u,points));
    assert((points==std::vector<std::uint32_t>{0,1,2,3,4,5}));
    const std::uint32_t strip[]{4,2,1,3};
    assert(game_sm3_expand_polygon_points(5u,strip,4u,5u,100u,points));
    assert((points==std::vector<std::uint32_t>{4,2,1,1,2,3}));
    assert(game_sm3_expand_polygon_points(6u,nullptr,4u,4u,100u,points));
    assert((points==std::vector<std::uint32_t>{0,1,2,0,2,3}));
    std::vector<std::uint32_t> connected;
    assert(game_sm3_expand_connected_instance_indices(
        5u,nullptr,4u,4u,2u,100u,connected));
    assert(game_sm3_expand_polygon_points(4u,connected.data(),
        static_cast<std::uint32_t>(connected.size()),8u,100u,points));
    assert((points==std::vector<std::uint32_t>{0,1,2,2,1,3,4,5,6,6,5,7}));
    const auto safe=points;
    const std::uint32_t bad[]{0,1,8};
    assert(!game_sm3_expand_polygon_points(4u,bad,3u,8u,100u,points));
    assert(!game_sm3_expand_polygon_points(4u,nullptr,4u,8u,100u,points));
    assert(!game_sm3_expand_polygon_points(5u,nullptr,4u,8u,5u,points));
    assert(!game_sm3_expand_polygon_points(1u,nullptr,4u,8u,100u,points));
    assert(points==safe);
    assert(game_sm3_polygon_fill_admitted(3u,4u,3u,true,false,false));
    assert(game_sm3_polygon_fill_admitted(2u,5u,3u,false,true,false));
    assert(game_sm3_polygon_fill_admitted(1u,6u,1u,false,false,true));
    assert(!game_sm3_polygon_fill_admitted(1u,6u,3u,false,false,true));
    assert(!game_sm3_polygon_fill_admitted(1u,6u,1u,false,false,false));
    assert(!game_sm3_polygon_fill_admitted(2u,5u,1u,true,true,false));
    assert(!game_sm3_polygon_fill_admitted(2u,5u,1u,false,false,false));
    assert(!game_sm3_polygon_fill_admitted(2u,3u,1u,false,true,false));
}
