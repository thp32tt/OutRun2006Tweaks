// QuestCockpitV2: original Windows game-render frame correlation (read-only).
// FrameRender RVA 0x49050 and callback RVA 0x9F3E0 are independent of D3D9
// BeginScene, EndScene and Present; this tracer NEVER admits cockpit gameplay.
#pragma once
#include <atomic>
#include <array>
#include <cstdint>
#include <limits>

namespace OutRunVR::QuestCockpitV2 {
struct NativeWindow {
    std::uint64_t ordinal=0, firstEpoch=0,lastEpoch=0;
    std::uint32_t enters=0,ends=0,playerCallbacks=0,playerCars=0;
    std::uint32_t unownedCallbacks=0,unmatchedEnds=0,nestedEntries=0;
    bool overflow=false;
};

class NativeFrameTracker final {
    // An original PC render callback may recurse. A single active epoch
    // would retain the child's identity after its return and could alias
    // the parent's car/robot work with the wrong XR/native frame.
    static constexpr std::size_t MaxNestedFrames=32u;
    NativeWindow window_{};
    std::uint64_t ordinal_=0;
    std::array<std::uint64_t,MaxNestedFrames> epochs_{};
    std::uint32_t depth_=0, overflowDepth_=0;
    bool rejectUntilEmpty_=false, saturated_=false;
    void Bump(std::uint32_t& n) noexcept {
        if(n<4096u)++n; else window_.overflow=true;
    }
public:
    void Clear() noexcept {
        window_={};epochs_.fill(0);depth_=overflowDepth_=0;
        rejectUntilEmpty_=saturated_=false;
    }
    bool Active() const noexcept {
        return !rejectUntilEmpty_ && !saturated_ &&
            overflowDepth_==0 && depth_>0 && epochs_[depth_-1]!=0;
    }
    std::uint64_t ActiveEpoch() const noexcept {
        return Active()?epochs_[depth_-1]:0;
    }
    void OnFrameEnter(std::uint64_t epoch) noexcept {
        Bump(window_.enters);
        if(depth_ || overflowDepth_)Bump(window_.nestedEntries);
        if(epoch==0) {
            // Never treat a missing native frame as a usable owner.
            rejectUntilEmpty_=true;window_.overflow=true;
        }
        if(overflowDepth_ || depth_==MaxNestedFrames) {
            // Preserve balanced end accounting without indexing past
            // the bounded stack. No cockpit admission until fully unwound.
            rejectUntilEmpty_=true;window_.overflow=true;
            if(overflowDepth_<(std::numeric_limits<std::uint32_t>::max)())
                ++overflowDepth_;
            else saturated_=true;
        } else {
            epochs_[depth_++]=epoch;
        }
        if(window_.firstEpoch==0)window_.firstEpoch=epoch;
        window_.lastEpoch=epoch;
    }
    void OnPlayerCallback() noexcept {
        if(!Active()) {Bump(window_.unownedCallbacks);return;}
        Bump(window_.playerCallbacks);
    }
    void OnPlayerCar() noexcept {
        if(!Active())return;
        Bump(window_.playerCars);
    }
    void OnFrameEnd() noexcept {
        // A suppressed frame is still a real unmatched-to-Active frame.
        // Pop it before the parent so its epoch cannot leak outward.
        if(overflowDepth_>0) {
            Bump(window_.ends);
            --overflowDepth_;
        } else if(depth_>0) {
            Bump(window_.ends);
            epochs_[--depth_]=0;
        } else {
            Bump(window_.unmatchedEnds);
            return;
        }
        if(depth_==0 && overflowDepth_==0 && !saturated_)
            rejectUntilEmpty_=false;
    }
    NativeWindow OnPresent() noexcept {
        NativeWindow snapshot=window_;
        snapshot.ordinal=++ordinal_;
        window_={};
        // Present is not the original native frame boundary: retain
        // any active stack and failure-to-admit state across Present.
        return snapshot;
    }
};
// A newly installed Quest seat may not yet have been consumed by the
// original 485FE0 camera tick (which precedes 449050 frame rendering).
// Native eye transforms are admitted only on a later camera-to-frame cycle
// that observes the same previously injected table; fallback is stock R26.
class NativeSeatCameraTickGate final {
    std::atomic<bool> ready_{false};
public:
    void Invalidate() noexcept {
        ready_.store(false,std::memory_order_release);
    }
    void AfterSeatSync(bool previouslyPatched,bool sameInput,
                       bool apkNativeCamera,bool afterCameraTick) noexcept {
        ready_.store(previouslyPatched && sameInput &&
                     apkNativeCamera && afterCameraTick,
                     std::memory_order_release);
    }
    bool Ready() const noexcept {
        return ready_.load(std::memory_order_acquire);
    }
};
inline NativeSeatCameraTickGate NativeSeatCameraTick{};
inline bool NativeQuestEyeEligible(bool gameModeOne,
                                   bool originalHooksReady,
                                   bool installedSeatReady) noexcept {
    return gameModeOne && originalHooksReady && installedSeatReady;
}
// Ready ONLY when the exact retail EXE game-frame callback triad installed.
inline std::atomic<bool> NativeOriginalHooksReady{false};
inline std::atomic<std::uint64_t> NativeEpochCounter{0};
inline thread_local NativeFrameTracker NativeFrameInstance{};
inline NativeFrameTracker& NativeFrameTrace() noexcept {
    return NativeFrameInstance;
}
inline std::uint64_t NextVerifiedNativeEpoch() noexcept {
    const std::uint64_t next=NativeEpochCounter.fetch_add(
        1,std::memory_order_relaxed)+1;
    return next?next:NativeEpochCounter.fetch_add(
        1,std::memory_order_relaxed)+1;
}
}
