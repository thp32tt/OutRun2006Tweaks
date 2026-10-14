#include <cassert>
#include "../vrhost/src/runtime/native_stereo_source_route.hpp"

int main()
{
    using namespace OutRunVrNativeEyePair;
    static_assert(ChooseStereoSource(false,false,false,false,false) ==
                  StereoSourceRoute::None);
    static_assert(ChooseStereoSource(true,true,true,false,false) ==
                  StereoSourceRoute::DirectGpu);
    static_assert(ChooseStereoSource(false,true,true,true,true) ==
                  StereoSourceRoute::Sbs);
    static_assert(ChooseStereoSource(true,true,true,false,true) ==
                  StereoSourceRoute::DirectGpu);
    static_assert(ChooseStereoSource(true,false,true,false,false) ==
                  StereoSourceRoute::None);
    static_assert(ChooseStereoSource(false,false,false,true,false) ==
                  StereoSourceRoute::None);
    // Neither a stale cached SRV nor an asserted bit alone is valid frame data.
    assert(ChooseStereoSource(false,true,true,false,true) ==
           StereoSourceRoute::None);
    assert(ChooseStereoSource(true,true,false,false,false) ==
           StereoSourceRoute::None);
}
