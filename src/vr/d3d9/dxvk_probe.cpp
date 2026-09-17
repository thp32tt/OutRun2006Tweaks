#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <atomic>

#include <spdlog/spdlog.h>

#include "game_addrs.hpp"
#include "hook_mgr.hpp"
#include "plugin.hpp"

// DXVK compatibility probe for the isolated multiview experiment branch.
//
// This file is intentionally non-invasive: it does not replace any D3D9 method,
// does not submit Vulkan work and does not change R31 stereo routing.  It only
// asks the live game device for DXVK's public ID3D9VkInteropDevice interface.
// Stock Microsoft/NVIDIA D3D9 returns E_NOINTERFACE; upstream DXVK exposes the
// interface from D3D9DeviceEx::QueryInterface.
//
// Upstream DXVK IID (src/d3d9/d3d9_interfaces.h):
//   ID3D9VkInteropDevice = 2eaa4b89-0107-4bdb-87f7-0f541c493ce0
//
// Keeping the probe at IUnknown level means the normal Tweaks build does not
// need Vulkan SDK headers or a source-level dependency on DXVK.
namespace OutRunVRDxvkProbe
{
    namespace
    {
        constexpr GUID DxvkVkInteropDeviceIid{
            0x2eaa4b89u, 0x0107u, 0x4bdbu,
            { 0x87u, 0xf7u, 0x0fu, 0x54u, 0x1cu, 0x49u, 0x3cu, 0xe0u }
        };

        std::atomic<bool> ProbeCompleted{ false };
        std::atomic<bool> DxvkDetected{ false };

        bool ProbeDevice(IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return false;

            IUnknown* interop = nullptr;
            const HRESULT hr = device->QueryInterface(
                DxvkVkInteropDeviceIid,
                reinterpret_cast<void**>(&interop));

            const bool detected = SUCCEEDED(hr) && interop != nullptr;
            if (interop)
                interop->Release();

            DxvkDetected.store(detected, std::memory_order_release);
            ProbeCompleted.store(true, std::memory_order_release);

            if (detected)
            {
                spdlog::info(
                    "VR DXVK POC: DXVK ID3D9VkInteropDevice detected; stock DXVK interop is available. Rendering remains on the unchanged R31 two-pass path.");
            }
            else
            {
                spdlog::info(
                    "VR DXVK POC: DXVK ID3D9VkInteropDevice not present (QueryInterface hr=0x{:08X}); classic D3D9 path remains unchanged.",
                    static_cast<unsigned>(hr));
            }

            return detected;
        }

        DWORD WINAPI DxvkProbeThread(void*)
        {
            // Follow the renderer's device-publication model rather than
            // intercepting Direct3DCreate9. This keeps the probe completely
            // independent from D3D9Ex promotion and the R31 hook transaction.
            for (int attempt = 0; attempt < 1200; ++attempt)
            {
                if (Game::D3DDevice_ptr && *Game::D3DDevice_ptr)
                {
                    ProbeDevice(*Game::D3DDevice_ptr);
                    return 0;
                }
                Sleep(100);
            }

            ProbeCompleted.store(true, std::memory_order_release);
            spdlog::warn(
                "VR DXVK POC: game D3D9 device was not published; DXVK probe could not run.");
            return 0;
        }

        class DxvkCompatibilityProbeHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRDXVKCompatibilityProbe";
            }

            bool validate() override { return true; }

            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, DxvkProbeThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    spdlog::error(
                        "VR DXVK POC: failed to start compatibility probe thread: {}",
                        GetLastError());
                    return false;
                }
                CloseHandle(thread);
                return true;
            }

            static DxvkCompatibilityProbeHook instance;
        };

        DxvkCompatibilityProbeHook DxvkCompatibilityProbeHook::instance;
    }

    bool IsProbeComplete() noexcept
    {
        return ProbeCompleted.load(std::memory_order_acquire);
    }

    bool IsDxvkDetected() noexcept
    {
        return DxvkDetected.load(std::memory_order_acquire);
    }
}
