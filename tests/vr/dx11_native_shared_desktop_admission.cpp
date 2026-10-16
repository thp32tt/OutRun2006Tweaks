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
    // Strictly fail closed for normal gameplay/fallback, unsupported scene
    // draws, cropped menu Presents, partial dirty updates and non-BGRA/MSAA.
    for (unsigned mask = 0; mask < 9; ++mask) {
        bool f[9]{true,true,true,true,true,true,true,true,true};
        f[mask] = false;
        assert(!allowed(f[0],f[1],f[2],f[3],f[4],f[5],f[6],f[7],f[8],
                        3440,1440,3));
    }
    assert(!allowed(true,true,true,true,true,true,true,true,true,0,1440,3));
    assert(!allowed(true,true,true,true,true,true,true,true,true,3440,0,3));
    assert(!allowed(true,true,true,true,true,true,true,true,true,3440,1440,0));
}
