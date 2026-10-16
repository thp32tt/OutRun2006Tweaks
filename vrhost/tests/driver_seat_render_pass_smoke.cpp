#include "vr/game/driver_seat_render_pass.hpp"
#include <utility>

// Model native detours as move-only RAII owners. A failed second install must
// destroy the temporary first detour, not retain a visible half cockpit.
struct MockNativeHook {
    int* live = nullptr;
    MockNativeHook() = default;
    explicit MockNativeHook(int* p) noexcept : live(p) {
        if (live) ++*live;
    }
    MockNativeHook(const MockNativeHook&) = delete;
    MockNativeHook& operator=(const MockNativeHook&) = delete;
    MockNativeHook(MockNativeHook&& old) noexcept :
        live(std::exchange(old.live, nullptr)) {}
    MockNativeHook& operator=(MockNativeHook&& old) noexcept {
        if (this != &old) {
            if (live) --*live;
            live = std::exchange(old.live, nullptr);
        }
        return *this;
    }
    ~MockNativeHook() { if (live) --*live; }
    explicit operator bool() const noexcept { return live != nullptr; }
};
static int TestCockpitAtomicInstall() {
    int carLive = 0, occupantLive = 0, occupantCalls = 0;
    {
        MockNativeHook car{}, occupant{};
        if (InstallAtomicCockpitPair(car, occupant,
                [] { return MockNativeHook{}; },
                [&] { ++occupantCalls; return MockNativeHook{&occupantLive}; }))
            return 13;
        if (carLive || occupantLive || car || occupant || occupantCalls)
            return 14;
        if (InstallAtomicCockpitPair(car, occupant,
                [&] { return MockNativeHook{&carLive}; },
                [&] { ++occupantCalls; return MockNativeHook{}; }))
            return 15;
        if (carLive || occupantLive || car || occupant || occupantCalls != 1)
            return 16;
        if (!InstallAtomicCockpitPair(car, occupant,
                [&] { return MockNativeHook{&carLive}; },
                [&] { ++occupantCalls; return MockNativeHook{&occupantLive}; }))
            return 17;
        if (carLive != 1 || occupantLive != 1 || !car || !occupant ||
            occupantCalls != 2)
            return 18;
    }
    return carLive == 0 && occupantLive == 0 ? 0 : 19;
}

using namespace OutRunVR::DriverSeatRenderPass;
int main()
{
    if (const int failure = TestCockpitAtomicInstall()) return failure;
    if (!IsWorldOrCockpitPass() || !UseCockpitForCamera(true) ||
        UseCockpitForCamera(false))
        return 1;
    {
        ScopedSceneEffect effect{};
        if (IsWorldOrCockpitPass() || UseCockpitForCamera(true) ||
            SceneEffectDepth != 1)
            return 2;
        {
            // A nested HUD/flare pass must not reactivate the real seat.
            ScopedSceneEffect nested{};
            if (SceneEffectDepth != 2 || UseCockpitForCamera(true))
                return 3;
        }
        if (SceneEffectDepth != 1 || IsWorldOrCockpitPass())
            return 4;
    }
    if (!IsWorldOrCockpitPass() || SceneEffectDepth != 0 ||
        !UseCockpitForCamera(true))
        return 5;

    // The actual game effect callback first replaces the seat matrix with
    // the native short-near-plane view. A stale SceneEffectDepth during the
    // restoration would keep the world camera unshifted (regression).
    int cameraView = 2; // 2: native seat, 1: original game/effect camera.
    int failure = 0;
    auto recalculateView = [&](bool seatEligible) {
        cameraView = UseCockpitForCamera(seatEligible) ? 2 : 1;
    };
    RunSceneEffectThenRestoreView(
        [&]() {
            recalculateView(true);
            if (cameraView != 1 || SceneEffectDepth != 1)
                failure = 6;
            RunSceneEffectThenRestoreView(
                [&]() {
                    if (SceneEffectDepth != 2 || UseCockpitForCamera(true))
                        failure = 7;
                },
                [&]() {
                    recalculateView(true);
                    if (SceneEffectDepth != 1 || cameraView != 1)
                        failure = 8;
                });
            if (SceneEffectDepth != 1 || cameraView != 1)
                failure = 9;
        },
        [&]() {
            recalculateView(true);
            if (SceneEffectDepth != 0 || cameraView != 2)
                failure = 10;
        });
    if (failure)
        return failure;

    // Disabled/transitioning native seat must remain the original camera.
    RunSceneEffectThenRestoreView(
        [&]() {
            recalculateView(false);
            if (cameraView != 1 || SceneEffectDepth != 1)
                failure = 11;
        },
        [&]() {
            recalculateView(false);
            if (cameraView != 1 || SceneEffectDepth != 0)
                failure = 12;
        });
    if (failure)
        return failure;
    return 0;
}
