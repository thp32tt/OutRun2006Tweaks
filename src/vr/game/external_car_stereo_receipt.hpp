#pragma once
// Strict, per-DIP physical stereo verification for opt-in external vehicle.
// A legacy D3D9 HRESULT can reflect LEFT success while RIGHT failed.
#include <cstdint>

namespace OutRunVR::DinoSidecar {
struct ExternalStereoMeshReceipt final {
    std::uint64_t expectedPose=0;
    std::uint64_t observedPose=0;
    unsigned reports=0;
    bool leftSucceeded=false;
    bool rightSucceeded=false;
    bool stateRestored=false;
    bool geometryStereo=false; // original fixed-function per-eye matrices proved
    bool rightDrawFailed=false; // real RIGHT DIP HRESULT, not merely missing stereo proof
    bool Complete() const noexcept {
        return expectedPose!=0 && reports==1 &&
            observedPose==expectedPose && leftSucceeded &&
            rightSucceeded && stateRestored && geometryStereo;
    }
};
inline thread_local ExternalStereoMeshReceipt* ActiveExternalStereoMesh=nullptr;
class ScopedExternalStereoMeshReceipt final {
    ExternalStereoMeshReceipt* previous_;
public:
    explicit ScopedExternalStereoMeshReceipt(ExternalStereoMeshReceipt& receipt) noexcept
        : previous_(ActiveExternalStereoMesh) {
        ActiveExternalStereoMesh=&receipt;
    }
    ~ScopedExternalStereoMeshReceipt() noexcept {
        ActiveExternalStereoMesh=previous_;
    }
    ScopedExternalStereoMeshReceipt(const ScopedExternalStereoMeshReceipt&)=delete;
    ScopedExternalStereoMeshReceipt& operator=(const ScopedExternalStereoMeshReceipt&)=delete;
};
inline void RecordExternalStereoMeshPair(bool leftOk,bool rightOk,
    bool restored,std::uint64_t pose, bool geometryStereo=false,
    bool rightGpuFailure=false) noexcept {
    auto* receipt=ActiveExternalStereoMesh;
    if(!receipt)return;
    ++receipt->reports;
    receipt->observedPose=pose;
    receipt->leftSucceeded=leftOk;
    receipt->rightSucceeded=rightOk;
    receipt->stateRestored=restored;
    receipt->geometryStereo=geometryStereo;
    receipt->rightDrawFailed=rightGpuFailure;
}
} // namespace OutRunVR::DinoSidecar
