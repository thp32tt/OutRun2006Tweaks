#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <cstdint>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "game_addrs.hpp"
#include "vr/d3d11/startup_census.hpp"
#include "vr/d3d11/native_backend.hpp"

namespace OutRunVRDeviceProbe
{
    namespace
    {
        bool Dx11CensusEnabled() noexcept
        {
            char value[8]{};
            const DWORD length = GetEnvironmentVariableA(
                "OUTRUN_VR_DX11_CENSUS", value,
                static_cast<DWORD>(sizeof(value)));
            return length > 0 && length < sizeof(value) && value[0] == '1';
        }

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

                const auto dx11 = outrun::vr::dx11::inspect_source_device(device);
                spdlog::info(
                    "VR DX11 R71 census: observed={} size={}x{} sourceFormat={} nativeFormat={} msaa={} bootstrapCompatible={}",
                    dx11.observed ? 1 : 0,
                    dx11.width,
                    dx11.height,
                    static_cast<int>(dx11.source_format),
                    static_cast<int>(dx11.native_format),
                    static_cast<int>(dx11.multisample),
                    dx11.native_bootstrap_compatible ? 1 : 0);

                const LUID adapterLuid = dx11.adapter_luid;
                const bool luidValid = dx11.adapter_luid_valid;

                if (Dx11CensusEnabled())
                {
                    if (!dx11.native_bootstrap_compatible || !luidValid)
                    {
                        spdlog::warn(
                            "VR DX11 R72 bootstrap probe skipped: compatible={} adapterLuidValid={}",
                            dx11.native_bootstrap_compatible ? 1 : 0,
                            luidValid ? 1 : 0);
                    }
                    else
                    {
                        outrun::vr::dx11::NativeBackend probe;
                        outrun::vr::dx11::NativeBackendConfig config{};
                        config.width = dx11.width;
                        config.height = dx11.height;
                        config.color_format = dx11.native_format;
                        config.adapter_luid_valid = true;
                        config.require_adapter_luid = true;
                        config.adapter_luid = adapterLuid;

                        const bool nativeReady = probe.initialize(config);
                        const LUID selected = probe.selected_adapter_luid();
                        spdlog::info(
                            "VR DX11 R72 bootstrap probe: ready={} featureLevel=0x{:04X} selectedLuidValid={} selectedLuid={:08X}:{:08X}",
                            nativeReady ? 1 : 0,
                            static_cast<unsigned>(probe.feature_level()),
                            probe.selected_adapter_luid_valid() ? 1 : 0,
                            static_cast<std::uint32_t>(selected.HighPart),
                            selected.LowPart);
                        probe.shutdown();
                    }
                }

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

                if (!isEx)
                    spdlog::warn(
                        "VR D3D9 probe: plain IDirect3DDevice9 detected; zero-copy cross-process sharing is impossible. Exact-eye SBS/DesktopDup remains available; helper D3D9Ex bridge is the optimization path.");

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