#include <cassert>
#include "../src/vr/game/external_car_runtime_policy.hpp"
using namespace OutRunVR::DinoSidecar;
int main() {
    for(int f50=0;f50<2;++f50)
        for(int requested=0;requested<2;++requested)
            assert(UseExternalSuspensionSmoothing(f50,requested)==
                   static_cast<bool>(f50&&requested));
    // Exhaust all sixteen allow/deny combinations. PBR is not silently
    // blocked when the fixed-function A/B probe is intentionally OFF.
    for(int selected=0;selected<2;++selected)
        for(int fixed=0;fixed<2;++fixed)
            for(int pbr=0;pbr<2;++pbr)
                for(int replacement=0;replacement<2;++replacement)
                    assert(PermitGenericSidecar(selected,fixed,pbr,replacement)==
                           static_cast<bool>(selected&&(fixed||pbr)&&replacement));
    // Positive: real PBR diagnostic route, without fixed-function override.
    assert(PermitGenericSidecar(true,false,true,true));
    // Negative: model-OFF, no experiment flags, and no callback ownership.
    assert(!PermitGenericSidecar(false,false,true,true));
    assert(!PermitGenericSidecar(true,false,false,true));
    assert(!PermitGenericSidecar(true,false,true,false));
    return 0;
}
