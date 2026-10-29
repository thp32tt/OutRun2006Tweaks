// Opt-in RAW GPU Draw tile must remain inside real cropped Present.
#include "../src/vr/d3d11/native_game_raw_partial_present_tile.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
constexpr bool valid_raw_partial_present() {
    NativeRawPresentTile p{};
    if (!native_raw_partial_present_tile(1920,1080,0,0,1920,1080,256,144,p) ||
        p.sourceX || p.sourceY || p.copyWidth!=256u ||
        p.copyHeight!=144u || p.destinationX!=1656 || p.destinationY!=8)
        return false;
    if (!native_raw_partial_present_tile(1920,1080,0,0,120,100,256,144,p) ||
        p.sourceX!=76u || p.sourceY!=30u || p.copyWidth!=104u ||
        p.copyHeight!=84u || p.destinationX!=8 || p.destinationY!=8)
        return false;
    if (!native_raw_partial_present_tile(1920,1080,700,300,748,348,256,144,p) ||
        p.sourceX!=112u || p.sourceY!=56u || p.copyWidth!=32u ||
        p.copyHeight!=32u || p.destinationX!=708 || p.destinationY!=308)
        return false;
    // The 30x30 source repaint carries an authentic unscaled 24x24 tile.
    if (!native_raw_partial_present_tile(
            1920,1080,700,300,730,330,96,64,p,true) ||
        p.copyWidth!=24u || p.copyHeight!=24u ||
        p.sourceX!=36u || p.sourceY!=20u ||
        p.destinationX!=703 || p.destinationY!=303)
        return false;
    if (native_raw_partial_present_tile(1920,1080,0,0,23,100,256,144,p) ||
        native_raw_partial_present_tile(1920,1080,0,0,100,23,256,144,p) ||
        native_raw_partial_present_tile(1920,1080,-1,0,100,100,256,144,p) ||
        native_raw_partial_present_tile(1920,1080,1800,0,1980,100,256,144,p) ||
        native_raw_partial_present_tile(1920,1080,0,0,0,100,256,144,p) ||
        native_raw_partial_present_tile(0xffffffffu,1080,0,0,1920,1080,256,144,p) ||
        native_raw_partial_present_tile(1920,1080,0,0,120,100,20,144,p))
        return false;
    return p.copyWidth == 0u && p.destinationX == 0;
}
static_assert(valid_raw_partial_present(), "source crop must bound RAW visual");
int main() { assert(valid_raw_partial_present()); }
