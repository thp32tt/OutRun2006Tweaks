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
    bool Complete() const noexcept {
        return expectedPose!=0 && reports==1 &&
            observedPose==expectedPose && leftSucceeded &&
            rightSucceeded && stateRestored;
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
    bool restored,std::uint64_t pose) noexcept {
    auto* receipt=ActiveExternalStereoMesh;
    if(!receipt)return;
    ++receipt->reports;
    receipt->observedPose=pose;
    receipt->leftSucceeded=leftOk;
    receipt->rightSucceeded=rightOk;
    receipt->stateRestored=restored;
}
} // namespace OutRunVR::DinoSidecar
