#include "vr/ipc/shadow_progress.hpp"

#include <cassert>
#include <cstdint>

int main()
{
    using namespace OutRunVR::IpcV3;
    const ShadowFrameStamp first{101, 21, 1};
    ShadowFrameStamp published{};
    assert(ShadowFrameNeedsPublish(first, published));
    published = first;
    assert(!ShadowFrameNeedsPublish(first, published));
    assert(ShadowFrameNeedsPublish({101, 21, 2}, published));
    // Recovered writer, restarted producer, and a reused frame ID all republish.
    assert(ShadowFrameNeedsPublish(first, {}));
    assert(ShadowFrameNeedsPublish({102, 22, 1}, published));
    assert(ShadowFrameNeedsPublish({101, 22, 1}, published));
    assert(!ShadowFrameNeedsPublish({0, 22, 1}, published));
    assert(!ShadowFrameNeedsPublish({101, 0, 1}, published));
    assert(!ShadowFrameNeedsPublish({101, 22, 0}, published));

    ClientState old{};
    InitializeWireState(old);
    old.clientPid = 101;
    old.presentationMode = 1;
    old.gameState = 4;
    old.stereoState = 1;
    old.lastPresentedFrameId = 10;
    old.lastRenderedPoseId = 5;
    old.interopProbeToken = 6;
    old.interopProbeHandle = 0x123456789ABCDEF0ull;
    old.backbufferWidth = 1280;
    old.backbufferHeight = 720;
    assert(ShadowClientEqual(old, old));

    auto check = [&](auto modify) {
        ClientState next = old;
        modify(next);
        assert(!ShadowClientEqual(next, old));
        assert(!ShadowClientEqual(old, next));
    };
    check([](ClientState& x) { ++x.clientPid; });
    check([](ClientState& x) { ++x.flags; });
    check([](ClientState& x) { ++x.presentationMode; });
    check([](ClientState& x) { ++x.gameState; });
    check([](ClientState& x) { ++x.stereoState; });
    check([](ClientState& x) { ++x.lastFailure; });
    check([](ClientState& x) { ++x.adapterLuidLow; });
    check([](ClientState& x) { ++x.adapterLuidHigh; });
    check([](ClientState& x) { ++x.interopProbeGeneration; });
    check([](ClientState& x) { ++x.interopProbeToken; });
    check([](ClientState& x) { ++x.interopProbeHandle; });
    check([](ClientState& x) { ++x.backbufferWidth; });
    check([](ClientState& x) { ++x.backbufferHeight; });
    check([](ClientState& x) { ++x.lastPresentedFrameId; });
    check([](ClientState& x) { ++x.lastRenderedPoseId; });
    return 0;
}
