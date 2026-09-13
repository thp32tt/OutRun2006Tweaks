// Compatibility translation unit for OpenXR runtimes such as VDXR.
//
// Milestone 1 only needs OpenXR 1.0 core plus XR_KHR_D3D11_enable, so request
// OpenXR 1.0 even though we build against newer Khronos headers/loader.
//
// VDXR can also report XR_ERROR_FORM_FACTOR_UNAVAILABLE while the Quest / VD
// session is still becoming available. OpenXR explicitly permits retrying
// xrGetSystem in that state, so keep the host alive instead of exiting.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <openxr/openxr.h>

#include <iostream>

static XrResult XRAPI_PTR OutRunRetryingXrGetSystem(
    XrInstance instance,
    const XrSystemGetInfo* getInfo,
    XrSystemId* systemId)
{
    bool waitingReported = false;

    for (;;)
    {
        const XrResult result = ::xrGetSystem(instance, getInfo, systemId);
        if (result != XR_ERROR_FORM_FACTOR_UNAVAILABLE)
        {
            if (waitingReported && XR_SUCCEEDED(result))
                std::cout << "OpenXR HMD is now available. Continuing startup.\n";
            return result;
        }

        if (!waitingReported)
        {
            std::cout
                << "OpenXR runtime is available, but no HMD is ready yet.\n"
                << "Waiting for Quest / Virtual Desktop VR session...\n"
                << "Keep the headset awake and connected. Ctrl+C cancels.\n";
            waitingReported = true;
        }

        Sleep(1000);
    }
}

#undef XR_CURRENT_API_VERSION
#define XR_CURRENT_API_VERSION XR_MAKE_VERSION(1, 0, 0)

// Route the host's xrGetSystem call through the retrying wrapper above.
#define xrGetSystem OutRunRetryingXrGetSystem
#include "main.cpp"
