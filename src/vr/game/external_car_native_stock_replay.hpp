#pragma once
#include <atomic>
#include <cstdint>
#include "external_car_isolated_transaction.hpp"

namespace OutRunVR::DinoSidecar {
// Verified retail 46BF8C -> 469600; only the three model queues are
// eligible. The original function, its state updates, shadows, lighting,
// and all original physical draws remain running exactly once.
struct NativeVehicleStockReplay {
    IsolatedVehicleKey key{};
    unsigned opened=0,closed=0,physicalDepth=0,physicalEntries=0;
    unsigned omitted[2]{};
    bool group=false,failed=false;
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
    }
    void LeavePhysical() noexcept {
        if(!physicalDepth){failed=true;return;}
        --physicalDepth;
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
    explicit ScopedNativeVehiclePhysical(bool owned) noexcept:replay(ActiveNativeVehicleStockReplay) {
        if(replay)replay->EnterPhysical(owned);
    }
    ~ScopedNativeVehiclePhysical(){if(replay)replay->LeavePhysical();}
    ScopedNativeVehiclePhysical(const ScopedNativeVehiclePhysical&)=delete;
    ScopedNativeVehiclePhysical& operator=(const ScopedNativeVehiclePhysical&)=delete;
};
} // namespace OutRunVR::DinoSidecar
