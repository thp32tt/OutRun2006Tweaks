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
        DWORD separateAlphaBlendEnable = FALSE;
        DWORD srcBlendAlpha = D3DBLEND_ONE;
        DWORD destBlendAlpha = D3DBLEND_ZERO;
        DWORD blendOpAlpha = D3DBLENDOP_ADD;

        DWORD alphaTestEnable = FALSE;
        DWORD alphaRef = 0;
        DWORD alphaFunc = D3DCMP_ALWAYS;

        DWORD cullMode = D3DCULL_CCW;
        DWORD fillMode = D3DFILL_SOLID;
        DWORD scissorTestEnable = FALSE;
        DWORD sRGBWriteEnable = FALSE;
        DWORD colorWriteEnable =
            D3DCOLORWRITEENABLE_RED |
            D3DCOLORWRITEENABLE_GREEN |
            D3DCOLORWRITEENABLE_BLUE |
            D3DCOLORWRITEENABLE_ALPHA;

        DWORD stencilEnable = FALSE;
        DWORD stencilReadMask = 0xFFFFFFFFu;
        DWORD stencilWriteMask = 0xFFFFFFFFu;
        DWORD stencilRef = 0;
        DWORD stencilFail = D3DSTENCILOP_KEEP;
        DWORD stencilZFail = D3DSTENCILOP_KEEP;
        DWORD stencilPass = D3DSTENCILOP_KEEP;
        DWORD stencilFunc = D3DCMP_ALWAYS;
        DWORD twoSidedStencilMode = FALSE;
        DWORD ccwStencilFail = D3DSTENCILOP_KEEP;
        DWORD ccwStencilZFail = D3DSTENCILOP_KEEP;
        DWORD ccwStencilPass = D3DSTENCILOP_KEEP;
        DWORD ccwStencilFunc = D3DCMP_ALWAYS;

        // D3D9 fog parameters are render-state DWORDs. Float-valued states
        // retain their raw IEEE-754 bit patterns so the DX11 census can prove
        // exact semantic identity before any native fog implementation.
        DWORD fogEnable = FALSE;
        DWORD fogColor = 0;
        DWORD fogTableMode = D3DFOG_NONE;
        DWORD fogStartBits = 0x00000000u;
        DWORD fogEndBits = 0x3F800000u;
        DWORD fogDensityBits = 0x3F800000u;
        DWORD rangeFogEnable = FALSE;
        DWORD fogVertexMode = D3DFOG_NONE;
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