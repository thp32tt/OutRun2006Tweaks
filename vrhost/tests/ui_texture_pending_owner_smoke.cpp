#include "vr/game/ui_texture_pending_owner.hpp"
#include <atomic>
#include <thread>
using OutRunVR::UiTexture::CurrentLookup;
using OutRunVR::UiTexture::PendingLookup;
#define CHECK(x) do { if (!(x)) return __LINE__; } while (false)
int main()
{
    int parent=0, mask=0, foreign=0;
    CurrentLookup.Clear();
    CHECK(CurrentLookup.texture == nullptr && CurrentLookup.maskTexture == nullptr);
    CurrentLookup.Advance(&mask, 0x23, true);
    CHECK(CurrentLookup.texture == &mask && CurrentLookup.textureId == 0x23);
    CurrentLookup.Advance(&parent, 0x24, true);
    CHECK(CurrentLookup.maskTexture == &mask && CurrentLookup.maskTextureId == 0x23);
    CHECK(CurrentLookup.texture == &parent && CurrentLookup.textureId == 0x24);
    // A native miss drops CURRENT but can leave the earlier source as a
    // legitimate mask candidate (identical to the pre-change UI behavior).
    CurrentLookup.Advance(nullptr, 0x25, true);
    CHECK(CurrentLookup.texture == nullptr && CurrentLookup.textureId == 0);
    CHECK(CurrentLookup.maskTexture == &parent && CurrentLookup.maskTextureId == 0x24);
    CurrentLookup.Clear();
    CHECK(!CurrentLookup.texture && !CurrentLookup.maskTexture &&
          CurrentLookup.textureId == 0 && CurrentLookup.maskTextureId == 0);

    // A concurrent texture loader must not replace a UI sprite's previous
    // mask/parent pointer association. No lock/sleep/data race is required.
    std::atomic<bool> workerReady{false}, releaseWorker{false}, workerOk{false};
    CurrentLookup.Advance(&mask, 0x77, true);
    std::thread t([&]() {
        // A new producer thread starts with NO inherited parent or mask.
        const bool isolated = CurrentLookup.texture == nullptr &&
            CurrentLookup.maskTexture == nullptr;
        CurrentLookup.Advance(&foreign, 0xAA, true);
        workerReady.store(true, std::memory_order_release);
        while (!releaseWorker.load(std::memory_order_acquire))
            std::this_thread::yield();
        workerOk.store(isolated &&
            CurrentLookup.texture == &foreign &&
            CurrentLookup.textureId == 0xAA &&
            CurrentLookup.maskTexture == nullptr,
            std::memory_order_release);
    });
    while (!workerReady.load(std::memory_order_acquire))
        std::this_thread::yield();
    const bool mainOk = CurrentLookup.texture == &mask &&
        CurrentLookup.textureId == 0x77 &&
        CurrentLookup.maskTexture == nullptr;
    releaseWorker.store(true, std::memory_order_release);
    t.join();
    CHECK(mainOk && workerOk.load(std::memory_order_acquire));
    CurrentLookup.Clear();
    return 0;
}