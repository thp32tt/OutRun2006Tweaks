#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    HRESULT TryXyzrhwPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount);

    HRESULT TryXyzrhwIndexedPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount);

    HRESULT TryXyzrhwPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride);

    HRESULT TryXyzrhwIndexedPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride);
}
