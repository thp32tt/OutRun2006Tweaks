#include "resource_translation.hpp"

#include <array>

namespace outrun::vr::dx11
{
    namespace
    {
        struct ResourceBehaviorRule
        {
            ResourceRole role;
            D3DPOOL pool;
            DWORD allowedUsage;
            DWORD requiredUsage;
            UINT bindFlags;
            ResourceMirrorLifetime lifetime;
            bool requiresMutationTelemetry;
            bool requiresCpuShadow;
        };

        constexpr std::array<ResourceBehaviorRule, 8> ResourceBehaviorRules{{
            { ResourceRole::Vertex, D3DPOOL_DEFAULT,
              D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY, 0,
              D3D11_BIND_VERTEX_BUFFER, ResourceMirrorLifetime::DeviceGeneration,
              true, false },
            { ResourceRole::Vertex, D3DPOOL_MANAGED,
              D3DUSAGE_WRITEONLY, 0,
              D3D11_BIND_VERTEX_BUFFER, ResourceMirrorLifetime::ManagedCpuShadow,
              true, true },
            { ResourceRole::Index, D3DPOOL_DEFAULT,
              D3DUSAGE_DYNAMIC | D3DUSAGE_WRITEONLY, 0,
              D3D11_BIND_INDEX_BUFFER, ResourceMirrorLifetime::DeviceGeneration,
              true, false },
            { ResourceRole::Index, D3DPOOL_MANAGED,
              D3DUSAGE_WRITEONLY, 0,
              D3D11_BIND_INDEX_BUFFER, ResourceMirrorLifetime::ManagedCpuShadow,
              true, true },
            { ResourceRole::Texture, D3DPOOL_DEFAULT,
              D3DUSAGE_DYNAMIC, 0,
              D3D11_BIND_SHADER_RESOURCE, ResourceMirrorLifetime::DeviceGeneration,
              true, false },
            { ResourceRole::Texture, D3DPOOL_MANAGED,
              0, 0,
              D3D11_BIND_SHADER_RESOURCE, ResourceMirrorLifetime::ManagedCpuShadow,
              true, true },
            { ResourceRole::Color, D3DPOOL_DEFAULT,
              D3DUSAGE_RENDERTARGET, D3DUSAGE_RENDERTARGET,
              D3D11_BIND_RENDER_TARGET, ResourceMirrorLifetime::DeviceGeneration,
              false, false },
            { ResourceRole::DepthStencil, D3DPOOL_DEFAULT,
              D3DUSAGE_DEPTHSTENCIL, D3DUSAGE_DEPTHSTENCIL,
              D3D11_BIND_DEPTH_STENCIL, ResourceMirrorLifetime::DeviceGeneration,
              false, false },
        }};
    }

    FormatTranslation translate_resource_format(
        D3DFORMAT source,
        ResourceRole role) noexcept
    {
        if (role == ResourceRole::Index)
        {
            switch (source)
            {
            case D3DFMT_INDEX16:
                return { DXGI_FORMAT_R16_UINT, true };
            case D3DFMT_INDEX32:
                return { DXGI_FORMAT_R32_UINT, true };
            default:
                return {};
            }
        }

        if (role == ResourceRole::DepthStencil)
        {
            switch (source)
            {
            case D3DFMT_D16:
                return { DXGI_FORMAT_D16_UNORM, true };
            case D3DFMT_D24S8:
                return { DXGI_FORMAT_D24_UNORM_S8_UINT, true };
            case D3DFMT_D32F_LOCKABLE:
                return { DXGI_FORMAT_D32_FLOAT, true };
            default:
                return {};
            }
        }

        // R179: resource-format exactness is role-specific. A vertex buffer
        // has no DXGI texture format, and block-compressed textures cannot
        // be created as D3D11 render targets. Never pass those as exact RTVs.
        if (role != ResourceRole::Color && role != ResourceRole::Texture)
            return {};
        if (role == ResourceRole::Color &&
            (source == D3DFMT_DXT1 ||
             source == D3DFMT_DXT3 ||
             source == D3DFMT_DXT5))
            return {};

        switch (source)
        {
        case D3DFMT_A8R8G8B8:
            return { DXGI_FORMAT_B8G8R8A8_UNORM, true };
        case D3DFMT_X8R8G8B8:
            return { DXGI_FORMAT_B8G8R8X8_UNORM, true };
        case D3DFMT_A8B8G8R8:
            return { DXGI_FORMAT_R8G8B8A8_UNORM, true };
        case D3DFMT_A2B10G10R10:
            // D3D9 A2B10G10R10 and DXGI R10G10B10A2_UNORM share the
            // same R-low/G/B/A-high packed channel layout. The opposite
            // D3D9 A2R10G10B10 ordering intentionally remains fail-closed.
            return { DXGI_FORMAT_R10G10B10A2_UNORM, true };
        case D3DFMT_R5G6B5:
            return { DXGI_FORMAT_B5G6R5_UNORM, true };
        case D3DFMT_A1R5G5B5:
            return { DXGI_FORMAT_B5G5R5A1_UNORM, true };
        case D3DFMT_A8:
            return { DXGI_FORMAT_A8_UNORM, true };
        case D3DFMT_DXT1:
            return { DXGI_FORMAT_BC1_UNORM, true };
        case D3DFMT_DXT3:
            return { DXGI_FORMAT_BC2_UNORM, true };
        case D3DFMT_DXT5:
            return { DXGI_FORMAT_BC3_UNORM, true };
        default:
            // Luminance/palettized/bump/floating formats deliberately remain
            // inexact until the matching shader/resource semantics are proven.
            return {};
        }
    }

