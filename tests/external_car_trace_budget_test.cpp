#include "../src/vr/game/external_car_trace_budget.hpp"
#include <cassert>
using namespace OutRunVR::DinoSidecar;
int main() {
    ExternalCarTraceBudget car{};
    // Long asynchronous CPU + staged DDS/VB upload consumes early samples.
    for(unsigned n=1;n<=1024;++n) {
        const bool show=car.ShouldLog(OriginalCarRoute::OriginalFallback,
                                      false,false);
        assert(show==(n<=8u));
    }
    assert(car.attempts==1024u);
    // In diagnostic-only mode the first actual completed GPU eye pairs
    // remain visible, rather than disappearing after four/warmup frames.
    for(unsigned n=0;n<4u;++n)
        assert(car.ShouldLog(OriginalCarRoute::ExternalComplete,false,false));
    assert(!car.ShouldLog(OriginalCarRoute::ExternalComplete,false,false));
    for(unsigned n=0;n<4u;++n)
        assert(car.ShouldLog(OriginalCarRoute::ExternalPartial,false,false));
    assert(!car.ShouldLog(OriginalCarRoute::ExternalPartial,false,false));
    // The next terminal upload failure must survive the per-car warmup cap.
    for(unsigned n=0;n<4u;++n)
        assert(car.ShouldLog(OriginalCarRoute::OriginalFallback,true,false));
    assert(!car.ShouldLog(OriginalCarRoute::OriginalFallback,true,false));
    // Separate Ferrari remains independently eligible for its milestones.
    ExternalCarTraceBudget other{};
    assert(other.ShouldLog(OriginalCarRoute::ExternalComplete,false,false));
    assert(other.attempts==1u && car.attempts>1024u);
    ExternalCarTraceBudget verbose{};
    for(unsigned n=1;n<=32u;++n) {
        const bool should=verbose.ShouldLog(
            OriginalCarRoute::OriginalFallback,false,true);
        assert(should==(n<=8u || (n&(n-1u))==0u));
    }
}
