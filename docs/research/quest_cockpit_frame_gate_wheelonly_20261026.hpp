// Quest cockpit frame admission: research-only C++17, not production-wired.
// Quest original: PcSceneRenderer::render_frame ELF 0x10CBE9C.
// The game-frame boundary source and owner mapping MUST be verified before use.
#pragma once
#include <cstddef>
#include <cstdint>
namespace quest_cockpit_research {
struct QuestNativeGate {
    std::uint32_t renderEventFlags = 0;
    bool cockpitEnabled = false;
    bool providerValid = false;
    std::size_t cameraBytes = 0;
    std::uint8_t nativeCameraMode = 0;
};
constexpr bool NativeGate(const QuestNativeGate& x) noexcept {
    return (x.renderEventFlags & ~std::uint32_t{2}) == 0x10u &&
           x.cockpitEnabled && x.providerValid &&
           x.cameraBytes > 0x34au && x.nativeCameraMode == 1;
}
struct PcFrameSample {
    std::uint64_t gameFrameSerial = 0;
    std::uintptr_t playerId = 0;
    bool optionEnabled = false;
    bool playable = false;
    bool carAndCameraValid = false;
    std::uint8_t nativeCameraMode = 0;
};
// Conservative PC port CANDIDATE: sample at a verified game-render boundary,
// never use an XR pose ID or Present number without game-frame correlation.
// Any conflicting camera/vehicle value within a frame invalidates the frame.
// SceneEffect is never allowed to borrow a cockpit camera. No game writes.
class FrameDecision final {
    bool initialized_ = false;
    bool eligible_ = false;
    std::uint64_t serial_ = 0;
    std::uintptr_t player_ = 0;
    std::uint8_t mode_ = 0;
public:
    bool Observe(const PcFrameSample& x) noexcept {
        if (!initialized_ || x.gameFrameSerial != serial_) {
            initialized_ = true;
            serial_ = x.gameFrameSerial;
            player_ = x.playerId;
            mode_ = x.nativeCameraMode;
            eligible_ = x.playerId != 0 && x.optionEnabled && x.playable &&
                        x.carAndCameraValid && x.nativeCameraMode == 1;
            return eligible_;
        }
        if (x.playerId != player_ || x.nativeCameraMode != mode_ ||
            !x.optionEnabled || !x.playable || !x.carAndCameraValid)
            eligible_ = false;
        return eligible_;
    }
    bool WorldPass(bool sceneEffect) const noexcept {
        return initialized_ && eligible_ && !sceneEffect;
    }
    bool Active() const noexcept { return initialized_ && eligible_; }
    void Reset() noexcept { initialized_ = eligible_ = false; }
};
static_assert(NativeGate({0x10,true,true,0x400,1}));
static_assert(NativeGate({0x12,true,true,0x400,1}));
static_assert(!NativeGate({0x11,true,true,0x400,1}));
static_assert(!NativeGate({0x10,true,true,0x400,2}));
static_assert(!NativeGate({0x10,true,true,0x34a,1}));
} // namespace quest_cockpit_research
