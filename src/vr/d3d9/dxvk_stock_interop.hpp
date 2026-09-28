#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <Unknwn.h>

#include <cstdint>

// Minimal ABI surface from official DXVK v3.1.1 src/d3d9/d3d9_interfaces.h.
// Keep this declaration intentionally limited to the first two stock interop
// methods that are required for a passive native-transport capability gate.
// No Vulkan object is created or mutated here.
namespace OutRunVR::DxvkStock
{
    inline constexpr char ExternalMemoryWin32ExtensionName[] =
        "VK_KHR_external_memory_win32";
    inline constexpr char ExternalSemaphoreWin32ExtensionName[] =
        "VK_KHR_external_semaphore_win32";
    inline constexpr char GetMemoryWin32HandleFunction[] =
        "vkGetMemoryWin32HandleKHR";
    inline constexpr char GetSemaphoreWin32HandleFunction[] =
        "vkGetSemaphoreWin32HandleKHR";

    using VulkanVoidFn = void (WINAPI*)();
    using GetDeviceProcAddrFn =
        VulkanVoidFn (WINAPI*)(void* device, const char* name);
}

// {2EAA4B89-0107-4BDB-87F7-0F541C493CE0}
MIDL_INTERFACE("2eaa4b89-0107-4bdb-87f7-0f541c493ce0")
ID3D9VkInteropDeviceR71 : public IUnknown
{
public:
    virtual void STDMETHODCALLTYPE GetVulkanHandles(
        void** instance,
        void** physicalDevice,
        void** device) = 0;

    virtual void STDMETHODCALLTYPE GetSubmissionQueue(
        void** queue,
        std::uint32_t* queueIndex,
        std::uint32_t* queueFamilyIndex) = 0;
};
