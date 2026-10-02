#pragma once

#include <d3d9.h>
#include <cstdint>

namespace OutRunVRStereo
{
    struct DirectTransportIdentitySnapshot
    {
        bool sharedStatePresent = false;
        bool interopVerified = false;
        std::uint32_t hostPid = 0;
        std::uint32_t hostAdapterLuidLow = 0;
        std::uint32_t hostAdapterLuidHigh = 0;
    };

    struct DirectTransportSlotView
    {
        IDirect3DSurface9* leftSurface = nullptr;
        IDirect3DSurface9* rightSurface = nullptr;
        IDirect3DQuery9* fence = nullptr;
        std::uint32_t frameId = 0;
    };

    DirectTransportIdentitySnapshot
    DirectTransportIdentitySnapshotForOverlay() noexcept;
    bool DirectTransportResourcesReadyRuntime() noexcept;
    bool EnsureDirectTransportResourcesRuntime(
        IDirect3DDevice9* device) noexcept;
    void InvalidateDirectTransportInteropResourcesRuntime() noexcept;

    bool ReadDirectTransportSlotView(
        std::uint32_t slotIndex,
        DirectTransportSlotView& out) noexcept;
    void CommitDirectTransportProducerSlot(
        std::uint32_t slotIndex,
        std::uint32_t frameId) noexcept;

    IDirect3DSurface9* DirectTransportBackBufferSnapshot() noexcept;
    std::uint32_t DirectTransportWidthSnapshot() noexcept;
    std::uint32_t DirectTransportHeightSnapshot() noexcept;
    D3DFORMAT DirectTransportFormatSnapshot() noexcept;

    bool DirectTransportFrameIdAtOrAfter(
        std::uint32_t current,
        std::uint32_t reference) noexcept;

    void NoteDirectTransportFenceTimeoutRuntime() noexcept;
    void NoteDirectTransportRingBackpressureRuntime() noexcept;
    std::uint64_t DirectTransportFenceTimeoutCount() noexcept;
    std::uint64_t DirectTransportRingBackpressureCount() noexcept;
}
