#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <atomic>
#include <cstdint>
#include <cstring>
#include <cwchar>
#include <filesystem>
#include <string>

#include <spdlog/spdlog.h>

#include "vr/d3d9/dxvk_provider_probe.hpp"
#include "vr/d3d9/dxvk_stock_interop.hpp"
#include "vr/game/disasm_render_contract.hpp"

namespace OutRunVR::Dxvk
{
    namespace
    {
        bool ModulePath(HMODULE module, std::wstring& out) noexcept
        {
            if (!module)
                return false;

            wchar_t buffer[32768]{};
            const DWORD count = GetModuleFileNameW(
                module, buffer, static_cast<DWORD>(sizeof(buffer) / sizeof(buffer[0])));
            if (count == 0 || count >= (sizeof(buffer) / sizeof(buffer[0])))
                return false;

            out.assign(buffer, count);
            return true;
        }

        bool IsSystemD3D9Provider(HMODULE module) noexcept
        {
            std::wstring modulePath;
            if (!ModulePath(module, modulePath))
                return true;

            wchar_t systemDir[32768]{};
            const UINT systemLen = GetSystemDirectoryW(
                systemDir, static_cast<UINT>(sizeof(systemDir) / sizeof(systemDir[0])));
            if (systemLen == 0 || systemLen >= (sizeof(systemDir) / sizeof(systemDir[0])))
                return true;

            std::wstring prefix(systemDir, systemLen);
            if (!prefix.empty() && prefix.back() != L'\\')
                prefix.push_back(L'\\');

            return modulePath.size() >= prefix.size() &&
                _wcsnicmp(modulePath.c_str(), prefix.c_str(), prefix.size()) == 0;
        }

        std::atomic<std::uint64_t> ProviderAttestationSequence{0};

        void ProbeStockNativeTransportPrerequisites(
            ID3D9VkInteropDeviceR71* interop,
            ProviderSnapshot& snapshot) noexcept
        {
            if (!interop)
                return;

            void* instance = nullptr;
            void* physicalDevice = nullptr;
            void* vkDevice = nullptr;
            void* submissionQueue = nullptr;
            std::uint32_t queueIndex = 0xffffffffu;
            std::uint32_t queueFamilyIndex = 0xffffffffu;

            interop->GetVulkanHandles(
                &instance, &physicalDevice, &vkDevice);
            interop->GetSubmissionQueue(
                &submissionQueue, &queueIndex, &queueFamilyIndex);

            snapshot.stockDxvkVulkanHandles =
                instance != nullptr &&
                physicalDevice != nullptr &&
                vkDevice != nullptr;
            snapshot.stockDxvkSubmissionQueue =
                submissionQueue != nullptr &&
                queueIndex != 0xffffffffu &&
                queueFamilyIndex != 0xffffffffu;
            snapshot.stockQueueIndex = queueIndex;
            snapshot.stockQueueFamilyIndex = queueFamilyIndex;

            // DXVK v3.1.1 enables VK_KHR_external_memory_win32 and
            // VK_KHR_external_semaphore_win32 when the physical device supports
            // them. Querying the corresponding device entry points proves the
            // running stock device actually enabled those capabilities. This is
            // passive: no image, memory, semaphore, queue submission or layout
            // transition is created or performed.
            HMODULE vulkan = GetModuleHandleW(L"vulkan-1.dll");
            if (vulkan && vkDevice)
            {
                const auto getDeviceProcAddr =
                    reinterpret_cast<DxvkStock::GetDeviceProcAddrFn>(
                        GetProcAddress(vulkan, "vkGetDeviceProcAddr"));
                if (getDeviceProcAddr)
                {
                    snapshot.externalMemoryWin32 =
                        getDeviceProcAddr(
                            vkDevice,
                            DxvkStock::GetMemoryWin32HandleFunction) != nullptr;
                    snapshot.externalSemaphoreWin32 =
                        getDeviceProcAddr(
                            vkDevice,
                            DxvkStock::GetSemaphoreWin32HandleFunction) != nullptr;
                }
            }

            snapshot.nativeTransportCandidate =
                snapshot.stockDxvkVulkanHandles &&
                snapshot.stockDxvkSubmissionQueue &&
                snapshot.externalMemoryWin32 &&
                snapshot.externalSemaphoreWin32;
        }

