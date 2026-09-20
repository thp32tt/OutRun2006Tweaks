#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <atomic>
#include <cwchar>
#include <filesystem>
#include <iterator>
#include <string>

#include <spdlog/spdlog.h>

#include "game_addrs.hpp"
#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "vr/d3d9/dxvk_interop.hpp"
#include "vr/d3d9/dxvk_probe.hpp"

namespace OutRunVRDxvkProbe
{
    namespace
    {
        // Public stock-DXVK D3D9 Vulkan interop IID.
        constexpr GUID DxvkVkInteropDeviceIid{
            0x2eaa4b89u, 0x0107u, 0x4bdbu,
            { 0x87u, 0xf7u, 0x0fu, 0x54u, 0x1cu, 0x49u, 0x3cu, 0xe0u }
        };

        std::atomic<bool> ProbeCompleted{false};
        std::atomic<bool> DxvkDetected{false};
        std::atomic<bool> CustomInteropDetected{false};
        std::atomic<bool> CustomInteropCompatible{false};
        std::atomic<bool> NonSystemProvider{false};
        std::atomic<bool> D3D9ExExposed{false};
        std::atomic<std::uint32_t> CustomProtocolVersion{0};
        std::atomic<std::uint32_t> CustomCapabilityFlags{0};
        std::atomic<long> DxvkInteropHr{E_PENDING};
        std::atomic<long> CustomInteropHr{E_PENDING};

        bool ModulePath(HMODULE module, std::wstring& out) noexcept
        {
            if (!module)
                return false;
            wchar_t buffer[32768]{};
            const DWORD count = GetModuleFileNameW(
                module, buffer, static_cast<DWORD>(std::size(buffer)));
            if (count == 0 || count >= std::size(buffer))
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
                systemDir, static_cast<UINT>(std::size(systemDir)));
            if (systemLen == 0 || systemLen >= std::size(systemDir))
                return true;

            std::wstring prefix(systemDir, systemLen);
            if (!prefix.empty() && prefix.back() != L'\\')
                prefix.push_back(L'\\');

            return modulePath.size() >= prefix.size() &&
                _wcsnicmp(modulePath.c_str(), prefix.c_str(), prefix.size()) == 0;
        }

        void LogProvider() noexcept
        {
            HMODULE provider = GetModuleHandleW(L"d3d9.dll");
            std::wstring path;
            ModulePath(provider, path);
            const bool nonSystem = provider && !IsSystemD3D9Provider(provider);
            NonSystemProvider.store(nonSystem, std::memory_order_release);

            if (!path.empty())
            {
                spdlog::info(
                    "VR DXVK PROBE: d3d9 provider={} nonSystem={}",
                    std::string(path.begin(), path.end()), nonSystem ? 1 : 0);
            }
            else
            {
                spdlog::warn("VR DXVK PROBE: d3d9.dll provider path unavailable");
            }
        }

