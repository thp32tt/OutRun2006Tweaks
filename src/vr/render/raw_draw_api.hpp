#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    HRESULT CallRawDrawPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount) noexcept;

    HRESULT CallRawDrawIndexedPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount) noexcept;

    HRESULT CallRawDrawPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride) noexcept;

    HRESULT CallRawDrawIndexedPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride) noexcept;
}
