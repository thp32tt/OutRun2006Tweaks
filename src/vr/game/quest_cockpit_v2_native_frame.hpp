// QuestCockpitV2: original Windows game-render frame correlation (read-only).
// FrameRender RVA 0x49050 and callback RVA 0x9F3E0 are independent of D3D9
// BeginScene, EndScene and Present; this tracer NEVER admits cockpit gameplay.
#pragma once
#include <atomic>
#include <cstdint>

namespace OutRunVR::QuestCockpitV2 {
struct NativeWindow {
    std::uint64_t ordinal=0, firstEpoch=0,lastEpoch=0;
    std::uint32_t enters=0,ends=0,playerCallbacks=0,playerCars=0;
    std::uint32_t unownedCallbacks=0,unmatchedEnds=0,nestedEntries=0;
    bool overflow=false;
};

class NativeFrameTracker final {
    NativeWindow window_{};
    std::uint64_t ordinal_=0, activeEpoch_=0;
    std::uint32_t depth_=0;
    void Bump(std::uint32_t& n) noexcept {
        if(n<4096u)++n; else window_.overflow=true;
    }
public:
    void Clear() noexcept {window_={};activeEpoch_=0;depth_=0;}
    bool Active() const noexcept {return depth_>0 && activeEpoch_!=0;}
    std::uint64_t ActiveEpoch() const noexcept {return Active()?activeEpoch_:0;}
    void OnFrameEnter(std::uint64_t epoch) noexcept {
        Bump(window_.enters);
        if(depth_>0) Bump(window_.nestedEntries);
        if(depth_<4096u)++depth_; else window_.overflow=true;
        activeEpoch_=epoch;
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
        if(!Active()) {Bump(window_.unmatchedEnds);return;}
        Bump(window_.ends);
        if(--depth_==0)activeEpoch_=0;
    }
    NativeWindow OnPresent() noexcept {
        NativeWindow snapshot=window_;
        snapshot.ordinal=++ordinal_;
        window_={};
        return snapshot;
    }
};
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
