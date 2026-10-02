#pragma once

#include <Windows.h>
#include <d3d9.h>

namespace OutRunVRStereo
{
    // R32 review/corrected-dispatch hook destinations consumed by R33.
    // Kept as an internal interface so the textual R32 implementation include
    // can later be removed behind an explicit build/link gate.
    HRESULT __stdcall DrawPrimitiveDestR32(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount);

    HRESULT __stdcall DrawIndexedPrimitiveDestR32(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount);

    HRESULT __stdcall DrawPrimitiveUPDestR32(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride);

    HRESULT __stdcall DrawIndexedPrimitiveUPDestR32(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride);

    HRESULT __stdcall ResetDestR32(
        IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params);

    HRESULT __stdcall PresentDestR32(
        IDirect3DDevice9* device,
        const RECT* sourceRect, const RECT* destRect,
        HWND destWindowOverride, const RGNDATA* dirtyRegion);
}
