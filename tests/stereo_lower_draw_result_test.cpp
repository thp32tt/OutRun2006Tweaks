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
    static_assert(Attempt::AfterDraw(NotImpl,true,Fail).handled);
    static_assert(Attempt::AfterDraw(Ok,false,Fail).hr==Fail);
}
