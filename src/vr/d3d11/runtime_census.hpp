#pragma once

#include <d3d9.h>

namespace outrun::vr::dx11
{
    // Passive R72 census. Enabled only when OUTRUN_VR_DX11_CENSUS=1.
    // It never mutates D3D9 state and never routes a draw to D3D11.
    void observe_source_draw(
        IDirect3DDevice9* device,
        D3DPRIMITIVETYPE primitive) noexcept;
}
