#include <cassert>
#include <cstdint>
#include <initializer_list>
#include "../src/vr/game/stereo_lower_draw_result.hpp"

using Result=std::int32_t;
using Attempt=OutRunVR::StereoLowerDraw::Attempt<Result>;
constexpr Result Ok=0, NotImpl=-2147467263, Fail=-2147467259;
struct MockDispatch {
    unsigned physicalLeft=0,lowerCalls=0;
    Result Run(bool eligible,bool rollbackClean,bool attemptLeft,
               Result gpuHr,bool restored) noexcept {
        Attempt outcome=Attempt::Declined();
        if(eligible) {
            if(!rollbackClean)outcome=Attempt::Handled(Fail);
            else if(attemptLeft) {
                ++physicalLeft;
                outcome=Attempt::AfterDraw(gpuHr,restored,Fail);
            }
        }
        if(outcome.handled)return outcome.hr;
        ++lowerCalls;
        return Ok;
    }
};
int main() {
    // Legitimate pre-draw declines (including a clean WVP rollback) still
    // invoke R29 exactly once.
    for(bool eligible: {false,true}) {
        MockDispatch d{};
        assert(d.Run(eligible,true,false,NotImpl,true)==Ok);
        assert(d.physicalLeft==0 && d.lowerCalls==1);
    }
    // Dirty pre-draw state must never escape to another renderer.
    MockDispatch dirty{};
    assert(dirty.Run(true,false,false,Ok,false)==Fail);
    assert(dirty.physicalLeft==0 && dirty.lowerCalls==0);
    // Real E_NOTIMPL after a physical LEFT attempt is not a route decline.
    // Neither that error nor a right-eye restoration failure can replay LEFT.
    for(Result hr: {Ok,NotImpl,Fail,Result(1)}) {
        for(bool restored: {false,true}) {
            MockDispatch d{};
            const auto result=d.Run(true,true,true,hr,restored);
            assert(result==(restored || hr<0 ? hr : Fail));
            assert(d.physicalLeft==1 && d.lowerCalls==0);
        }
    }
    // R30 -> support API -> R32 -> R33 indexed route uses the same typed
    // outcome; simulate a real raw indexed UP attempt and both VB/IB restores.
    for (bool stream : {false,true}) for (bool indices : {false,true}) {
        for (bool attempted : {false,true}) {
            for (Result hr : {NotImpl,Fail,Ok}) {
                const bool restored = stream && indices;
                const auto a = Attempt::AfterRoute(hr,attempted,restored,NotImpl,Fail);
                unsigned lowerCalls = 0;
                const auto finalHr = a.handled ? a.hr : (++lowerCalls,Ok);
                const bool decline = !attempted && restored && hr==NotImpl;
                assert(a.handled == !decline);
                assert(lowerCalls == (decline ? 1u : 0u));
                const auto expected = decline ? Ok :
                    (!restored && ((!attempted && hr==NotImpl) || hr>=0) ? Fail : hr);
                assert(finalHr == expected);
            }
        }
    }
    // FVF142 route entry means projection setup was attempted, even if
    // the setter fails before raw raster. Clean pre-admission declines
    // still allow native fallback exactly once.
    for (bool entered : {false,true}) for (bool restored : {false,true}) {
        const auto outcome = Attempt::AfterRoute(NotImpl,entered,restored,NotImpl,Fail);
        unsigned nativeFallback = 0;
        const Result hr = outcome.handled ? outcome.hr : (++nativeFallback,Ok);
        assert(nativeFallback == (!entered && restored ? 1u : 0u));
        assert(hr == (entered ? NotImpl : (restored ? Ok : Fail)));
    }
    assert(Attempt::AfterRoute(Ok,true,false,NotImpl,Fail).hr == Fail);
    assert(Attempt::AfterRoute(Fail,true,true,NotImpl,Fail).hr == Fail);
    static_assert(Attempt::AfterDraw(NotImpl,true,Fail).handled);
    static_assert(Attempt::AfterDraw(Ok,false,Fail).hr==Fail);
}