        bool ProbeDevice(IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return false;

            LogProvider();

            IUnknown* stockInterop = nullptr;
            const HRESULT dxvkHr = device->QueryInterface(
                DxvkVkInteropDeviceIid,
                reinterpret_cast<void**>(&stockInterop));
            const bool dxvk = SUCCEEDED(dxvkHr) && stockInterop != nullptr;
            if (stockInterop)
                stockInterop->Release();

            DxvkInteropHr.store(dxvkHr, std::memory_order_release);
            DxvkDetected.store(dxvk, std::memory_order_release);

            IDirect3DDevice9Ex* deviceEx = nullptr;
            const HRESULT exHr = device->QueryInterface(
                __uuidof(IDirect3DDevice9Ex),
                reinterpret_cast<void**>(&deviceEx));
            const bool ex = SUCCEEDED(exHr) && deviceEx != nullptr;
            if (deviceEx)
                deviceEx->Release();
            D3D9ExExposed.store(ex, std::memory_order_release);

            ID3D9OutRunVRInterop* custom = nullptr;
            const HRESULT customHr = device->QueryInterface(
                __uuidof(ID3D9OutRunVRInterop),
                reinterpret_cast<void**>(&custom));
            bool customDetected = SUCCEEDED(customHr) && custom != nullptr;
            bool customCompatible = false;
            std::uint32_t protocol = 0;
            std::uint32_t capabilities = 0;
            if (customDetected)
            {
                const HRESULT versionHr = custom->GetProtocolVersion(&protocol);
                const bool protocolOk = SUCCEEDED(versionHr) &&
                    protocol == OutRunVR::DxvkInterop::ProtocolVersion;
                const HRESULT capsHr = protocolOk
                    ? custom->GetCapabilities(&capabilities)
                    : E_NOINTERFACE;
                constexpr std::uint32_t requiredCaps =
                    OutRunVR::DxvkInterop::CapabilityWorldMultiview |
                    OutRunVR::DxvkInterop::CapabilityExternalRightTargets;
                customCompatible = protocolOk && SUCCEEDED(capsHr) &&
                    (capabilities & requiredCaps) == requiredCaps;
                custom->Release();
            }

            CustomInteropHr.store(customHr, std::memory_order_release);
            CustomProtocolVersion.store(protocol, std::memory_order_release);
            CustomCapabilityFlags.store(capabilities, std::memory_order_release);
            CustomInteropDetected.store(customDetected, std::memory_order_release);
            CustomInteropCompatible.store(customCompatible, std::memory_order_release);
            ProbeCompleted.store(true, std::memory_order_release);

            if (dxvk)
            {
                spdlog::info(
                    "VR DXVK PROBE: stock ID3D9VkInteropDevice detected; D3D9Ex={} customStereo={} protocol={} capabilities=0x{:08X} compatible={}",
                    ex ? 1 : 0,
                    customDetected ? 1 : 0,
                    protocol,
                    capabilities,
                    customCompatible ? 1 : 0);

                if (!customDetected)
                {
                    spdlog::info(
                        "VR DXVK PROBE: compatibility mode active; custom multiview interface absent, existing fail-closed stereo/fallback path remains authoritative");
                }
                else if (!customCompatible)
                {
                    if (protocol != OutRunVR::DxvkInterop::ProtocolVersion)
                    {
                        spdlog::error(
                            "VR DXVK PROBE: custom interface protocol mismatch (game={} provider={}); custom stereo disabled",
                            OutRunVR::DxvkInterop::ProtocolVersion,
                            protocol);
                    }
                    else
                    {
                        spdlog::info(
                            "VR DXVK PROBE: custom protocol v{} detected but required multiview capability bits are not advertised (flags=0x{:08X}); validated two-pass fallback remains active",
                            protocol, capabilities);
                    }
                }
            }
            else
            {
                spdlog::info(
                    "VR DXVK PROBE: stock DXVK interop absent (hr=0x{:08X}); normal D3D9 path remains active",
                    static_cast<unsigned>(dxvkHr));
            }

            return dxvk;
        }

        DWORD WINAPI DxvkProbeThread(void*)
        {
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
                "VR DXVK PROBE: game D3D9 device was not published within 120 seconds");
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
                LogProvider();
                HANDLE thread = CreateThread(
                    nullptr, 0, DxvkProbeThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    spdlog::error(
                        "VR DXVK PROBE: failed to start capability thread error={}",
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

    bool IsCustomInteropAvailable() noexcept
    {
        return CustomInteropCompatible.load(std::memory_order_acquire);
    }

    bool PreflightNonSystemD3D9Provider() noexcept
    {
        HMODULE provider = GetModuleHandleW(L"d3d9.dll");
        if (provider)
        {
            const bool nonSystem = !IsSystemD3D9Provider(provider);
            NonSystemProvider.store(nonSystem, std::memory_order_release);
            return nonSystem;
        }

        // Host auto-launch may run before the game's D3D9 import has been
        // resolved. A local d3d9.dll beside OR2006C2C.EXE is therefore a
        // conservative wrapper/DXVK preflight signal. Treating another local
        // wrapper the same way is safe: it merely keeps Desktop Duplication
        // available and avoids forcing the D3D9Ex-only transport too early.
        try
        {
            const auto localProvider =
                Module::ExePath.parent_path() / L"d3d9.dll";
            const bool localExists =
                !Module::ExePath.empty() && std::filesystem::exists(localProvider);
            if (localExists)
                NonSystemProvider.store(true, std::memory_order_release);
            return localExists;
        }
        catch (...)
        {
            return false;
        }
    }

    Snapshot GetSnapshot() noexcept
    {
        Snapshot snapshot{};
        snapshot.probeComplete = ProbeCompleted.load(std::memory_order_acquire);
        snapshot.dxvkDetected = DxvkDetected.load(std::memory_order_acquire);
        snapshot.customInteropDetected =
            CustomInteropDetected.load(std::memory_order_acquire);
        snapshot.customInteropCompatible =
            CustomInteropCompatible.load(std::memory_order_acquire);
        snapshot.nonSystemD3D9Provider =
            NonSystemProvider.load(std::memory_order_acquire);
        snapshot.d3d9ExExposed = D3D9ExExposed.load(std::memory_order_acquire);
        snapshot.customProtocolVersion =
            CustomProtocolVersion.load(std::memory_order_acquire);
        snapshot.customCapabilityFlags =
            CustomCapabilityFlags.load(std::memory_order_acquire);
        snapshot.dxvkInteropHr = DxvkInteropHr.load(std::memory_order_acquire);
        snapshot.customInteropHr = CustomInteropHr.load(std::memory_order_acquire);
        return snapshot;
    }
}
