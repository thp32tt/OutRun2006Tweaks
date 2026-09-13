// Compatibility translation unit for OpenXR runtimes that still expose only
// the OpenXR 1.0 core API (notably some VDXR configurations).
//
// We build against newer Khronos headers/loader, but deliberately request
// OpenXR 1.0 from xrCreateInstance. Milestone 1 only uses OpenXR 1.0 core plus
// XR_KHR_D3D11_enable, so requesting 1.1 is unnecessary and can cause
// XR_ERROR_API_VERSION_UNSUPPORTED (-4) on otherwise compatible runtimes.
#include <openxr/openxr.h>

#undef XR_CURRENT_API_VERSION
#define XR_CURRENT_API_VERSION XR_MAKE_VERSION(1, 0, 0)

#include "main.cpp"
