#pragma once

#include <atomic>
#include <d3d9.h>

#include "state_block_tracker.hpp"

namespace OutRunVR::State
{
    // Neutral execution boundary for the lazy StateBlock resync requested by
    // StateBlockTracker. R31 still supplies the proven resync primitives while
    // upper draw overlays consume only this neutral API.
    class StateBlockRecovery final
    {
    public:
        using ResynchronizeShaderEpochFn = void (*)(IDirect3DDevice9*) noexcept;
        using PrimeShadowStateFn = bool (*)(IDirect3DDevice9*) noexcept;

        static void Configure(ResynchronizeShaderEpochFn resynchronizeShaderEpoch,
            PrimeShadowStateFn primeShadowState) noexcept
        {
            ResynchronizeShaderEpoch().store(
                resynchronizeShaderEpoch, std::memory_order_release);
            PrimeShadowState().store(
                primeShadowState, std::memory_order_release);
        }

        static void FlushPendingResync(IDirect3DDevice9* device) noexcept
        {
            if (!device || !StateBlockTracker::ConsumeResync())
                return;

            const auto resynchronizeShaderEpoch =
                ResynchronizeShaderEpoch().load(std::memory_order_acquire);
            const auto primeShadowState =
                PrimeShadowState().load(std::memory_order_acquire);
            if (!resynchronizeShaderEpoch || !primeShadowState)
            {
                StateBlockTracker::SetR31Reliable(false);
                StateBlockTracker::MarkCoverageLost();
                return;
            }

            resynchronizeShaderEpoch(device);
            if (!primeShadowState(device))
            {
                StateBlockTracker::SetR31Reliable(false);
                StateBlockTracker::MarkCoverageLost();
            }
        }

    private:
        static std::atomic<ResynchronizeShaderEpochFn>&
        ResynchronizeShaderEpoch() noexcept
        {
            static std::atomic<ResynchronizeShaderEpochFn> value{nullptr};
            return value;
        }

        static std::atomic<PrimeShadowStateFn>& PrimeShadowState() noexcept
        {
            static std::atomic<PrimeShadowStateFn> value{nullptr};
            return value;
        }
    };
}
