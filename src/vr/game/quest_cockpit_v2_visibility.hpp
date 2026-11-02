// Quest original node_visible_10AA17C forces visible/LOD0 on
// cockpit_occupant_draw TLS AND a view-service flag +0x35.
// PC 405015 -> 40501D -> 405021 uses EAX+LOD[ESP+0x1C] instead.
// No assertion of native view+0x35 semantic equivalence: experimental.
#pragma once
#include <cstdint>
namespace OutRunVR::QuestCockpitV2 {
inline thread_local std::uint32_t ActiveOriginalOccupantLod0=0;
class ScopedOriginalOccupantLod0 final {
    bool active_=false;
public:
    explicit ScopedOriginalOccupantLod0(bool admit) noexcept
        :active_(admit && ActiveOriginalOccupantLod0==0) {
        if(active_)++ActiveOriginalOccupantLod0;
    }
    ~ScopedOriginalOccupantLod0() noexcept {
        if(active_)--ActiveOriginalOccupantLod0;
    }
    ScopedOriginalOccupantLod0(const ScopedOriginalOccupantLod0&)=delete;
    ScopedOriginalOccupantLod0& operator=(const ScopedOriginalOccupantLod0&)=delete;
    bool Active() const noexcept {return active_;}
};
inline bool OriginalOccupantLod0Active() noexcept {
    return ActiveOriginalOccupantLod0==1u;
}
}
