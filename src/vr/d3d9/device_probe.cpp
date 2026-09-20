#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <cstdint>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "game_addrs.hpp"
#include "../d3d12/d3d9on12_compat.hpp"

namespace OutRunVRDeviceProbe
{
    namespace
    {
        const char* DeviceTypeName(D3DDEVTYPE type) noexcept
        {
            switch (type)
            {
            case D3DDEVTYPE_HAL: return "HAL";
            case D3DDEVTYPE_REF: return "REF";
            case D3DDEVTYPE_SW: return "SW";
            case D3DDEVTYPE_NULLREF: return "NULLREF";
            default: return "UNKNOWN";
            }
        }

        DWORD WINAPI ProbeThread(void*)
        {
            for (int attempt = 0; attempt < 1200; ++attempt)
            {
                IDirect3DDevice9* device = Game::D3DDevice_ptr ? *Game::D3DDevice_ptr : nullptr;
                if (!device)
                {
                    Sleep(100);
                    continue;
                }

                D3DDEVICE_CREATION_PARAMETERS creation{};
                const HRESULT creationHr = device->GetCreationParameters(&creation);
                IDirect3DSurface9* backBuffer = nullptr;
                D3DSURFACE_DESC backDesc{};
                const HRESULT backHr = device->GetBackBuffer(
                    0, 0, D3DBACKBUFFER_TYPE_MONO, &backBuffer);
                if (SUCCEEDED(backHr) && backBuffer)
                    backBuffer->GetDesc(&backDesc);

                D3DCAPS9 caps{};
                const HRESULT capsHr = device->GetDeviceCaps(&caps);

                IDirect3DDevice9Ex* deviceEx = nullptr;
                const HRESULT exHr = device->QueryInterface(
                    __uuidof(IDirect3DDevice9Ex), reinterpret_cast<void**>(&deviceEx));
                const bool isEx = SUCCEEDED(exHr) && deviceEx;

                IDirect3DDevice9On12* deviceOn12 = nullptr;
                const HRESULT on12Hr = device->QueryInterface(
                    __uuidof(IDirect3DDevice9On12),
                    reinterpret_cast<void**>(&deviceOn12));
                const bool isOn12 = SUCCEEDED(on12Hr) && deviceOn12;
                ID3D12Device* underlying12 = nullptr;
                LUID on12Luid{};
                bool on12LuidValid = false;
                if (isOn12 &&
                    SUCCEEDED(deviceOn12->GetD3D12Device(
                        __uuidof(ID3D12Device),
                        reinterpret_cast<void**>(&underlying12))) &&
                    underlying12)
                {
                    on12Luid = underlying12->GetAdapterLuid();
                    on12LuidValid = true;
                }

                LUID adapterLuid{};
                bool luidValid = false;
                IDirect3D9* d3d = nullptr;
                IDirect3D9Ex* d3dEx = nullptr;
                if (isEx && SUCCEEDED(deviceEx->GetDirect3D(&d3d)) && d3d &&
                    SUCCEEDED(d3d->QueryInterface(__uuidof(IDirect3D9Ex),
                        reinterpret_cast<void**>(&d3dEx))) && d3dEx &&
                    SUCCEEDED(d3dEx->GetAdapterLUID(creation.AdapterOrdinal, &adapterLuid)))
                    luidValid = true;

                const DWORD flags = SUCCEEDED(creationHr) ? creation.BehaviorFlags : 0;
                spdlog::info(
                    "VR D3D9 probe: deviceType={} adapter={} D3D9Ex={} behavior=0x{:08X} multithreaded={} hwvp={} swvp={} pure={} fpuPreserve={}",
                    SUCCEEDED(creationHr) ? DeviceTypeName(creation.DeviceType) : "unavailable",
                    SUCCEEDED(creationHr) ? creation.AdapterOrdinal : 0u,
                    isEx ? 1 : 0, flags,
                    (flags & D3DCREATE_MULTITHREADED) ? 1 : 0,
                    (flags & D3DCREATE_HARDWARE_VERTEXPROCESSING) ? 1 : 0,
                    (flags & D3DCREATE_SOFTWARE_VERTEXPROCESSING) ? 1 : 0,
                    (flags & D3DCREATE_PUREDEVICE) ? 1 : 0,
                    (flags & D3DCREATE_FPU_PRESERVE) ? 1 : 0);

                spdlog::info(
                    "VR D3D9 probe: backbuffer={}x{} format={} msaa={} quality={} maxTexture={}x{} capsHr=0x{:08X}",
                    backDesc.Width, backDesc.Height, static_cast<int>(backDesc.Format),
                    static_cast<int>(backDesc.MultiSampleType), backDesc.MultiSampleQuality,
                    SUCCEEDED(capsHr) ? caps.MaxTextureWidth : 0u,
                    SUCCEEDED(capsHr) ? caps.MaxTextureHeight : 0u,
                    static_cast<unsigned>(capsHr));

                if (luidValid)
                    spdlog::info("VR D3D9 probe: adapterLuid={:08X}:{:08X}",
                        static_cast<std::uint32_t>(adapterLuid.HighPart), adapterLuid.LowPart);
                else
                    spdlog::info("VR D3D9 probe: adapter LUID unavailable from game device (expected on plain D3D9)");

                if (isOn12 && on12LuidValid)
                    spdlog::info(
                        "VR DX12 POC: D3D9On12 ACTIVE underlyingD3D12Luid={:08X}:{:08X}",
                        static_cast<std::uint32_t>(on12Luid.HighPart),
                        on12Luid.LowPart);
                else
                    spdlog::info(
                        "VR DX12 POC: D3D9On12 interface unavailable; current device is not running through the D3D12 translation layer");

                if (!isEx)
                    spdlog::warn(
                        "VR D3D9 probe: plain IDirect3DDevice9 detected; zero-copy cross-process sharing is impossible. Exact-eye SBS/DesktopDup remains available; helper D3D9Ex bridge is the optimization path.");

                if (underlying12) underlying12->Release();
                if (deviceOn12) deviceOn12->Release();
                if (d3dEx) d3dEx->Release();
                if (d3d) d3d->Release();
                if (deviceEx) deviceEx->Release();
                if (backBuffer) backBuffer->Release();
                return 0;
            }

            spdlog::warn("VR D3D9 probe: game device did not appear within startup window");
            return 0;
        }
    }

    class DeviceProbeHook final : public Hook
    {
    public:
        std::string_view description() override { return "OpenXRVRDeviceProbe"; }
        bool validate() override { return true; }
        bool apply() override
        {
            HANDLE thread = CreateThread(nullptr, 0, ProbeThread, nullptr, 0, nullptr);
            if (!thread)
            {
                spdlog::warn("VR D3D9 probe: failed to start capability thread: {}", GetLastError());
                return false;
            }
            CloseHandle(thread);
            return true;
        }

        static DeviceProbeHook instance;
    };

    DeviceProbeHook DeviceProbeHook::instance;
}
