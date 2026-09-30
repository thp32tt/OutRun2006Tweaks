#pragma once

#include <Windows.h>
#include <d3d9.h>
#include <cstdint>

namespace OutRunVR::State
{
    struct DepthStencilWriteState
    {
        DWORD zEnable = D3DZB_TRUE;
        DWORD zWrite = TRUE;
        DWORD stencilEnable = FALSE;
        DWORD stencilWriteMask = 0xFFFFFFFFu;
        DWORD stencilFail = D3DSTENCILOP_KEEP;
        DWORD stencilZFail = D3DSTENCILOP_KEEP;
        DWORD stencilPass = D3DSTENCILOP_KEEP;
        DWORD twoSided = FALSE;
        DWORD ccwStencilFail = D3DSTENCILOP_KEEP;
        DWORD ccwStencilZFail = D3DSTENCILOP_KEEP;
        DWORD ccwStencilPass = D3DSTENCILOP_KEEP;
        std::uint64_t depthGeneration = 0;
        std::uint64_t stateBlockRecordings = 0;
        std::uint64_t stateBlockApplies = 0;
        bool valid = false;
    };
}
