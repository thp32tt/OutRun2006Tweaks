#pragma once

#include <Windows.h>
#include <d3d9.h>

namespace OutRunVR::Core
{
    struct DispatchResult
    {
        bool handled = false;
        HRESULT hr = D3D_OK;
    };
}
