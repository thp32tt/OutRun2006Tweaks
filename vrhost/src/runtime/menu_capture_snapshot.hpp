#pragma once
#include <algorithm>
#include <cstdint>

// Keep a game-window/client snapshot coherent across VR capture, aspect and
// partial-window placement when Desktop Duplication or the VD profile resizes.
namespace OutRunVrMenuCapture {
struct Snapshot {
    bool visible = false, fullyVisible = false;
    float x = 0, y = 0, width = 0, height = 0;
};
constexpr Snapshot ClipClient(
    std::int64_t l, std::int64_t t, std::int64_t r, std::int64_t b,
    std::uint32_t outputW, std::uint32_t outputH) noexcept {
    if (!outputW || !outputH || r <= l || b <= t) return {};
    const auto cl = (std::max)(std::int64_t{0}, l);
    const auto ct = (std::max)(std::int64_t{0}, t);
    const auto cr = (std::min)(static_cast<std::int64_t>(outputW), r);
    const auto cb = (std::min)(static_cast<std::int64_t>(outputH), b);
    if (cr <= cl || cb <= ct) return {};
    Snapshot s{};
    s.x = static_cast<float>(cl) / outputW;
    s.y = static_cast<float>(ct) / outputH;
    s.width = static_cast<float>(cr - cl) / outputW;
    s.height = static_cast<float>(cb - ct) / outputH;
    s.visible = s.width > .01f && s.height > .01f;
    s.fullyVisible = s.visible && l >= 0 && t >= 0 &&
        r <= static_cast<std::int64_t>(outputW) &&
        b <= static_cast<std::int64_t>(outputH);
    return s;
}
constexpr auto Full = ClipClient(160,90,1440,810,1920,1080);
constexpr auto Partial = ClipClient(-240,90,1040,810,1920,1080);
static_assert(Full.visible && Full.fullyVisible && Full.width > .66f);
static_assert(Partial.visible && !Partial.fullyVisible &&
    Partial.x == 0.f && Partial.width > .54f);
static_assert(!ClipClient(2000,0,2300,900,1920,1080).visible);
static_assert(!ClipClient(0,0,1,900,1920,1080).visible);
}
