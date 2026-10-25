#include "../src/vr/d3d11/native_game_shared_desktop_source.hpp"
#include <cassert>
using namespace outrun::vr::dx11::live_game_frame;
int main() {
    using T = NativeSharedDesktopSourceTransfer;
    // One native menu/car/race surface with a full mip chain still has a
    // publishable mip-zero color frame, regardless of RT/SRV view semantics.
    assert(native_shared_desktop_source_transfer(1, 1, 1, 0, true, false) == T::Copy);
    assert(native_shared_desktop_source_transfer(8, 1, 1, 0, true, false) == T::Copy);
    assert(native_shared_desktop_source_transfer(8, 1, 1, 0, false, false) == T::Copy);
    // No arbitrary array/eye selection or unproved multisample resolve.
    assert(native_shared_desktop_source_transfer(8, 2, 1, 0, true, false) == T::Reject);
    assert(native_shared_desktop_source_transfer(8, 1, 4, 0, true, true) == T::Reject);
    assert(native_shared_desktop_source_transfer(1, 1, 4, 0, true, true) == T::Resolve);
    assert(native_shared_desktop_source_transfer(1, 1, 4, 0, true, false) == T::Reject);
    assert(native_shared_desktop_source_transfer(0, 1, 1, 0, true, false) == T::Reject);
    assert(native_shared_desktop_source_transfer(1, 1, 1, 1, true, false) == T::Reject);
}
