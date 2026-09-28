#pragma once

#include <cstdint>
#include <d3d9.h>
#include <d3d11.h>

namespace outrun::vr::dx11
{
    enum class ResourceRole
    {
        Color,
        Texture,
        DepthStencil,
        Index,
        Vertex,
    };

    enum class ResourceMirrorLifetime : std::uint8_t
    {
        Unsupported = 0,
        DeviceGeneration,
        ManagedCpuShadow,
    };

    struct FormatTranslation
    {
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        bool exact = false;
    };

    struct ResourceBehaviorTranslation
    {
        D3D11_USAGE usage = D3D11_USAGE_DEFAULT;
        UINT bindFlags = 0;
        UINT cpuAccessFlags = 0;
        ResourceMirrorLifetime lifetime = ResourceMirrorLifetime::Unsupported;
        bool descriptorExact = false;
        bool requiresMutationTelemetry = false;
        bool requiresCpuShadow = false;
    };

    // Conservative translation contract used by the passive R72/R73 census.
    // "exact" means the source format can be represented without inventing
    // channel/depth semantics. Unknown/inexact formats remain on the D3D9 path.
    [[nodiscard]] FormatTranslation translate_resource_format(
        D3DFORMAT source,
        ResourceRole role) noexcept;

    // R73 descriptor/lifetime plan for resources observed on live draw calls.
    // This is evidence for a future mirror implementation, not an activation
    // signal. VB/IB/textures intentionally require mutation telemetry before
    // a sampled draw can be counted resource-exact. Managed resources also
    // require a CPU shadow that survives D3D9 Reset semantics.
    [[nodiscard]] ResourceBehaviorTranslation translate_resource_behavior(
        ResourceRole role,
        D3DPOOL pool,
        DWORD usage) noexcept;
}
