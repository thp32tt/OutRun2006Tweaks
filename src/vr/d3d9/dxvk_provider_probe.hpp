#pragma once

struct IDirect3DDevice9;

namespace OutRunVR::Dxvk
{
    struct ProviderSnapshot
    {
        bool d3d9ProviderLoaded{};
        bool nonSystemProvider{};
        bool stockDxvkInterop{};
        bool d3d9ExAvailable{};
        long stockDxvkInteropHr{};
        long d3d9ExHr{};
    };

    // Passive only: no hook installation, no device mutation, no rendering
    // changes. R71 uses this to census the actual provider before enabling any
    // DXVK-specific path.
    [[nodiscard]] ProviderSnapshot ProbeProvider(
        IDirect3DDevice9* device) noexcept;

    [[nodiscard]] bool PreflightNonSystemProvider() noexcept;
}
