#pragma once
// QuestCockpitV2 P0: read-only, bounded and thread-local Present correlation.
// A Present is NOT verified original game frame_render_449050 ownership.
// This probe MUST NEVER admit a cockpit render, modify a car or change FFB.
#include <cstdint>
namespace OutRunVR::QuestCockpitV2 {
struct Sample {
    std::uint64_t ordinal=0, firstPoseEpoch=0, lastPoseEpoch=0;
    std::uint32_t begins=0, ends=0, failedEnds=0, worldCameras=0,
        effectCameras=0, borrowedCameras=0, playerCars=0,
        firstPose=0, lastPose=0;
    std::uint8_t firstMode=0, lastMode=0;
    bool sawPose=false, sawMode=false, poseChanged=false,
        modeChanged=false, overflow=false;
};
class Probe final {
    Sample s_{};
    std::uint64_t ordinal_=0;
    void Bump(std::uint32_t& x) noexcept {
        if(x<4096) ++x;
        else s_.overflow=true;
    }
public:
    void Clear() noexcept { s_={}; }
    void OnBegin(std::uint32_t pose, std::uint64_t epoch) noexcept {
        Bump(s_.begins);
        if(!s_.sawPose) {
            s_.sawPose=true; s_.firstPose=pose; s_.firstPoseEpoch=epoch;
        } else if(s_.firstPose!=pose || s_.firstPoseEpoch!=epoch)
            s_.poseChanged=true;
        s_.lastPose=pose; s_.lastPoseEpoch=epoch;
    }
    void OnEnd(bool success) noexcept {
        Bump(s_.ends); if(!success) Bump(s_.failedEnds);
    }
    void ObserveMode(std::uint8_t mode) noexcept {
        if(!s_.sawMode) {s_.sawMode=true;s_.firstMode=mode;}
        else if(s_.firstMode!=mode) s_.modeChanged=true;
        s_.lastMode=mode;
    }
    void OnCamera(std::uint8_t mode,bool borrowed,bool effect) noexcept {
        if(effect) Bump(s_.effectCameras); else Bump(s_.worldCameras);
        if(borrowed) Bump(s_.borrowedCameras);
        ObserveMode(mode);
    }
    void OnPlayerCar(std::uint8_t mode) noexcept {
        Bump(s_.playerCars); ObserveMode(mode);
    }
    Sample OnPresent() noexcept {
        s_.ordinal=++ordinal_;
        const Sample out=s_;
        Clear(); return out;
    }
};
// Events from another thread intentionally do not merge. The logs expose
// calling thread ID, not a proven global game-render/Present pairing.
inline Probe& ThreadProbe() noexcept {
    static thread_local Probe probe{};
    return probe;
}
}
