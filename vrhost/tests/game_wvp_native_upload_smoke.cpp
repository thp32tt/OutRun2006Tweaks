#include "vr/game/game_wvp_native_upload.hpp"
#include <iostream>

using namespace OutRunVR::GameWvpNative;
int main() {
    ScratchBank bank{};
    if (!MayPublishReturnedWvp(true, 1, 1) ||
        MayPublishReturnedWvp(false, 1, 1) ||
        MayPublishReturnedWvp(true, 1, 2) ||
        MayPublishReturnedWvp(true, 0, 0)) return 1;
    {
        ScopedFrame outer(bank);
        if (!outer.data() || bank.depth != 1) return 2;
        outer.data()[64u * 4u] = 11.f;
        {
            ScopedFrame inner(bank);
            if (!inner.data() || inner.data() == outer.data() ||
                bank.depth != 2) return 3;
            inner.data()[64u * 4u] = 22.f;
            if (outer.data()[64u * 4u] != 11.f ||
                inner.data()[64u * 4u] != 22.f) return 4;
            // A nested game upload has its own D3D9 source; returning from
            // the older native setter must not restore a stale game WVP.
            if (MayPublishReturnedWvp(true, 1, 2) ||
                !MayPublishReturnedWvp(true, 2, 2)) return 5;
            {
                ScopedFrame third(bank);
                ScopedFrame fourth(bank);
                if (!third.data() || !fourth.data() ||
                    third.data() == fourth.data() || bank.depth != 4)
                    return 6;
                ScopedFrame overflow(bank);
                if (overflow.data() || bank.depth != 4) return 7;
            }
            if (bank.depth != 2 || outer.data()[64u * 4u] != 11.f ||
                inner.data()[64u * 4u] != 22.f) return 8;
        }
        if (bank.depth != 1 || outer.data()[64u * 4u] != 11.f)
            return 9;
    }
    if (bank.depth != 0) return 10;
    {
        ScopedFrame reuse(bank);
        if (!reuse.data() || bank.depth != 1) return 11;
    }
    if (bank.depth != 0) return 12;
    std::cout << "R84 world native c64 upload reentrancy PASS\n";
    return 0;
}
