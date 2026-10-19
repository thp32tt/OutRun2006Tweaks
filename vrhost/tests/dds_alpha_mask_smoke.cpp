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
    // 16-bit selector source: RGB-only high alpha-shaped bits must remain
    // opaque X1, while true declared A1/A4 remains alpha-bearing.
    using OutRunVR::DdsAlphaMask::Classify16;
    using OutRunVR::DdsAlphaMask::Rgb16Intent;
    if (Classify16(0x40u, 16, 0x7c00, 0x03e0, 0x001f, 0x8000) !=
            Rgb16Intent::Opaque555 ||
        Classify16(0x41u, 16, 0x7c00, 0x03e0, 0x001f, 0x8000) !=
            Rgb16Intent::Alpha1555 ||
        Classify16(0x41u, 16, 0x0f00, 0x00f0, 0x000f, 0xf000) !=
            Rgb16Intent::Alpha4444 ||
        Classify16(0x40u, 16, 0xf800, 0x07e0, 0x001f, 0) !=
            Rgb16Intent::Rgb565)
        return 4;
    // A4 mask without declared alpha, conflicting FOURCC, and invalid
    // 5:6:5 alpha requests use the unchanged native-D3DX failure path.
    if (Classify16(0x40u, 16, 0x0f00, 0x00f0, 0x000f, 0xf000) !=
            Rgb16Intent::Unsupported ||
        Classify16(0x44u, 16, 0x7c00, 0x03e0, 0x001f, 0x8000) !=
            Rgb16Intent::Unsupported ||
        Classify16(0x41u, 16, 0xf800, 0x07e0, 0x001f, 0) !=
            Rgb16Intent::Unsupported ||
        Classify16(0x41u, 16, 0x7c00, 0x03e0, 0x001f, 0) !=
            Rgb16Intent::Unsupported)
        return 5;
    return 0;
}
