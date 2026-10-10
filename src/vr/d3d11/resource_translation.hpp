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

    enum class BufferMutationUpdateKind : std::uint8_t
    {
        Unsupported = 0,
        DynamicMapWrite,
        DynamicMapWriteDiscard,
        DynamicMapWriteNoOverwrite,
        DefaultUpdateSubresource,
        ManagedCpuShadowRead,
        ManagedCpuShadowWrite,
    };

    struct BufferMutationTranslation
    {
        BufferMutationUpdateKind kind = BufferMutationUpdateKind::Unsupported;
        D3D11_MAP mapType = D3D11_MAP_WRITE;
        bool planExact = false;
        bool requiresCpuShadow = false;
    };

    // R100 models the conservative update contract for a future D3D11
    // Texture2D mirror. Only a full-subresource DISCARD write to a DEFAULT
    // D3D9 dynamic texture is currently exact enough to map to
    // D3D11_MAP_WRITE_DISCARD. Partial writes, plain writes and NOOVERWRITE
    // remain fail-closed until preservation semantics are implemented.
    enum class TextureMutationUpdateKind : std::uint8_t
    {
        Unsupported = 0,
        DynamicMapWriteDiscard,
        ManagedCpuShadowRead,
        ManagedCpuShadowWrite,
    };

    struct TextureMutationTranslation
    {
        TextureMutationUpdateKind kind = TextureMutationUpdateKind::Unsupported;
        D3D11_MAP mapType = D3D11_MAP_WRITE;
        bool planExact = false;
        bool requiresCpuShadow = false;
        bool requiresFullSubresource = false;
    };

    // R77 models the lifetime contract a future MANAGED D3D11 mirror must obey.
    // CPU shadow contents survive a successful D3D9 Reset; the GPU mirror is
    // generation-bound and must be recreated/reuploaded before use.
    struct ManagedMirrorLifetimeState
    {
        std::uint64_t deviceGeneration = 1;
        std::uint64_t cpuShadowVersion = 0;
        std::uint64_t mirrorGeneration = 0;
        std::uint64_t mirrorShadowVersion = 0;
        bool cpuShadowValid = false;
        bool mirrorValid = false;
    };

    [[nodiscard]] constexpr ManagedMirrorLifetimeState
    note_managed_shadow_write(ManagedMirrorLifetimeState state) noexcept
    {
        state.cpuShadowVersion =
            state.cpuShadowVersion == ~std::uint64_t{0}
                ? 1
                : state.cpuShadowVersion + 1;
        state.cpuShadowValid = true;
        state.mirrorValid = false;
        return state;
    }

    [[nodiscard]] constexpr ManagedMirrorLifetimeState
    note_managed_mirror_upload(ManagedMirrorLifetimeState state) noexcept
    {
        if (!state.cpuShadowValid)
            return state;
        state.mirrorGeneration = state.deviceGeneration;
        state.mirrorShadowVersion = state.cpuShadowVersion;
        state.mirrorValid = true;
        return state;
    }

    [[nodiscard]] constexpr ManagedMirrorLifetimeState
    advance_managed_device_generation(ManagedMirrorLifetimeState state) noexcept
    {
        state.deviceGeneration =
            state.deviceGeneration == ~std::uint64_t{0}
                ? 1
                : state.deviceGeneration + 1;
        state.mirrorValid = false;
        return state;
    }

    [[nodiscard]] constexpr bool
    managed_mirror_ready(const ManagedMirrorLifetimeState& state) noexcept
    {
        return state.cpuShadowValid &&
            state.mirrorValid &&
            state.mirrorGeneration == state.deviceGeneration &&
            state.mirrorShadowVersion == state.cpuShadowVersion;
    }

    static_assert(note_managed_shadow_write({}).cpuShadowValid);
    static_assert(
        managed_mirror_ready(
            note_managed_mirror_upload(note_managed_shadow_write({}))));
    static_assert(
        advance_managed_device_generation(
            note_managed_mirror_upload(note_managed_shadow_write({})))
            .cpuShadowValid);
    static_assert(
        !managed_mirror_ready(
            advance_managed_device_generation(
                note_managed_mirror_upload(note_managed_shadow_write({})))));

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

    // R75 classifies VB/IB Lock flags into a concrete future D3D11 mirror
    // update operation. planExact describes the translation plan only; it
    // does not mean that a live D3D11 mirror path or native draw is enabled.
    // R121 treats ordinary MANAGED read/write locks as exact CPU-shadow
    // operations now that the R113/R119 shadow/reset-generation model exists.
    // requiresCpuShadow remains true, so this never proves live draw readiness.
    [[nodiscard]] BufferMutationTranslation translate_buffer_mutation(
        ResourceRole role,
        D3DPOOL pool,
        DWORD usage,
        DWORD lockFlags) noexcept;

    // R100 translates observed Texture2D LockRect intent into a future mirror
    // update plan. The returned plan is readiness evidence only; it does not
    // map, copy, upload or bind a D3D11 texture.
    [[nodiscard]] TextureMutationTranslation translate_texture_mutation(
        D3DPOOL pool,
        DWORD usage,
        DWORD lockFlags,
        bool fullSubresource) noexcept;
}
