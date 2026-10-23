#include "native_game_pre_draw_replay.hpp"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <vector>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    GameNativePreDrawFills fills{};
    assert(fills.record(101,202,-5,4,25,22,128,72,0x204080c0u));
    assert(fills.record(101,202,40,50,130,80,128,72,0x7f102030u));
    std::vector<GameNativePreDrawTile> tiles;
    unsigned clearCalls=0, rasterCalls=0;
    const auto clear=[&](const GameNativePreDrawTile& t){++clearCalls;tiles.push_back(t);return true;};
    const auto raster=[&](const GameNativePreDrawTile& t){++rasterCalls;tiles.push_back(t);return true;};
    assert(game_native_replay_pre_draw_fills(fills,101,202,128,72,false,false,clear,raster));
    assert(rasterCalls==2 && clearCalls==0 && tiles.size()==2);
    assert(tiles[0].left==0 && tiles[0].top==4 && tiles[0].right==25);
    assert(tiles[1].left==40 && tiles[1].right==128 && tiles[1].bottom==72);
    assert(std::fabs(tiles[0].rgba[0]-64.0f/255.0f)<0.00001f);
    assert(std::fabs(tiles[0].rgba[3]-32.0f/255.0f)<0.00001f);
    tiles.clear();
    assert(game_native_replay_pre_draw_fills(fills,101,202,128,72,true,true,clear,raster));
    assert(clearCalls==2 && rasterCalls==2 && tiles.size()==2);
    assert(tiles[0].rgba[3]==1.0f && tiles[1].rgba[3]==1.0f);
    tiles.clear();
    assert(!game_native_replay_pre_draw_fills(fills,101,203,128,72,false,true,clear,raster));
    assert(!game_native_replay_pre_draw_fills(fills,101,202,64,72,false,false,clear,raster));
    assert(tiles.empty() && clearCalls==2 && rasterCalls==2);
    const auto reject=[&](const GameNativePreDrawTile&){++rasterCalls;return false;};
    assert(!game_native_replay_pre_draw_fills(fills,101,202,128,72,false,false,clear,reject));
    assert(rasterCalls==3 && fills.count==2);
    fills.entries[0].right=129;
    assert(!game_native_replay_pre_draw_fills(fills,101,202,128,72,false,false,clear,raster));
    assert(rasterCalls==3);
}
