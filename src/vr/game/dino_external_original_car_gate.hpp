#pragma once
// Pure admission logic for replacing ONLY the original playable Dino player
// display callback (PC retail 0x49F3E0). Never suppress a game callback just
// because an external OVC file exists: a successful physical draw is required.
#include <cstdint>
namespace OutRunVR::DinoSidecar {
struct OriginalCarGate final {
    bool optedIn=false,ownedPlayer=false,gameplay=false,cockpitModeOne=false;
    bool validStereo=false,nativeFrameActive=false,deviceReady=false;
    std::uint64_t ticketEpoch=0,liveEpoch=0;
    std::uint64_t ticketPose=0,livePose=0;
};
inline bool CanReplaceOriginalCar(const OriginalCarGate& gate) noexcept {
    return gate.optedIn && gate.ownedPlayer && gate.gameplay &&
        gate.cockpitModeOne && gate.validStereo && gate.nativeFrameActive &&
        gate.deviceReady && gate.ticketEpoch!=0 &&
        gate.ticketEpoch==gate.liveEpoch && gate.ticketPose!=0 &&
        gate.ticketPose==gate.livePose;
}
inline bool SuppressOriginalCarAfterExternalDraw(
    const OriginalCarGate& gate, bool externalSubmittedAndStateRestored) noexcept
{
    return CanReplaceOriginalCar(gate) && externalSubmittedAndStateRestored;
}
} // namespace OutRunVR::DinoSidecar
