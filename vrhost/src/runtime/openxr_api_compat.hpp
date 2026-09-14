#pragma once

// The VR host uses only OpenXR 1.0 core entry points plus XR_KHR_D3D11_enable.
// Keep the application API request at 1.0 so runtimes that have not promoted to
// OpenXR 1.1 (including the VDXR 1.0.x runtime used by the Quest/Virtual Desktop
// test path) can create the instance. Newer 1.1 runtimes remain backwards
// compatible with an application that requests 1.0.
#include <openxr/openxr.h>

#undef XR_CURRENT_API_VERSION
#define XR_CURRENT_API_VERSION XR_API_VERSION_1_0

static_assert(XR_CURRENT_API_VERSION == XR_API_VERSION_1_0,
    "OutRun VR host must request the OpenXR 1.0 application API baseline");
