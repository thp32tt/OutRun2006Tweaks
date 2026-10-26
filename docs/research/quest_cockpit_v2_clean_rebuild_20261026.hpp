// Replacement Quest cockpit V2 frame contract, research-only, standalone C++17.
// No dependency on legacy driver_seat_camera_math, hand input or wheel steering.
// NOT registered as a Windows hook. Compiling this file does not enable cockpit.
// The renderer must supply a verified GAME render epoch; VR Present and pose
// sequences are NOT interchangeable with game epochs.
#pragma once
#include <cstdint>
#include <cstddef>

namespace OutRunVR::QuestCockpitV2 {

struct FrameInput {
    std::uint64_t gameEpoch = 0;        // from a verified game render boundary
    std::uint64_t headPoseSequence = 0; // XR snapshot correlated to this frame
    std::uint32_t xrSpaceGeneration = 0;
    std::uintptr_t player = 0;
    std::uint8_t nativeCameraMode = 0;  // EvWorkCamera::cam_mode_34A
    bool requested = false;
    bool gameplay = false;
    bool worldPass = false;             // excludes HUD, menu and SceneEffect
    bool carAndCameraValid = false;
    bool stereoTrackingValid = false;
    bool verifiedRenderOwner = false;   // PC equivalent of Quest event scope
};

struct SnapshotKey {
    std::uint64_t gameEpoch = 0;
    std::uint64_t headPoseSequence = 0;
    std::uint32_t xrSpaceGeneration = 0;
    std::uintptr_t player = 0;
};

// Pure admission policy, not a substitute for source/clock verification.
// Native Quest render_frame additionally checks (eventFlags&~2)==0x10;
// callers must prove their equivalent world-event owner before setting
// verifiedRenderOwner. The flags are NOT PC STATE_GAME/FrameDescriptor flags.
constexpr bool Eligible(const FrameInput& f) noexcept {
    return f.gameEpoch != 0 && f.headPoseSequence != 0 &&
           f.player != 0 && f.nativeCameraMode == 1 &&
           f.requested && f.gameplay && f.worldPass &&
           f.carAndCameraValid && f.stereoTrackingValid &&
           f.verifiedRenderOwner;
}

// A changed input during the same game epoch irrevocably invalidates it;
// re-enabling is possible only at the next *verified game* epoch. This avoids
// different decisions for left/right eyes or camera/full-car/driver hooks.
class Decision final {
    SnapshotKey key_{};
    bool seen_ = false;
    bool admitted_ = false;
public:
    void Reset() noexcept { key_ = {}; seen_ = admitted_ = false; }
    bool BeginOrObserve(const FrameInput& f) noexcept {
        const bool newEpoch = !seen_ || f.gameEpoch != key_.gameEpoch;
        if (newEpoch) {
            seen_ = true;
            key_ = {f.gameEpoch,f.headPoseSequence,f.xrSpaceGeneration,f.player};
            admitted_ = Eligible(f);
        } else if (f.player != key_.player ||
                   f.headPoseSequence != key_.headPoseSequence ||
                   f.xrSpaceGeneration != key_.xrSpaceGeneration ||
                   !Eligible(f)) {
            admitted_ = false;
        }
        return admitted_;
    }
    bool WorldOnly(bool isSceneEffectOrHud) const noexcept {
        return admitted_ && !isSceneEffectOrHud;
    }
    bool Active() const noexcept { return admitted_; }
    SnapshotKey Key() const noexcept { return key_; }
};

// Prevent combining gameplay decisions of different game-frame owners.
// Quest body matrix_F0 identity is a scoped render-only transaction;
// the implementation must not modify persistent game physics data.
static_assert(Eligible({1,7,2,0x1234,1,true,true,true,true,true,true}));
static_assert(!Eligible({1,7,2,0x1234,2,true,true,true,true,true,true}));
static_assert(!Eligible({1,7,2,0x1234,1,true,true,false,true,true,true}));
static_assert(!Eligible({1,7,2,0x1234,1,true,true,true,true,true,false}));
} // namespace OutRunVR::QuestCockpitV2
