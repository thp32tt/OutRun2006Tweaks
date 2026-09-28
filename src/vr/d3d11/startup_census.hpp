#pragma once

#include <cstdint>
#include <d3d9.h>
#include <dxgiformat.h>

namespace outrun::vr::dx11
{
    struct StartupCensus
    {
        bool observed{};
        std::uint32_t width{};
        std::uint32_t height{};
        D3DFORMAT source_format = D3DFMT_UNKNOWN;
        DXGI_FORMAT native_format = DXGI_FORMAT_UNKNOWN;
        D3DMULTISAMPLE_TYPE multisample = D3DMULTISAMPLE_NONE;
        DWORD behavior_flags{};
        bool format_supported{};
        bool single_sample{};
        bool native_bootstrap_compatible{};
    };

    // Passive source-device census. This never creates a D3D11 device and never
    // mutates the live D3D9 state. It only tells later activation stages whether
    // the current OutRun backbuffer can be represented by the R71 bootstrap.
    [[nodiscard]] StartupCensus inspect_source_device(
        IDirect3DDevice9* device) noexcept;
}
