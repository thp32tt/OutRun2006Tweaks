#pragma once
// Dino basic model0 (guest layout 0x5B0CB8): original body 0x10000 and
// mode1-only object 0x10010. The modded PMT must be externally verified;
// this helper never loads, mutates or redistributes proprietary model data.
namespace OutRunVR::DinoMode1 {
    constexpr bool SelectReplacement(bool optedIn, bool cockpitEligible,
        bool racing, bool originalFrameActive, bool stereoPoseValid,
        int signedCarModel, int cameraMode) noexcept
    {
        return optedIn && cockpitEligible && racing &&
            originalFrameActive && stereoPoseValid &&
            signedCarModel == 0 && cameraMode == 1;
    }
}
