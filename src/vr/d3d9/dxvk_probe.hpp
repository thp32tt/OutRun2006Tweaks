#pragma once

#include <cstdint>

namespace OutRunVRDxvkProbe
{
    struct Snapshot
    {
        bool probeComplete{};
        bool dxvkDetected{};
        bool customInteropDetected{};
        bool customInteropCompatible{};
        bool nonSystemD3D9Provider{};
        bool d3d9ExExposed{};
        std::uint32_t customProtocolVersion{};
        long dxvkInteropHr{};
        long customInteropHr{};
    };

    bool IsProbeComplete() noexcept;
    bool IsDxvkDetected() noexcept;
    bool IsCustomInteropAvailable() noexcept;

    // Safe before device creation. Returns true when the already-loaded d3d9.dll
    // is not the Windows system provider, which is the expected stock-DXVK case.
    bool PreflightNonSystemD3D9Provider() noexcept;

    Snapshot GetSnapshot() noexcept;
}