        bool IsGameLocalD3D9Provider(HMODULE module) noexcept
        {
            try
            {
                std::wstring providerPath;
                if (!ModulePath(module, providerPath))
                    return false;

                wchar_t exeBuffer[32768]{};
                const DWORD exeCount = GetModuleFileNameW(
                    nullptr, exeBuffer,
                    static_cast<DWORD>(sizeof(exeBuffer) / sizeof(exeBuffer[0])));
                if (exeCount == 0 ||
                    exeCount >= (sizeof(exeBuffer) / sizeof(exeBuffer[0])))
                    return false;

                const auto provider =
                    std::filesystem::path(providerPath).lexically_normal();
                const auto exe =
                    std::filesystem::path(std::wstring(exeBuffer, exeCount))
                        .lexically_normal();

                return _wcsicmp(
                    provider.parent_path().c_str(),
                    exe.parent_path().c_str()) == 0 &&
                    _wcsicmp(provider.filename().c_str(), L"d3d9.dll") == 0;
            }
            catch (...)
            {
                return false;
            }
        }
    }

    static_assert(DisasmContract::WvpVsRegister == 64u);
    static_assert(DisasmContract::WvpVsRegisterCount == 4u);
    static_assert(
        DisasmContract::ClassifyCriticalProducer(0x000BAD20u) ==
        DisasmContract::SpacePolicy::WorldBillboard);

    bool PreflightNonSystemProvider() noexcept
    {
        HMODULE provider = GetModuleHandleW(L"d3d9.dll");
        return provider != nullptr && !IsSystemD3D9Provider(provider);
    }

    ProviderSnapshot ProbeProvider(IDirect3DDevice9* device) noexcept
    {
        ProviderSnapshot snapshot{};

        HMODULE provider = GetModuleHandleW(L"d3d9.dll");
        snapshot.d3d9ProviderLoaded = provider != nullptr;
        snapshot.nonSystemProvider =
            provider != nullptr && !IsSystemD3D9Provider(provider);
        snapshot.gameLocalProvider =
            provider != nullptr && IsGameLocalD3D9Provider(provider);

        if (!device)
            return snapshot;

        ID3D9VkInteropDeviceR71* stockInterop = nullptr;
        const HRESULT stockHr = device->QueryInterface(
            __uuidof(ID3D9VkInteropDeviceR71),
            reinterpret_cast<void**>(&stockInterop));
        snapshot.stockDxvkInteropHr = static_cast<long>(stockHr);
        snapshot.stockDxvkInterop =
            SUCCEEDED(stockHr) && stockInterop != nullptr;
        if (stockInterop)
        {
            ProbeStockNativeTransportPrerequisites(stockInterop, snapshot);
            stockInterop->Release();
        }

        IDirect3DDevice9Ex* deviceEx = nullptr;
        const HRESULT exHr = device->QueryInterface(
            __uuidof(IDirect3DDevice9Ex),
            reinterpret_cast<void**>(&deviceEx));
        snapshot.d3d9ExHr = static_cast<long>(exHr);
        snapshot.d3d9ExAvailable =
            SUCCEEDED(exHr) && deviceEx != nullptr;
        if (deviceEx)
            deviceEx->Release();

        return snapshot;
    }

    void LogProviderCensus(
        IDirect3DDevice9* device,
        const char* source) noexcept
    {
        const auto snapshot = ProbeProvider(device);
        const auto attestation =
            ProviderAttestationSequence.fetch_add(1, std::memory_order_relaxed) + 1;
        spdlog::info(
            "VR DXVK R71 census: providerLoaded={} nonSystem={} gameLocal={} stockInterop={} D3D9Ex={} stockHr=0x{:08X} exHr=0x{:08X} source={} attestation={} vkHandles={} vkQueue={} extMemoryWin32={} extSemaphoreWin32={} nativeTransportCandidate={} queueFamily={} queueIndex={}",
            snapshot.d3d9ProviderLoaded ? 1 : 0,
            snapshot.nonSystemProvider ? 1 : 0,
            snapshot.gameLocalProvider ? 1 : 0,
            snapshot.stockDxvkInterop ? 1 : 0,
            snapshot.d3d9ExAvailable ? 1 : 0,
            static_cast<unsigned>(snapshot.stockDxvkInteropHr),
            static_cast<unsigned>(snapshot.d3d9ExHr),
            source ? source : "unknown",
            attestation,
            snapshot.stockDxvkVulkanHandles ? 1 : 0,
            snapshot.stockDxvkSubmissionQueue ? 1 : 0,
            snapshot.externalMemoryWin32 ? 1 : 0,
            snapshot.externalSemaphoreWin32 ? 1 : 0,
            snapshot.nativeTransportCandidate ? 1 : 0,
            snapshot.stockQueueFamilyIndex,
            snapshot.stockQueueIndex);
    }
}