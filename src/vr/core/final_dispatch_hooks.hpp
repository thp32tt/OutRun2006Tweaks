#pragma once

#include <Windows.h>
#include <d3d9.h>

namespace OutRunVRStereo
{
    // R33 final-dispatch hook destinations.
    //
    // These declarations are intentionally separated from the R33
    // implementation TU so R34 can eventually compile against a stable
    // interface instead of textually including stereo_renderer_r33.cpp.
    HRESULT __stdcall DrawPrimitiveDestR33(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount);

    HRESULT __stdcall DrawIndexedPrimitiveDestR33(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount);

    HRESULT __stdcall DrawPrimitiveUPDestR33(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride);

    HRESULT __stdcall DrawIndexedPrimitiveUPDestR33(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride);

    HRESULT __stdcall ResetDestR33(
        IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params);

    HRESULT __stdcall PresentDestR33(
        IDirect3DDevice9* device,
        const RECT* sourceRect, const RECT* destRect,
        HWND destWindowOverride, const RGNDATA* dirtyRegion);
}
