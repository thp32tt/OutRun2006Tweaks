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
// Compact failure proof retained for the native per-car diagnostic log.
// It is never a license to invoke the original callback after a partial DIP.
enum class ExternalEyeFailure : unsigned char {
    NotAttempted,None,MissingReport,MultipleReports,PoseMismatch,LeftFailed,
    RightGpuFailed,RightNotVerified,RestoreFailed,IdenticalEyeGeometry
};
inline ExternalEyeFailure ClassifyExternalEyeFailure(
    const ExternalStereoMeshReceipt& r) noexcept
{
    if(r.Complete())return ExternalEyeFailure::None;
    if(r.reports==0)return ExternalEyeFailure::MissingReport;
    // Keep a physical RIGHT GPU fault visible even when the renderer chain
    // accidentally publishes multiple (invalid) receipts for one DIP.
    if(r.rightDrawFailed)return ExternalEyeFailure::RightGpuFailed;
    if(r.reports!=1)return ExternalEyeFailure::MultipleReports;
    if(r.expectedPose==0 || r.observedPose!=r.expectedPose)
        return ExternalEyeFailure::PoseMismatch;
    if(!r.leftSucceeded)return ExternalEyeFailure::LeftFailed;
    if(r.rightDrawFailed)return ExternalEyeFailure::RightGpuFailed;
    if(!r.rightSucceeded)return ExternalEyeFailure::RightNotVerified;
    if(!r.stateRestored)return ExternalEyeFailure::RestoreFailed;
    if(!r.geometryStereo)return ExternalEyeFailure::IdenticalEyeGeometry;
    return ExternalEyeFailure::RightNotVerified;
}
inline const char* ExternalEyeFailureName(ExternalEyeFailure failure) noexcept {
    switch(failure) {
    case ExternalEyeFailure::NotAttempted:return "NOT_ATTEMPTED";
    case ExternalEyeFailure::None:return "STEREO_OK";
    case ExternalEyeFailure::MissingReport:return "NO_PHYSICAL_REPORT";
    case ExternalEyeFailure::MultipleReports:return "DUPLICATE_PHYSICAL_REPORT";
    case ExternalEyeFailure::PoseMismatch:return "POSE_MISMATCH";
    case ExternalEyeFailure::LeftFailed:return "LEFT_GPU_FAILED";
    case ExternalEyeFailure::RightGpuFailed:return "RIGHT_GPU_FAILED";
    case ExternalEyeFailure::RightNotVerified:return "RIGHT_NOT_VERIFIED";
    case ExternalEyeFailure::RestoreFailed:return "PHYSICAL_RESTORE_FAILED";
    case ExternalEyeFailure::IdenticalEyeGeometry:return "MONO_EYE_MATRICES";
    }
    return "UNKNOWN_EYE_FAILURE";
}
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
    // Multiple nested owner reports must never erase an earlier physical
    // RIGHT-eye HRESULT failure and incorrectly downgrade hard quarantine.
    receipt->rightDrawFailed = receipt->rightDrawFailed || rightGpuFailure;
}
} // namespace OutRunVR::DinoSidecar
