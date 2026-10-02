#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    // R30 HUD/XYZRHW/screen-space hook destinations consumed by R31.
    HRESULT __stdcall DrawPrimitiveDestR30(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount);

    HRESULT __stdcall DrawIndexedPrimitiveDestR30(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount);

    HRESULT __stdcall DrawPrimitiveUPDestR30(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride);

    HRESULT __stdcall DrawIndexedPrimitiveUPDestR30(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride);
}
