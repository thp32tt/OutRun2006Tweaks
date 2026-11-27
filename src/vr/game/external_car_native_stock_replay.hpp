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
// Canonical retail OR2006C2C.exe (SHA256 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3).
// 469600 selects one of 30 records through 5B2F68. The three queue
// groups use the explicit object fields below, not a prefix-only heuristic.
struct NativeModelProfile { std::uint32_t prefix, parts[3]; };
inline constexpr NativeModelProfile NativeModelProfiles[30]={
    {0x10000u, {0x60000u, 0x38e001u, 0x3c01ffeu}}, // 0
    {0x20000u, {0x60u, 0x38fu, 0x3c00u}}, // 1
    {0x30000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 2
    {0xa0000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 3
    {0x50000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 4
    {0x40000u, {0x60000u, 0x218e001u, 0x1e01ffeu}}, // 5
    {0x70000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 6
    {0x80000u, {0x60000u, 0x18e001u, 0x1e01ffeu}}, // 7
    {0x90000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 8
    {0xb0000u, {0x60u, 0x38fu, 0x3c00u}}, // 9
    {0x60000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 10
    {0x14a0000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 11
    {0x14b0000u, {0x60000u, 0x18e001u, 0x1e01ffeu}}, // 12
    {0x14c0000u, {0x60000u, 0x38e001u, 0x3c01ffeu}}, // 13
    {0x14d0000u, {0x60000u, 0x28e001u, 0x3c01ffeu}}, // 14
    {0x14e0000u, {0x60000u, 0x38e001u, 0x3c01ffeu}}, // 15
    {0x14f0000u, {0x60u, 0x38fu, 0x3c00u}}, // 16
    {0x1500000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 17
    {0x1570000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 18
    {0x1520000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 19
    {0x1510000u, {0x60000u, 0x18e001u, 0x1e01ffeu}}, // 20
    {0x1540000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 21
    {0x1550000u, {0x60000u, 0x18e001u, 0x1e01ffeu}}, // 22
    {0x1560000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 23
    {0x1580000u, {0x60u, 0x38fu, 0x3c00u}}, // 24
    {0x1530000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 25
    {0x1590000u, {0x60000u, 0x78e001u, 0x7801ffeu}}, // 26
    {0x15a0000u, {0x60000u, 0x18e001u, 0x1e01ffeu}}, // 27
    {0x15b0000u, {0x60000u, 0x38e001u, 0x3c01ffeu}}, // 28
    {0x15c0000u, {0x60000u, 0x28e001u, 0x3c01ffeu}}, // 29
};
constexpr const NativeModelProfile* NativeModelProfileFor(int model) noexcept {
    return model>=0&&model<30?&NativeModelProfiles[model]:nullptr;
}
inline constexpr unsigned NativeModelFields[3][16]={
    {0xa,0xe},
    {0,6,0x12,0x18,0x19,0x1f,0x20,0x21},
    {0x22,0x23,0x24,0x25,0x2a,0x2b,0x2c,0x2d,0x32,0x33,0x34,0x35,0x3a,0x3b,0x3c,0x3d}
};
inline constexpr unsigned NativeModelFieldCounts[3]={2,8,16};
inline bool NativeModelLayoutMatches(int model,const std::uint32_t* layout,unsigned count) noexcept {
    const auto* profile=NativeModelProfileFor(model);
    if(!profile||!layout||count<0x3eu)return false;
    for(unsigned group=0;group<3;++group){
        std::uint32_t observed=0;
        for(unsigned i=0;i<NativeModelFieldCounts[group];++i){
            const auto id=layout[NativeModelFields[group][i]];
            if(id==0xffffffffu)continue;
            const auto part=id&0xffffu;
            if((id&0xffff0000u)!=profile->prefix||part>=32u)return false;
            const auto bit=std::uint32_t{1}<<part;
            if(observed&bit)return false;
            observed|=bit;
        }
        if(observed!=profile->parts[group])return false;
    }
    return true;
}
struct NativeVehicleStockReplay {
    IsolatedVehicleKey key{};
    unsigned opened=0,closed=0,physicalDepth=0,physicalEntries=0;
    unsigned omitted[2]{},entryOmitted[2]{};
    int model=-1;
    bool group=false,failed=false;
    bool OwnsObject(std::uint32_t object) const noexcept {
        const auto* profile=NativeModelProfileFor(model);
        const auto part=object&0xffffu;
        return profile&&group&&opened>=1&&opened<=3&&part<32u&&
            (object&0xffff0000u)==profile->prefix&&
            (profile->parts[opened-1]&(std::uint32_t{1}<<part))!=0;
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
