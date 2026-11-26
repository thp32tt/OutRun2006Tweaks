#pragma once
#include <cstdint>

namespace OutRunVR::DinoSidecar {
// One receipt for the entire car, never one receipt per physical DIP.
struct IsolatedVehicleKey {
    std::uint64_t resource=0, boundary=0, present=0, nativeFrame=0, pose=0;
    std::uintptr_t player=0;
    bool Same(const IsolatedVehicleKey& b) const noexcept {
        return resource&&present&&nativeFrame&&pose&&player&&
            resource==b.resource&&boundary==b.boundary&&present==b.present&&
            nativeFrame==b.nativeFrame&&pose==b.pose&&player==b.player;
    }
};
enum class IsolatedStageResult { Unavailable, Complete, DirtyRestore };
template<class Current,class StageEye>
IsolatedStageResult StageWholeIsolatedVehicle(Current current,StageEye stageEye) noexcept {
    if(!current())return IsolatedStageResult::Unavailable;
    for(unsigned eye=0;eye<2;++eye) {
        const auto result=stageEye(eye);
        if(result!=IsolatedStageResult::Complete)return result;
        if(!current())return IsolatedStageResult::Unavailable;
    }
    return IsolatedStageResult::Complete;
}
// The target is a host-unpublished transport slot, never a game eye.
// An unsuccessful candidate transfer is overwritten by BOTH stock eyes,
// not by just the missing eye. Only a completed pair may arm its fence.
enum class IsolatedPairTransfer { Candidate, Stock, CopyFailed, FenceFailed, Retired };
template<class OwnerCurrent,class CandidateCurrent,class CopyEye,class Fence>
IsolatedPairTransfer TransferIsolatedPair(OwnerCurrent ownerCurrent,
    CandidateCurrent candidateCurrent,CopyEye copyEye,Fence fence) noexcept {
    if(!ownerCurrent())return IsolatedPairTransfer::Retired;
    bool candidate=candidateCurrent();
    if(candidate) {
        for(unsigned eye=0;eye<2;++eye) {
            if(!ownerCurrent())return IsolatedPairTransfer::Retired;
            if(!candidateCurrent()||!copyEye(true,eye)) {candidate=false;break;}
            if(!ownerCurrent())return IsolatedPairTransfer::Retired;
            if(!candidateCurrent()){candidate=false;break;}
        }
    }
    // A receipt can be retired without replacing the device. If that
    // occurs before the fence, overwrite BOTH unpublished candidate eyes.
    if(candidate&&!candidateCurrent())candidate=false;
    if(!candidate) {
        for(unsigned eye=0;eye<2;++eye) {
            if(!ownerCurrent())return IsolatedPairTransfer::Retired;
            if(!copyEye(false,eye))
                return ownerCurrent()?IsolatedPairTransfer::CopyFailed:IsolatedPairTransfer::Retired;
            if(!ownerCurrent())return IsolatedPairTransfer::Retired;
        }
    }
    if(!ownerCurrent())return IsolatedPairTransfer::Retired;
    if(!fence())return ownerCurrent()?IsolatedPairTransfer::FenceFailed:IsolatedPairTransfer::Retired;
    if(!ownerCurrent())return IsolatedPairTransfer::Retired;
    // The EVENT Issue itself may synchronously invalidate the scene
    // receipt. Never certify that slot; its owner must quarantine it.
    if(candidate&&!candidateCurrent())return IsolatedPairTransfer::FenceFailed;
    return candidate?IsolatedPairTransfer::Candidate:IsolatedPairTransfer::Stock;
}
} // namespace OutRunVR::DinoSidecar
