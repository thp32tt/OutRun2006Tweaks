#pragma once

// Production OpenXR compatibility shim.
//
// VirtualDesktopXR 1.0.x is the primary runtime for this project. Keep the
// application request on the OpenXR 1.0 API baseline, but do not intercept
// xrEndFrame or create diagnostic swapchains in the production host.
//
// R9's alternating test-pattern layer was useful while proving compositor
// visibility, but it also owned extra swapchain acquire/wait/release state and
// could become active exactly when the game projection layer was temporarily
// unavailable. R20 deliberately removes that diagnostic behavior from the
// normal host and leaves only the API-version compatibility contract.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <Windows.h>
#include <d3d11.h>

// Forced includes run before main.cpp defines the OpenXR platform/graphics
// macros. Define them only while the OpenXR headers are parsed, then remove
// only the definitions introduced here so main.cpp remains source-compatible.
#ifndef XR_USE_PLATFORM_WIN32
#define OUTRUN_R20_DEFINED_XR_PLATFORM 1
#define XR_USE_PLATFORM_WIN32
#endif
#ifndef XR_USE_GRAPHICS_API_D3D11
#define OUTRUN_R20_DEFINED_XR_D3D11 1
#define XR_USE_GRAPHICS_API_D3D11
#endif

#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

#ifdef OUTRUN_R20_DEFINED_XR_PLATFORM
#undef XR_USE_PLATFORM_WIN32
#undef OUTRUN_R20_DEFINED_XR_PLATFORM
#endif
#ifdef OUTRUN_R20_DEFINED_XR_D3D11
#undef XR_USE_GRAPHICS_API_D3D11
#undef OUTRUN_R20_DEFINED_XR_D3D11
#endif

#ifdef XR_CURRENT_API_VERSION
#undef XR_CURRENT_API_VERSION
#endif
#define XR_CURRENT_API_VERSION XR_MAKE_VERSION(1, 0, 0)
