#pragma once
#include <atomic>
#include <cstdint>
#include "external_car_isolated_transaction.hpp"

namespace OutRunVR::DinoSidecar {
// Verified retail 46BF8C -> 469600; only the three model queues are
// eligible. The original function, its state updates, shadows, lighting,
// and all original physical draws remain running exactly once.
// 405220..405249 initializes the 256-entry queue; 405047..405076
// appends exactly one 0x3c-byte record and its sorted-list pointer.
// Use the populated record count, not the allocation capacity.
constexpr bool NativeQueueEntryInPool(std::uint32_t count,std::uint32_t capacity,
    std::uintptr_t pool,std::uintptr_t entry) noexcept {
    return count&&count<=capacity&&capacity<=0x100u&&pool&&entry>=pool&&
        (entry-pool)%0x3cu==0&&(entry-pool)/0x3cu<count;
}
struct NativeVehicleStockReplay {
    IsolatedVehicleKey key{};
    unsigned opened=0,closed=0,physicalDepth=0,physicalEntries=0;
    unsigned omitted[2]{},entryOmitted[2]{};
    int model=-1;
    bool group=false,failed=false;
    // Exact F50 object IDs from canonical layouts 5B0F08 and 5B2060.
    bool OwnsObject(std::uint32_t object) const noexcept {
        const std::uint32_t prefix=model==2?0x30000u:model==17?0x1500000u:0u;
        if(!prefix||!group||(object&0xffff0000u)!=prefix)return false;
        const auto part=object&0xffffu;
        if(opened==1)return part==0x11u||part==0x12u;
        if(opened==2)return part==0u||(part>=0x0du&&part<=0x0fu)||
            (part>=0x13u&&part<=0x16u);
        if(opened==3)return (part>=1u&&part<=0x0cu)||(part>=0x17u&&part<=0x1au);
        return false;
    }
    void Open(bool empty) noexcept {
        if(group||physicalDepth||opened!=closed||opened>=3||!empty)failed=true;
        group=true;++opened;
    }
    void Close(bool empty) noexcept {
        if(!group||physicalDepth||opened!=closed+1||!empty)failed=true;
        group=false;++closed;
    }
    void EnterPhysical(bool owned) noexcept {
        if(!group||physicalDepth||!owned)failed=true;
        ++physicalDepth;++physicalEntries;
        if(physicalDepth==1){entryOmitted[0]=omitted[0];entryOmitted[1]=omitted[1];}
    }
    void LeavePhysical() noexcept {
        if(!physicalDepth){failed=true;return;}
        --physicalDepth;
        if(!physicalDepth){
            // A missing physical replay is not proof of a culled entry.
            const auto l=omitted[0]-entryOmitted[0],r=omitted[1]-entryOmitted[1];
            if(!l||l!=r)failed=true;
        }
    }
    bool StockOnly() const noexcept {return group&&physicalDepth==1&&!failed;}
    bool Ready() const noexcept {
        return !failed&&!group&&!physicalDepth&&opened==3&&closed==3&&
            physicalEntries&&omitted[0]&&omitted[0]==omitted[1]&&key.Same(key);
    }
};
inline thread_local NativeVehicleStockReplay* ActiveNativeVehicleStockReplay=nullptr;
inline std::atomic<bool> NativeVehicleModelEdgesReady{false},NativeVehiclePmtConsumerReady{false};
struct ScopedNativeVehicleStockReplay {
    NativeVehicleStockReplay* previous;
    explicit ScopedNativeVehicleStockReplay(NativeVehicleStockReplay& r) noexcept:
        previous(ActiveNativeVehicleStockReplay) {
        if(previous){previous->failed=true;r.failed=true;}
        ActiveNativeVehicleStockReplay=&r;
    }
    ~ScopedNativeVehicleStockReplay(){ActiveNativeVehicleStockReplay=previous;}
    ScopedNativeVehicleStockReplay(const ScopedNativeVehicleStockReplay&)=delete;
    ScopedNativeVehicleStockReplay& operator=(const ScopedNativeVehicleStockReplay&)=delete;
};
struct ScopedNativeVehiclePhysical {
    NativeVehicleStockReplay* replay;
    explicit ScopedNativeVehiclePhysical(bool owned) noexcept:
        replay(ActiveNativeVehicleStockReplay&&ActiveNativeVehicleStockReplay->group?
            ActiveNativeVehicleStockReplay:nullptr) {
        // Native shadows and other legitimate draws between model groups
        // must be replayed in both scenes, not interpreted as failed body
        // ownership. Only a physical entry INSIDE a model group can omit.
        if(replay)replay->EnterPhysical(owned);
    }
    ~ScopedNativeVehiclePhysical(){if(replay)replay->LeavePhysical();}
    ScopedNativeVehiclePhysical(const ScopedNativeVehiclePhysical&)=delete;
    ScopedNativeVehiclePhysical& operator=(const ScopedNativeVehiclePhysical&)=delete;
};
} // namespace OutRunVR::DinoSidecar
