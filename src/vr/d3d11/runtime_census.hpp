#pragma once

#include <d3d9.h>

namespace outrun::vr::dx11
{
    // Passive R72-R76 census. Enabled only when OUTRUN_VR_DX11_CENSUS=1.
    // It never mutates D3D9 state and never routes a draw to D3D11.
    void observe_source_draw(
        IDirect3DDevice9* device,
        D3DPRIMITIVETYPE primitive) noexcept;

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
    void observe_update_texture(
        IDirect3DBaseTexture9* source,
        IDirect3DBaseTexture9* destination,
        HRESULT result) noexcept;
    void observe_update_surface(
        IDirect3DSurface9* source,
        IDirect3DSurface9* destination,
        HRESULT result) noexcept;
}
