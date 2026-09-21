#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <openxr/openxr.h>

#include <cstring>
#include <iostream>
#include <vector>

static const char* ResultName(XrResult r)
{
    switch (r)
    {
    case XR_SUCCESS: return "XR_SUCCESS";
    case XR_ERROR_RUNTIME_UNAVAILABLE: return "XR_ERROR_RUNTIME_UNAVAILABLE";
    case XR_ERROR_FORM_FACTOR_UNAVAILABLE: return "XR_ERROR_FORM_FACTOR_UNAVAILABLE";
    case XR_ERROR_INITIALIZATION_FAILED: return "XR_ERROR_INITIALIZATION_FAILED";
    default: return "XR_OTHER";
    }
}

int main()
{
    std::cout << "OutRun x86 OpenXR capability probe (" << (sizeof(void*) * 8) << "-bit)\n";

    uint32_t extCount = 0;
    XrResult r = xrEnumerateInstanceExtensionProperties(nullptr, 0, &extCount, nullptr);
    std::cout << "xrEnumerateInstanceExtensionProperties=" << ResultName(r)
              << " (" << r << "), extensions=" << extCount << "\n";
    if (XR_FAILED(r))
        return 2;

    std::vector<XrExtensionProperties> exts(extCount, { XR_TYPE_EXTENSION_PROPERTIES });
    r = xrEnumerateInstanceExtensionProperties(nullptr, extCount, &extCount, exts.data());
    if (XR_FAILED(r))
        return 3;

    XrInstanceCreateInfo ci{ XR_TYPE_INSTANCE_CREATE_INFO };
    std::strncpy(ci.applicationInfo.applicationName, "OutRun2006Tweaks x86 probe",
                 sizeof(ci.applicationInfo.applicationName) - 1);
    ci.applicationInfo.applicationVersion = 1;
    std::strncpy(ci.applicationInfo.engineName, "OutRun2006Tweaks",
                 sizeof(ci.applicationInfo.engineName) - 1);
    ci.applicationInfo.engineVersion = 1;
    // VDXR's 32-bit path has historically been stricter than 64-bit runtimes.
    // Request OpenXR 1.0 here: the probe is capability detection, not the final renderer.
    ci.applicationInfo.apiVersion = XR_MAKE_VERSION(1, 0, 34);

    XrInstance instance = XR_NULL_HANDLE;
    r = xrCreateInstance(&ci, &instance);
    std::cout << "xrCreateInstance=" << ResultName(r) << " (" << r << ")\n";
    if (XR_FAILED(r))
        return 4;

    XrInstanceProperties props{ XR_TYPE_INSTANCE_PROPERTIES };
    if (XR_SUCCEEDED(xrGetInstanceProperties(instance, &props)))
        std::cout << "runtime=" << props.runtimeName
                  << " version=" << XR_VERSION_MAJOR(props.runtimeVersion) << "."
                  << XR_VERSION_MINOR(props.runtimeVersion) << "."
                  << XR_VERSION_PATCH(props.runtimeVersion) << "\n";

    XrSystemGetInfo gi{ XR_TYPE_SYSTEM_GET_INFO };
    gi.formFactor = XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
    XrSystemId system = XR_NULL_SYSTEM_ID;
    r = xrGetSystem(instance, &gi, &system);
    std::cout << "xrGetSystem(HMD)=" << ResultName(r) << " (" << r << ")\n";

    xrDestroyInstance(instance);
    return XR_SUCCEEDED(r) ? 0 : 5;
}
