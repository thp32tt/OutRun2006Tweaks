#include "../../src/vr/d3d11/native_game_shared_desktop_admission.hpp"
#include <cassert>
using outrun::vr::dx11::live_game_frame::NativeSharedDesktopAdmission;
int main() {
    auto allowed = [](bool opt, bool full, bool complete, bool writable,
                      bool owner, bool region, bool dirty, bool bgra,
                      bool single, unsigned w, unsigned h, unsigned gen) {
        return NativeSharedDesktopAdmission::allowed(
            opt,full,complete,writable,owner,region,dirty,bgra,single,w,h,gen);
    };
    assert(allowed(true,true,true,true,true,true,true,true,true,3440,1440,3));
    // D3DFMT_A8R8G8B8=21 and X8R8G8B8=22 are valid full-screen
    // desktop destinations. Unsupported format conversions stay on D3D9.
    constexpr unsigned a8 = 21u, x8 = 22u;
    assert(NativeSharedDesktopAdmission::destination_compatible(a8,a8,x8));
    assert(NativeSharedDesktopAdmission::destination_compatible(x8,a8,x8));
    assert(!NativeSharedDesktopAdmission::destination_compatible(23u,a8,x8));
    assert(allowed(true,true,true,true,true,true,true,
                   NativeSharedDesktopAdmission::destination_compatible(x8,a8,x8),
                   true,3440,1440,3));
    assert(!allowed(true,true,true,true,true,true,true,
                    NativeSharedDesktopAdmission::destination_compatible(23u,a8,x8),
                    true,3440,1440,3));
    // Strictly fail closed for default-off gameplay/fallback, unsupported
    // scene draws, unknown dirty regions and non-BGRA/MSAA.
    for (unsigned mask = 0; mask < 9; ++mask) {
        bool f[9]{true,true,true,true,true,true,true,true,true};
        f[mask] = false;
        assert(!allowed(f[0],f[1],f[2],f[3],f[4],f[5],f[6],f[7],f[8],
                        3440,1440,3));
    }
    assert(!allowed(true,true,true,true,true,true,true,true,true,0,1440,3));
    assert(!allowed(true,true,true,true,true,true,true,true,true,3440,0,3));
    assert(!allowed(true,true,true,true,true,true,true,true,true,3440,1440,0));
    // Exact game Present source crop: GPU StretchRect updates the cropped
    // area only, not the rest of the original D3D9 menu/race backbuffer.
    using outrun::vr::dx11::live_game_frame::GameNativePresentRegion;
    using outrun::vr::dx11::live_game_frame::GameNativePartialDirtySelection;
    constexpr GameNativePresentRegion full{0,0,3440,1440};
    constexpr GameNativePresentRegion crop{100,50,3300,1390};
    constexpr GameNativePresentRegion tile{200,100,400,300};
    constexpr GameNativePartialDirtySelection noTile{};
    constexpr GameNativePartialDirtySelection oneTile{tile,true};
    auto select = [](GameNativePresentRegion visible, bool hasDirty,
                     bool oneDirty, bool fullDirty, bool cropDirty,
                     bool partitionCrop, GameNativePartialDirtySelection partial) {
        return NativeSharedDesktopAdmission::select_region(
            3440,1440,visible,hasDirty,oneDirty,fullDirty,cropDirty,
            partitionCrop,partial);
    };
    const auto whole = select(full,false,false,false,false,false,noTile);
    assert(whole.valid && whole.source.right == 3440 && whole.source.bottom == 1440);
    const auto cropped = select(crop,false,false,false,false,false,noTile);
    assert(cropped.valid && cropped.source.left == 100 && cropped.source.top == 50);
    const auto completeCrop = select(crop,true,true,false,true,false,noTile);
    assert(completeCrop.valid && completeCrop.source.right == 3300);
    assert(select(crop,true,false,true,false,false,noTile).valid);
    assert(select(crop,true,false,false,false,true,noTile).valid);
    const auto dirty = select(crop,true,true,false,false,false,oneTile);
    assert(dirty.valid && dirty.source.left == 200 &&
           dirty.source.right == 400 && dirty.source.bottom == 300);
    // CopySubresourceRegion and the subsequent StretchRect share this exact
    // rect, so the GPU transfer can skip all untouched source/backbuffer pixels.
    assert((dirty.source.right - dirty.source.left) *
           (dirty.source.bottom - dirty.source.top) == 40000);
    assert((cropped.source.right - cropped.source.left) *
           (cropped.source.bottom - cropped.source.top) < 3440 * 1440);
    // Contradictory dirty metadata must never authorize a partial GPU copy.
    assert(!select(crop,false,true,false,false,false,oneTile).valid);
    assert(!select(crop,false,false,true,false,false,noTile).valid);
    assert(!select(crop,false,false,false,true,false,noTile).valid);
    assert(!select(crop,false,false,false,false,true,noTile).valid);
    assert(!select(crop,true,false,false,false,false,oneTile).valid);
    assert(!select(crop,true,true,false,false,false,noTile).valid);
    assert(!select(crop,true,false,false,false,false,noTile).valid);
    const GameNativePartialDirtySelection foreign{{10,10,400,300},true};
    assert(!select(crop,true,true,false,false,false,foreign).valid);
    const auto malformed = NativeSharedDesktopAdmission::select_region(
        3440,1440,{0,-1,3440,1440},false,false,false,false,false,noTile);
    assert(!malformed.valid);
}
