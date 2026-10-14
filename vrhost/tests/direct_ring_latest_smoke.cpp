#include "runtime/direct_ring_latest.hpp"
#include "runtime/direct_run_epoch.hpp"
#include <array>
#include <cstdint>
using namespace OutRunVrDirectRingLatest;
// Release/NDEBUG must also execute the negative regressions.
#define EXPECT(x) do { if (!(x)) return __LINE__; } while (false)
struct Frame { std::uint32_t frameId, generation, slot; bool basic, ready; };
static bool Before(std::uint32_t a, std::uint32_t b) noexcept {
    return a != b && static_cast<std::int32_t>(a-b) < 0;
}
template<std::size_t N>
Selection Select(const std::array<Frame,N>& frames, std::uint32_t last=0) {
    return Pick(frames.data(),frames.size(),
        [](const Frame& f){return f.basic && f.frameId && f.generation;},
        [last](const Frame& f){return f.ready && f.slot < 4 &&
            (!last || Before(last,f.frameId));},
        [](const Frame& f){return f.generation;},Before);
}
int main() {
    EXPECT(Select(std::array<Frame,0>{}).index == NoIndex);
    const std::array<Frame,4> unordered{{
        {31,7,1,true,true},{28,7,2,true,true},
        {30,7,3,true,true},{29,7,0,true,true}}};
    EXPECT(Select(unordered).index == 0);
    EXPECT(Select(unordered,29).index == 0);
    EXPECT(Select(unordered,31).index == NoIndex);
    const std::array<Frame,4> switched{{
        {101,9,1,true,true},{105,10,9,true,true},
        {102,10,2,true,true},{104,9,0,true,true}}};
    const auto sw=Select(switched);
    EXPECT(sw.haveGeneration && sw.generation==10 && sw.index==2);
    EXPECT(Select(switched,103).index == NoIndex);
    // Newest generation is first discovered at the end of the ring,
    // but its only eligible member was already encountered earlier.
    // The former naïve single-pass variant incorrectly returned NoIndex.
    const std::array<Frame,4> lateGeneration{{
        {14,4,4,true,false},{11,1,3,true,true},
        {6,2,2,true,true},{17,2,5,true,true}}};
    const auto lg = Select(lateGeneration,5);
    EXPECT(lg.haveGeneration && lg.generation == 2 && lg.index == 2);
    const std::array<Frame,4> newestUnready{{
        {100,5,0,true,true},{103,5,1,true,false},
        {102,5,2,true,true},{101,5,3,true,true}}};
    EXPECT(Select(newestUnready).index == 2);
    const std::array<Frame,4> invalidNewer{{
        {10,3,0,true,true},{15,4,8,true,true},
        {11,3,1,true,true},{14,4,2,true,true}}};
    EXPECT(Select(invalidNewer).index == 3);
    const std::array<Frame,4> nonDirect{{
        {10,3,0,true,true},{15,4,1,false,true},
        {12,3,2,true,true},{11,3,3,true,true}}};
    EXPECT(Select(nonDirect).index == 2);
    const std::array<Frame,4> wrap{{
        {0xfffffffeU,7,0,true,true},{1,7,1,true,true},
        {0xffffffffU,7,2,true,true},{0,7,3,true,true}}};
    EXPECT(Select(wrap).index == 1);
    EXPECT(Select(wrap,0xffffffffU).index == 1);
    // Real host/game restart: Frame.v2 reader has switched to a new
    // runGeneration/PID, but last displayed frame belonged to the old run.
    // Reusing frameId 1..2 must not be suppressed behind old frame 9000.
    OutRunVrDirectRunEpoch::Cursor epoch{};
    std::uint32_t displayed = 9000;
    EXPECT(!epoch.Observe({77, 4200}));
    EXPECT(!epoch.Observe({77, 4200}));
    EXPECT(!epoch.Observe({0, 0})); // malformed publication is ignored
    const std::array<Frame, 2> restarted{{
        {1,1,0,true,true},{2,1,1,true,true}}};
    EXPECT(Select(restarted, displayed).index == NoIndex);
    if (epoch.Observe({78, 4300})) displayed = 0;
    EXPECT(displayed == 0);
    EXPECT(Select(restarted, displayed).index == 1);
    displayed = 2;
    EXPECT(Select(restarted, displayed).index == NoIndex);
    EXPECT(!epoch.Observe({78, 4300})); // same-run duplicate suppressed
    EXPECT(displayed == 2);
    if (epoch.Observe({78, 4400})) displayed = 0; // PID reuse/restart
    EXPECT(displayed == 0 && epoch.active.gamePid == 4400);
    return 0;
}
