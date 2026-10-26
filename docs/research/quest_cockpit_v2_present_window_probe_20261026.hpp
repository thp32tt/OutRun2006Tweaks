// Quest cockpit V2: READ-ONLY frame-correlation research helper.
// No game hooks, no side effects, no camera changes, no wheel/hand data.
// Rejects ambiguous Present groups; only a diagnostic candidate, NOT a
// guarantee of Quest3 runtime equivalence or production admission.
#pragma once
#include <cstdint>

namespace quest_cockpit_research {

struct PresentWindow final {
    // Populated by a future explicit trace around game native 449050 entry/
    // exit, 49F3E0 player display, D3D9 BeginScene/EndScene, and Present.
    std::uint32_t gameRenderEntries = 0;
    std::uint32_t gameRenderExits = 0;
    std::uint32_t playerDisplayCallbacks = 0;
    std::uint32_t successfulBeginScene = 0;
    std::uint32_t successfulEndScene = 0;
    std::uint32_t distinctPlayerPointers = 0;
    std::uint32_t distinctPoseSequences = 0;
    std::uint32_t nativeCameraModeChanges = 0;
    bool nativeCameraModeOne = false;
    bool validStereoTracking = false;
    bool cullingCameraBorrowOverlapsNativeCamera = false;
    bool verifiedPlayerEventOwner = false;
};

enum class PresentWindowClass : std::uint8_t {
    IncompleteRender,         // missing/unbalanced render or scene boundaries
    NonPlayer,                // no verified player car display
    MultipleRenderOwners,     // ambiguous game frame(s) inside this Present
    MultipleOrMissingPoses,   // not one coherent OpenXR pose per Present
    MixedCameraOrBorrow,     // mode changed or mutable camera was borrowed
    ValidTraceCandidate       // diagnostic only: still needs HMD proof
};

constexpr PresentWindowClass Classify(const PresentWindow& w) noexcept {
    if (w.gameRenderEntries == 0 || w.gameRenderExits == 0 ||
        w.successfulBeginScene == 0 ||
        w.successfulBeginScene != w.successfulEndScene ||
        w.gameRenderEntries != w.gameRenderExits)
        return PresentWindowClass::IncompleteRender;
    if (w.gameRenderEntries != 1 || w.distinctPlayerPointers != 1)
        return PresentWindowClass::MultipleRenderOwners;
    if (!w.verifiedPlayerEventOwner || w.playerDisplayCallbacks == 0)
        return PresentWindowClass::NonPlayer;
    if (w.distinctPoseSequences != 1 || !w.validStereoTracking)
        return PresentWindowClass::MultipleOrMissingPoses;
    if (w.nativeCameraModeChanges != 0 ||
        !w.nativeCameraModeOne ||
        w.cullingCameraBorrowOverlapsNativeCamera)
        return PresentWindowClass::MixedCameraOrBorrow;
    return PresentWindowClass::ValidTraceCandidate;
}
constexpr PresentWindow kCandidate{1,1,1,2,2,1,1,0,true,true,false,true};
static_assert(Classify(kCandidate) == PresentWindowClass::ValidTraceCandidate);
static_assert(Classify({1,1,1,1,1,1,1,0,true,true,true,true}) ==
              PresentWindowClass::MixedCameraOrBorrow);
static_assert(Classify({2,2,1,2,2,1,1,0,true,true,false,true}) ==
              PresentWindowClass::MultipleRenderOwners);
static_assert(Classify({1,1,1,2,1,1,1,0,true,true,false,true}) ==
              PresentWindowClass::IncompleteRender);
} // namespace quest_cockpit_research
