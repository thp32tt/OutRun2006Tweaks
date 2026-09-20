#pragma once

#include <cstdint>

namespace OutRunVR
{
    enum class RenderBackend : std::uint8_t
    {
        Auto = 0,
        D3D9TwoPass = 1,
        Dxvk = 2,
        Dx12 = 3,
    };

    constexpr RenderBackend RenderBackendFromSetting(int value) noexcept
    {
        switch (value)
        {
        case 1: return RenderBackend::D3D9TwoPass;
        case 2: return RenderBackend::Dxvk;
        case 3: return RenderBackend::Dx12;
        default: return RenderBackend::Auto;
        }
    }

    constexpr const char* RenderBackendName(RenderBackend backend) noexcept
    {
        switch (backend)
        {
        case RenderBackend::D3D9TwoPass: return "D3D9TwoPass";
        case RenderBackend::Dxvk: return "DXVK";
        case RenderBackend::Dx12: return "DX12";
        default: return "Auto";
        }
    }

    constexpr bool BackendRequestsDxvk(RenderBackend backend) noexcept
    {
        return backend == RenderBackend::Dxvk;
    }

    constexpr bool BackendRequestsDx12(RenderBackend backend) noexcept
    {
        return backend == RenderBackend::Dx12;
    }
}
