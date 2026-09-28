#pragma once

#include <d3d9.h>

namespace OutRunVR::DrawState
{
    struct RenderStateSnapshot
    {
        DWORD zEnable = D3DZB_TRUE;
        DWORD zWriteEnable = TRUE;
        DWORD zFunc = D3DCMP_LESSEQUAL;

        DWORD alphaBlendEnable = FALSE;
        DWORD srcBlend = D3DBLEND_ONE;
        DWORD destBlend = D3DBLEND_ZERO;
        DWORD blendOp = D3DBLENDOP_ADD;

        DWORD alphaTestEnable = FALSE;
        DWORD alphaRef = 0;
        DWORD alphaFunc = D3DCMP_ALWAYS;

        DWORD cullMode = D3DCULL_CCW;
        DWORD colorWriteEnable =
            D3DCOLORWRITEENABLE_RED |
            D3DCOLORWRITEENABLE_GREEN |
            D3DCOLORWRITEENABLE_BLUE |
            D3DCOLORWRITEENABLE_ALPHA;

        DWORD stencilEnable = FALSE;
        DWORD stencilWriteMask = 0xFFFFFFFFu;

        DWORD fogEnable = FALSE;
        DWORD lighting = FALSE;

        bool complete = false;
    };
}

namespace OutRunVRStereo
{
    // Reuses the existing game-authored render-state shadow. No new D3D9 vtable
    // hook is installed for backend development.
    bool CaptureTrackedRenderStateSnapshot(
        IDirect3DDevice9* device,
        OutRunVR::DrawState::RenderStateSnapshot& out) noexcept;
}
