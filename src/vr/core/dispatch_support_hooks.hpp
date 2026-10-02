#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    // R31 cached-world dispatch hook destinations consumed by R32.
    HRESULT __stdcall DrawPrimitiveDestR31(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount);

    HRESULT __stdcall DrawIndexedPrimitiveDestR31(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount);

    HRESULT __stdcall DrawPrimitiveUPDestR31(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride);

    HRESULT __stdcall DrawIndexedPrimitiveUPDestR31(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride);
}
