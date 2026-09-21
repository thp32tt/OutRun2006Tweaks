#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define XR_USE_PLATFORM_WIN32
#define XR_USE_GRAPHICS_API_D3D11
#include <Windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

template <typename T> void ReleaseCom(T*& p) { if (p) { p->Release(); p = nullptr; } }

static void CheckXr(XrResult r, const char* where)
{
    if (XR_FAILED(r))
        throw std::runtime_error(std::string(where) + " failed: " + std::to_string(r));
}

static bool HasExtension(const char* wanted)
{
    uint32_t count = 0;
    CheckXr(xrEnumerateInstanceExtensionProperties(nullptr, 0, &count, nullptr),
            "xrEnumerateInstanceExtensionProperties(count)");
    std::vector<XrExtensionProperties> props(count, {XR_TYPE_EXTENSION_PROPERTIES});
    CheckXr(xrEnumerateInstanceExtensionProperties(nullptr, count, &count, props.data()),
            "xrEnumerateInstanceExtensionProperties(list)");
    for (const auto& p : props)
        if (std::strcmp(p.extensionName, wanted) == 0)
            return true;
    return false;
}

struct D3D
{
    IDXGIAdapter1* adapter = nullptr;
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    ~D3D() { ReleaseCom(context); ReleaseCom(device); ReleaseCom(adapter); }
};

static D3D CreateRequiredDevice(const LUID& required)
{
    IDXGIFactory1* factory = nullptr;
    if (FAILED(CreateDXGIFactory1(__uuidof(IDXGIFactory1),
        reinterpret_cast<void**>(&factory))) || !factory)
        throw std::runtime_error("CreateDXGIFactory1 failed");

    IDXGIAdapter1* chosen = nullptr;
    for (UINT i = 0;; ++i)
    {
        IDXGIAdapter1* a = nullptr;
        if (factory->EnumAdapters1(i, &a) == DXGI_ERROR_NOT_FOUND)
            break;
        DXGI_ADAPTER_DESC1 desc{};
        a->GetDesc1(&desc);
        if (desc.AdapterLuid.LowPart == required.LowPart &&
            desc.AdapterLuid.HighPart == required.HighPart)
        {
            chosen = a;
            break;
        }
        a->Release();
    }
    factory->Release();
    if (!chosen)
        throw std::runtime_error("OpenXR-required adapter LUID was not found");

    static constexpr D3D_FEATURE_LEVEL levels[] = {
        D3D_FEATURE_LEVEL_11_1, D3D_FEATURE_LEVEL_11_0,
        D3D_FEATURE_LEVEL_10_1, D3D_FEATURE_LEVEL_10_0
    };
    D3D out{};
    out.adapter = chosen;
    D3D_FEATURE_LEVEL actual{};
    const HRESULT hr = D3D11CreateDevice(
        chosen, D3D_DRIVER_TYPE_UNKNOWN, nullptr,
        D3D11_CREATE_DEVICE_BGRA_SUPPORT,
        levels, static_cast<UINT>(std::size(levels)),
        D3D11_SDK_VERSION, &out.device, &actual, &out.context);
    if (FAILED(hr) || !out.device)
        throw std::runtime_error("D3D11CreateDevice on OpenXR adapter failed");
    return out;
}

