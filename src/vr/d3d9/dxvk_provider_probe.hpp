#pragma once

#include <cstdint>

struct IDirect3DDevice9;

namespace OutRunVR::Dxvk
{
    struct ProviderSnapshot
    {
        bool d3d9ProviderLoaded{};
        bool nonSystemProvider{};
        bool gameLocalProvider{};
        bool stockDxvkInterop{};
        bool d3d9ExAvailable{};
        bool stockDxvkVulkanHandles{};
        bool stockDxvkSubmissionQueue{};
        bool externalMemoryWin32{};
        bool externalSemaphoreWin32{};
        bool nativeTransportCandidate{};
        std::uint32_t stockQueueIndex{0xffffffffu};
        std::uint32_t stockQueueFamilyIndex{0xffffffffu};
        long stockDxvkInteropHr{};
        long d3d9ExHr{};
    };

    // Passive only: no hook installation, no device mutation, no rendering
    // changes. R71 uses this to census the actual provider before enabling any
    // DXVK-specific path.
    [[nodiscard]] ProviderSnapshot ProbeProvider(
        IDirect3DDevice9* device) noexcept;

    // Emit one provider/capability attestation. Device-creation call sites use
    // this on every successful CreateDevice/CreateDeviceEx so a later full
    // device recreation cannot silently inherit the startup-only census.
    void LogProviderCensus(
        IDirect3DDevice9* device,
        const char* source) noexcept;

    [[nodiscard]] bool PreflightNonSystemProvider() noexcept;
}
