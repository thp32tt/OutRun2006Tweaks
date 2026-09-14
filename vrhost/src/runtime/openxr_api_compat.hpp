#pragma once

// The VR host only needs OpenXR 1.0 core entry points plus XR_KHR_D3D11_enable.
// Keep the application API request at 1.0 so VDXR 1.0.x can create the instance.
//
// Do not depend on XR_API_VERSION_1_0 here: older OpenXR headers do not define
// that convenience macro. XR_MAKE_VERSION is part of the OpenXR 1.0 header and
// therefore works with both old 1.0 headers and current 1.1 SDK headers.
#include <openxr/openxr.h>

#undef XR_CURRENT_API_VERSION
#define XR_CURRENT_API_VERSION XR_MAKE_VERSION(1, 0, 0)

static_assert(XR_VERSION_MAJOR(XR_CURRENT_API_VERSION) == 1 &&
              XR_VERSION_MINOR(XR_CURRENT_API_VERSION) == 0,
    "OutRun VR host must request the OpenXR 1.0 application API baseline");