int main()
{
    XrInstance instance = XR_NULL_HANDLE;
    XrSession session = XR_NULL_HANDLE;
    try
    {
        if (!HasExtension(XR_KHR_D3D11_ENABLE_EXTENSION_NAME))
            throw std::runtime_error("32-bit runtime lacks XR_KHR_D3D11_enable");

        const char* extensions[]{XR_KHR_D3D11_ENABLE_EXTENSION_NAME};
        XrInstanceCreateInfo ci{XR_TYPE_INSTANCE_CREATE_INFO};
        std::strncpy(ci.applicationInfo.applicationName,
            "OutRun x86 OpenXR direct POC",
            sizeof(ci.applicationInfo.applicationName) - 1);
        ci.applicationInfo.applicationVersion = 1;
        std::strncpy(ci.applicationInfo.engineName, "OutRun2006Tweaks",
            sizeof(ci.applicationInfo.engineName) - 1);
        ci.applicationInfo.engineVersion = 1;
        // VDXR's 32-bit path has historically been safest with OpenXR 1.0.
        ci.applicationInfo.apiVersion = XR_MAKE_VERSION(1, 0, 34);
        ci.enabledExtensionCount = 1;
        ci.enabledExtensionNames = extensions;
        CheckXr(xrCreateInstance(&ci, &instance), "xrCreateInstance");

        XrInstanceProperties ip{XR_TYPE_INSTANCE_PROPERTIES};
        CheckXr(xrGetInstanceProperties(instance, &ip), "xrGetInstanceProperties");
        std::cout << "runtime=" << ip.runtimeName << " bits=32\n";

        XrSystemGetInfo si{XR_TYPE_SYSTEM_GET_INFO};
        si.formFactor = XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
        XrSystemId system = XR_NULL_SYSTEM_ID;
        CheckXr(xrGetSystem(instance, &si, &system), "xrGetSystem");

        PFN_xrGetD3D11GraphicsRequirementsKHR getRequirements = nullptr;
        CheckXr(xrGetInstanceProcAddr(instance, "xrGetD3D11GraphicsRequirementsKHR",
            reinterpret_cast<PFN_xrVoidFunction*>(&getRequirements)),
            "xrGetInstanceProcAddr(xrGetD3D11GraphicsRequirementsKHR)");
        if (!getRequirements)
            throw std::runtime_error("xrGetD3D11GraphicsRequirementsKHR missing");

        XrGraphicsRequirementsD3D11KHR req{XR_TYPE_GRAPHICS_REQUIREMENTS_D3D11_KHR};
        CheckXr(getRequirements(instance, system, &req),
                "xrGetD3D11GraphicsRequirementsKHR");
        D3D d3d = CreateRequiredDevice(req.adapterLuid);

        XrGraphicsBindingD3D11KHR binding{XR_TYPE_GRAPHICS_BINDING_D3D11_KHR};
        binding.device = d3d.device;
        XrSessionCreateInfo sci{XR_TYPE_SESSION_CREATE_INFO};
        sci.next = &binding;
        sci.systemId = system;
        CheckXr(xrCreateSession(instance, &sci, &session), "xrCreateSession");

        uint32_t count = 0;
        CheckXr(xrEnumerateViewConfigurationViews(
            instance, system, XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO,
            0, &count, nullptr), "xrEnumerateViewConfigurationViews(count)");
        std::vector<XrViewConfigurationView> views(
            count, {XR_TYPE_VIEW_CONFIGURATION_VIEW});
        CheckXr(xrEnumerateViewConfigurationViews(
            instance, system, XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO,
            count, &count, views.data()), "xrEnumerateViewConfigurationViews(list)");
        if (count < 2)
            throw std::runtime_error("runtime returned fewer than two stereo views");

        std::cout << "x86-direct-session=READY"
                  << " eye0=" << views[0].recommendedImageRectWidth
                  << "x" << views[0].recommendedImageRectHeight
                  << " eye1=" << views[1].recommendedImageRectWidth
                  << "x" << views[1].recommendedImageRectHeight << "\n";

        xrDestroySession(session); session = XR_NULL_HANDLE;
        xrDestroyInstance(instance); instance = XR_NULL_HANDLE;
        return 0;
    }
    catch (const std::exception& e)
    {
        if (session != XR_NULL_HANDLE) xrDestroySession(session);
        if (instance != XR_NULL_HANDLE) xrDestroyInstance(instance);
        std::cerr << "x86-direct-session=FAILED " << e.what() << "\n";
        return 1;
    }
}
