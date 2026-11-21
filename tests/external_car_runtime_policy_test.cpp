#include <cassert>
#include "../src/vr/game/external_car_runtime_policy.hpp"
using namespace OutRunVR::DinoSidecar;
int main() {
    for(int f50=0;f50<2;++f50)
        for(int requested=0;requested<2;++requested)
            assert(UseExternalSuspensionSmoothing(f50,requested)==
                   static_cast<bool>(f50&&requested));
    for(int selected=0;selected<2;++selected)
        for(int fixed=0;fixed<2;++fixed)
            for(int replacement=0;replacement<2;++replacement)
                assert(PermitGenericSidecar(selected,fixed,replacement)==
                       static_cast<bool>(selected&&fixed&&replacement));
    return 0;
}
