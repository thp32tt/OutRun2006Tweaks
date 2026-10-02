#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    // R29 conservative stereo-base hook destinations consumed by R30/R33.
    HRESULT __stdcall DrawPrimitiveDestR29(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount);

    HRESULT __stdcall DrawIndexedPrimitiveDestR29(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount);

    HRESULT __stdcall DrawPrimitiveUPDestR29(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride);

    HRESULT __stdcall DrawIndexedPrimitiveUPDestR29(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride);

    HRESULT __stdcall SetRenderStateDestR29(
        IDirect3DDevice9* device, D3DRENDERSTATETYPE state, DWORD value);
}
