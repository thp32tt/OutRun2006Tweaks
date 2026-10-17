#pragma once

#include <cstdint>
#include <d3d9.h>

namespace outrun::vr::dx11
{
    // R294 preserves the exact source draw-call identity required by the
    // future production R258 revalidation producer. User-memory draws remain
    // explicitly ineligible for native-buffer evidence even though their call
    // identity is complete. This is diagnostic metadata only.
    enum class SourceDrawKind : std::uint8_t
    {
        Unknown = 0,
        NonIndexed,
        Indexed,
        NonIndexedUserMemory,
        IndexedUserMemory,
    };

    struct SourceDrawObservation
    {
        SourceDrawKind kind = SourceDrawKind::Unknown;
        D3DPRIMITIVETYPE primitive = D3DPT_FORCE_DWORD;
        UINT primitiveCount{};
        UINT startVertex{};
        INT baseVertexIndex{};
        UINT minVertexIndex{};
        UINT numVertices{};
        UINT startIndex{};
        D3DFORMAT indexFormat = D3DFMT_UNKNOWN;
        UINT vertexStride{};

        [[nodiscard]] bool native_buffer_eligible() const noexcept
        {
            return kind == SourceDrawKind::NonIndexed ||
                kind == SourceDrawKind::Indexed;
        }
    };

    [[nodiscard]] inline SourceDrawObservation
    make_nonindexed_source_draw_observation(
        D3DPRIMITIVETYPE primitive, UINT startVertex,
        UINT primitiveCount) noexcept
    {
        SourceDrawObservation out{};
        out.kind = SourceDrawKind::NonIndexed;
        out.primitive = primitive;
        out.primitiveCount = primitiveCount;
        out.startVertex = startVertex;
        return out;
    }

    [[nodiscard]] inline SourceDrawObservation
    make_indexed_source_draw_observation(
        D3DPRIMITIVETYPE primitive, INT baseVertexIndex,
        UINT minVertexIndex, UINT numVertices, UINT startIndex,
        UINT primitiveCount) noexcept
    {
        SourceDrawObservation out{};
        out.kind = SourceDrawKind::Indexed;
        out.primitive = primitive;
        out.primitiveCount = primitiveCount;
        out.baseVertexIndex = baseVertexIndex;
        out.minVertexIndex = minVertexIndex;
        out.numVertices = numVertices;
        out.startIndex = startIndex;
        return out;
    }

    [[nodiscard]] inline SourceDrawObservation
    make_nonindexed_up_source_draw_observation(
        D3DPRIMITIVETYPE primitive, UINT primitiveCount,
        UINT vertexStride) noexcept
    {
        SourceDrawObservation out{};
        out.kind = SourceDrawKind::NonIndexedUserMemory;
        out.primitive = primitive;
        out.primitiveCount = primitiveCount;
        out.vertexStride = vertexStride;
        return out;
    }

    [[nodiscard]] inline SourceDrawObservation
    make_indexed_up_source_draw_observation(
        D3DPRIMITIVETYPE primitive, UINT minVertexIndex,
        UINT numVertices, UINT primitiveCount, D3DFORMAT indexFormat,
        UINT vertexStride) noexcept
    {
        SourceDrawObservation out{};
        out.kind = SourceDrawKind::IndexedUserMemory;
        out.primitive = primitive;
        out.primitiveCount = primitiveCount;
        out.minVertexIndex = minVertexIndex;
        out.numVertices = numVertices;
        out.indexFormat = indexFormat;
        out.vertexStride = vertexStride;
        return out;
    }

    // Passive R72-R77 census. Enabled only when OUTRUN_VR_DX11_CENSUS=1.
    // It never mutates D3D9 state and never routes a draw to D3D11.
    void observe_source_draw(
        IDirect3DDevice9* device,
        const SourceDrawObservation& draw) noexcept;

    // R74 consumes the already-installed R30 VB/IB hooks as observation points.
    // A successful non-READONLY Lock followed by a successful Unlock is evidence
    // of a real source mutation pattern only; it does not activate native draws
    // or claim that the corresponding D3D11 mirror/update path is complete.
    void observe_vertex_buffer_lock(
        IDirect3DVertexBuffer9* buffer,
        UINT offset,
        UINT size,
        DWORD flags) noexcept;
    void observe_vertex_buffer_unlock(
        IDirect3DVertexBuffer9* buffer,
        HRESULT result) noexcept;
    void forget_vertex_buffer_mutation(
        IDirect3DVertexBuffer9* buffer) noexcept;

    void observe_index_buffer_lock(
        IDirect3DIndexBuffer9* buffer,
        UINT offset,
        UINT size,
        DWORD flags) noexcept;
    void observe_index_buffer_unlock(
        IDirect3DIndexBuffer9* buffer,
        HRESULT result) noexcept;
    void forget_index_buffer_mutation(
        IDirect3DIndexBuffer9* buffer) noexcept;

    // R76 adds passive texture mutation/update coverage. These observation
    // points record successful 2D LockRect/UnlockRect pairs plus device-level
    // UpdateTexture/UpdateSurface outcomes only. They do not create D3D11
    // mirrors, clear the R73 mutation gate, or enable native draw routing.
    void observe_texture_lock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        DWORD flags) noexcept;
    void observe_texture_unlock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        HRESULT result) noexcept;

    // R105 census-only MANAGED texture shadow capture. LockRect begins a
    // per-texture transaction after the real lock succeeds. UnlockRect staging
    // runs before the real COM UnlockRect; finish commits only on real success.
    // No SRV is bound and no draw is rerouted.
    bool observe_managed_texture_lock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        const D3DLOCKED_RECT& lockedRect,
        const RECT* rect,
        DWORD flags) noexcept;
    bool stage_managed_texture_unlock_rect(
        IDirect3DTexture9* texture,
        UINT level) noexcept;
    bool finish_managed_texture_unlock_rect(
        IDirect3DTexture9* texture,
        UINT level,
        HRESULT result) noexcept;
    void forget_texture_mutation(
        IDirect3DTexture9* texture) noexcept;
    void clear_managed_texture_shadows() noexcept;

    void observe_update_texture(
        IDirect3DBaseTexture9* source,
        IDirect3DBaseTexture9* destination,
        HRESULT result) noexcept;
    void observe_update_surface(
        IDirect3DSurface9* source,
        IDirect3DSurface9* destination,
        HRESULT result) noexcept;

    // R77 advances the modeled D3D11 device generation only after a successful
    // D3D9 Reset. MANAGED CPU-shadow validity/version is preserved while any
    // generation-bound mirror becomes stale.
    void observe_device_reset_generation(HRESULT result) noexcept;
}