    ResourceBehaviorTranslation translate_resource_behavior(
        ResourceRole role,
        D3DPOOL pool,
        DWORD usage) noexcept
    {
        for (const auto& rule : ResourceBehaviorRules)
        {
            if (rule.role != role || rule.pool != pool)
                continue;
            if ((usage & ~rule.allowedUsage) != 0)
                continue;
            if ((usage & rule.requiredUsage) != rule.requiredUsage)
                continue;

            ResourceBehaviorTranslation out{};
            out.bindFlags = rule.bindFlags;
            out.lifetime = rule.lifetime;
            out.descriptorExact = true;
            out.requiresMutationTelemetry = rule.requiresMutationTelemetry;
            out.requiresCpuShadow = rule.requiresCpuShadow;

            if ((usage & D3DUSAGE_DYNAMIC) != 0)
            {
                out.usage = D3D11_USAGE_DYNAMIC;
                out.cpuAccessFlags = D3D11_CPU_ACCESS_WRITE;
            }
            else
            {
                out.usage = D3D11_USAGE_DEFAULT;
            }
            return out;
        }

        // SYSTEMMEM/SCRATCH and unmodelled usage combinations deliberately
        // fail closed until a concrete staging/update/reset policy exists.
        return {};
    }

    BufferMutationTranslation translate_buffer_mutation(
        ResourceRole role,
        D3DPOOL pool,
        DWORD usage,
        DWORD lockFlags) noexcept
    {
        if (role != ResourceRole::Vertex && role != ResourceRole::Index)
            return {};

        constexpr DWORD classifiedFlags =
            D3DLOCK_READONLY | D3DLOCK_DISCARD | D3DLOCK_NOOVERWRITE;
        if ((lockFlags & ~classifiedFlags) != 0)
            return {};

        const bool readOnly = (lockFlags & D3DLOCK_READONLY) != 0;
        const bool discard = (lockFlags & D3DLOCK_DISCARD) != 0;
        const bool noOverwrite = (lockFlags & D3DLOCK_NOOVERWRITE) != 0;
        if ((readOnly && (discard || noOverwrite)) ||
            (discard && noOverwrite))
            return {};
        if (readOnly && (usage & D3DUSAGE_WRITEONLY) != 0)
            return {};

        const auto behavior = translate_resource_behavior(role, pool, usage);
        if (!behavior.descriptorExact)
            return {};

        BufferMutationTranslation out{};
        if (pool == D3DPOOL_MANAGED)
        {
            if (discard || noOverwrite)
                return {};
            out.kind = readOnly
                ? BufferMutationUpdateKind::ManagedCpuShadowRead
                : BufferMutationUpdateKind::ManagedCpuShadowWrite;
            // R121: the CPU-shadow/reset-generation implementation now makes
            // this mutation *plan* exact. Live mirror/draw readiness remains
            // independently gated by requiresCpuShadow and R119 snapshots.
            out.planExact = true;
            out.requiresCpuShadow = true;
            return out;
        }

        if (readOnly)
            return {};

        if (behavior.usage == D3D11_USAGE_DYNAMIC)
        {
            out.planExact = true;
            if (discard)
            {
                out.kind = BufferMutationUpdateKind::DynamicMapWriteDiscard;
                out.mapType = D3D11_MAP_WRITE_DISCARD;
            }
            else if (noOverwrite)
            {
                out.kind = BufferMutationUpdateKind::DynamicMapWriteNoOverwrite;
                out.mapType = D3D11_MAP_WRITE_NO_OVERWRITE;
            }
            else
            {
                out.kind = BufferMutationUpdateKind::DynamicMapWrite;
                out.mapType = D3D11_MAP_WRITE;
            }
            return out;
        }

        if (discard || noOverwrite)
            return {};

        out.kind = BufferMutationUpdateKind::DefaultUpdateSubresource;
        out.planExact = true;
        return out;
    }

    TextureMutationTranslation translate_texture_mutation(
        D3DPOOL pool,
        DWORD usage,
        DWORD lockFlags,
        bool fullSubresource) noexcept
    {
        constexpr DWORD classifiedFlags =
            D3DLOCK_READONLY | D3DLOCK_DISCARD | D3DLOCK_NOOVERWRITE;
        if ((lockFlags & ~classifiedFlags) != 0)
            return {};

        const bool readOnly = (lockFlags & D3DLOCK_READONLY) != 0;
        const bool discard = (lockFlags & D3DLOCK_DISCARD) != 0;
        const bool noOverwrite = (lockFlags & D3DLOCK_NOOVERWRITE) != 0;
        if ((readOnly && (discard || noOverwrite)) ||
            (discard && noOverwrite))
            return {};

        const auto behavior = translate_resource_behavior(
            ResourceRole::Texture, pool, usage);
        if (!behavior.descriptorExact)
            return {};

        TextureMutationTranslation out{};
        if (pool == D3DPOOL_MANAGED)
        {
            if (discard || noOverwrite)
                return {};
            out.kind = readOnly
                ? TextureMutationUpdateKind::ManagedCpuShadowRead
                : TextureMutationUpdateKind::ManagedCpuShadowWrite;
            out.requiresCpuShadow = true;
            return out;
        }

        if (pool != D3DPOOL_DEFAULT ||
            behavior.usage != D3D11_USAGE_DYNAMIC ||
            readOnly || noOverwrite)
            return {};

        // WRITE_DISCARD invalidates prior contents. Without a full-subresource
        // source lock, untouched texels cannot be preserved exactly.
        out.requiresFullSubresource = true;
        if (!discard || !fullSubresource)
            return out;

        out.kind = TextureMutationUpdateKind::DynamicMapWriteDiscard;
        out.mapType = D3D11_MAP_WRITE_DISCARD;
        out.planExact = true;
        return out;
    }
}
