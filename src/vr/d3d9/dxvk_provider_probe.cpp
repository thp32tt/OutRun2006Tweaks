#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <cwchar>
#include <string>

#include "vr/d3d9/dxvk_provider_probe.hpp"
#include "vr/game/disasm_render_contract.hpp"

namespace OutRunVR::Dxvk
{
    namespace
    {
        // Historical stock-DXVK D3D9 Vulkan interop IID already used by the
        // previous PoC. This is detection only; no custom fork API is armed.
        const GUID DxvkVkInteropDeviceIid{
            0x2eaa4b89u, 0x0107u, 0x4bdbu,
            { 0x87u, 0xf7u, 0x0fu, 0x54u, 0x1cu, 0x49u, 0x3cu, 0xe0u }
        };

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

        if (!device)
            return snapshot;

        IUnknown* stockInterop = nullptr;
        const HRESULT stockHr = device->QueryInterface(
            DxvkVkInteropDeviceIid,
            reinterpret_cast<void**>(&stockInterop));
        snapshot.stockDxvkInteropHr = static_cast<long>(stockHr);
        snapshot.stockDxvkInterop =
            SUCCEEDED(stockHr) && stockInterop != nullptr;
        if (stockInterop)
            stockInterop->Release();

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
}
