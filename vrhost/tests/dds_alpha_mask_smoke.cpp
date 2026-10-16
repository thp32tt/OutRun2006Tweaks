#include "vr/game/dds_alpha_mask_policy.hpp"

int main()
{
    using OutRunVR::DdsAlphaMask::Classify;
    using OutRunVR::DdsAlphaMask::Rgb32Intent;
    // Opaque car/selector RGB whose DDS writer left the A8 mask in place.
    if (Classify(0x40u, 32, 0xff000000u) != Rgb32Intent::Opaque ||
        Classify(0x40u, 32, 0u) != Rgb32Intent::Opaque)
        return 1;
    // Real transparency must survive on both BGRA and RGBA mask layouts.
    if (Classify(0x41u, 32, 0xff000000u) != Rgb32Intent::Alpha)
        return 2;
    // Broken/mismatched source layouts are not implicitly promoted.
    if (Classify(0x41u, 32, 0u) != Rgb32Intent::Unsupported ||
        Classify(0x00u, 32, 0xff000000u) != Rgb32Intent::Unsupported ||
        Classify(0x40u, 24, 0xff000000u) != Rgb32Intent::Unsupported ||
        Classify(0x40u, 32, 0x000000ffu) != Rgb32Intent::Unsupported)
        return 3;
    return 0;
}
