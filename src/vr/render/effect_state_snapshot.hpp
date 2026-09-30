#pragma once

#include <Windows.h>
#include <d3d9.h>

namespace OutRunVR::Render
{
    struct EffectStateSnapshot
    {
        DWORD alphaBlend = FALSE;
        DWORD alphaTest = FALSE;
        DWORD zWrite = TRUE;
        DWORD zEnable = D3DZB_TRUE;
        DWORD cullMode = D3DCULL_CCW;
    };
}
