#pragma once

#include <d3d9.h>

#include <cstdint>

#include "dxvk_interop.hpp"

namespace OutRunVRDxvkMultiview
{
    struct Telemetry
    {
        std::uint64_t armAttempts{};
        std::uint64_t armSuccess{};
        std::uint64_t armRejected{};
        std::uint64_t drawSuccess{};
        std::uint64_t drawFailure{};
        std::uint64_t cancels{};
        std::uint64_t interfaceMisses{};
        std::uint64_t protocolMismatches{};
        std::uint64_t capabilityMisses{};
    };

    bool TryArmWorldDraw(
        IDirect3DDevice9* device,
        IDirect3DSurface9* rightColorTarget,
        IDirect3DSurface9* rightDepthTarget,
        const float* leftWvp,
        const float* rightWvp,
        std::uint64_t poseSequence,
        std::uint64_t drawToken,
        std::uint32_t eligibilityFlags) noexcept;

    void FinishArmedDraw(bool drawSucceeded) noexcept;
    void InvalidateDevice() noexcept;
    Telemetry GetTelemetry() noexcept;
}
