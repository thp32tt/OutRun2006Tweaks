#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <cwchar>
#include <filesystem>
#include <new>
#include <mutex>
#include <utility>
#include <vector>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "../d3d12/d3d9on12_compat.hpp"
#include "../d3d12/d3d12_game_bridge.hpp"

namespace Settings
{
    extern Setting<bool> VREnabled;
}

namespace OutRunVRD3D9ExUpgrade
{
    namespace
    {
        using Direct3DCreate9Fn = IDirect3D9* (WINAPI*)(UINT);

        constexpr std::size_t TestCooperativeLevelVtableIndex = 3;
        constexpr std::size_t EvictManagedResourcesVtableIndex = 5;
        constexpr std::size_t ResetVtableIndex = 16;
        constexpr std::size_t CreateTextureVtableIndex = 23;
        constexpr std::size_t CreateVolumeTextureVtableIndex = 24;
        constexpr std::size_t CreateCubeTextureVtableIndex = 25;
        constexpr std::size_t CreateVertexBufferVtableIndex = 26;
        constexpr std::size_t CreateIndexBufferVtableIndex = 27;

        Direct3DCreate9Fn OriginalDirect3DCreate9 = nullptr;
        std::atomic<bool> FirstUpgradeLogged{false};
        std::atomic<bool> FirstOn12Logged{false};
        std::atomic<bool> FirstOn12FailureLogged{false};
        std::atomic<bool> FirstDeviceFailureLogged{false};
        std::atomic<bool> ThirdPartyLogged{false};
        std::atomic<bool> FirstCreateFlagsLogged{false};
        std::atomic<bool> FirstPureDeviceFallbackLogged{false};
        std::atomic<bool> FirstOverlayUnavailableLogged{false};
        std::atomic<bool> FinalCompatOverlayReady{false};
        std::atomic<IDirect3DDevice9*> CompatDevice{nullptr};

        SafetyHookInline TestCooperativeLevelCompatHook{};
        SafetyHookInline EvictManagedResourcesCompatHook{};
        SafetyHookInline ResetCompatHook{};
        SafetyHookInline CreateTextureCompatHook{};
        SafetyHookInline CreateVolumeTextureCompatHook{};
        SafetyHookInline CreateCubeTextureCompatHook{};
        SafetyHookInline CreateVertexBufferCompatHook{};
        SafetyHookInline CreateIndexBufferCompatHook{};

        std::atomic<std::uint64_t> ManagedTextureCreates{0};
        std::atomic<std::uint64_t> ManagedVolumeTextureCreates{0};
        std::atomic<std::uint64_t> ManagedCubeTextureCreates{0};
        std::atomic<std::uint64_t> ManagedVertexBufferCreates{0};
        std::atomic<std::uint64_t> ManagedIndexBufferCreates{0};
        std::atomic<std::uint64_t> ManagedCreateFailures{0};
        std::atomic<std::uint64_t> ManagedTextureDynamicFallbacks{0};
        std::atomic<std::uint64_t> ResetExRedirects{0};
        std::atomic<std::uint64_t> CooperativeLevelTranslations{0};
        std::atomic<std::uint64_t> ClassicResetStateRestores{0};
        std::atomic<std::uint64_t> ClassicResetStateRestoreFailures{0};
        std::atomic<bool> CompatWindowed{true};
        std::atomic<HWND> CompatFocusWindow{nullptr};
        std::atomic<bool> FirstCooperativeTranslationLogged{false};
        std::atomic<bool> FirstResetStateRestoreFailureLogged{false};

        struct CompatStateValue
        {
            DWORD state = 0;
            DWORD value = 0;
        };
        struct CompatStageStateValue
        {
            DWORD stage = 0;
            DWORD state = 0;
            DWORD value = 0;
        };
        struct CompatClassicBaseline
        {
            std::vector<CompatStateValue> render;
            std::vector<CompatStageStateValue> textureStage;
            std::vector<CompatStageStateValue> sampler;
            bool ready = false;
        };
        CompatClassicBaseline ClassicBaseline{};
        std::mutex ClassicBaselineMutex;

        bool CaptureClassicBaseline(IDirect3DDevice9* device) noexcept
        {
            if (!device) return false;
            try
            {
                CompatClassicBaseline next{};
                next.render.reserve(192);
                for (DWORD state = 1; state <= 255; ++state)
                {
                    DWORD value = 0;
                    if (SUCCEEDED(device->GetRenderState(
                            static_cast<D3DRENDERSTATETYPE>(state), &value)))
                        next.render.push_back({ state, value });
                }
                for (DWORD stage = 0; stage < 8; ++stage)
                {
                    for (DWORD state = 1; state <= 32; ++state)
                    {
                        DWORD value = 0;
                        if (SUCCEEDED(device->GetTextureStageState(stage,
                                static_cast<D3DTEXTURESTAGESTATETYPE>(state),
                                &value)))
                            next.textureStage.push_back({ stage, state, value });
                    }
                }
                for (DWORD sampler = 0; sampler < 16; ++sampler)
                {
                    for (DWORD state = 1; state <= 16; ++state)
                    {
                        DWORD value = 0;
                        if (SUCCEEDED(device->GetSamplerState(sampler,
                                static_cast<D3DSAMPLERSTATETYPE>(state), &value)))
                            next.sampler.push_back({ sampler, state, value });
                    }
                }
                next.ready = !next.render.empty();
                std::lock_guard<std::mutex> lock(ClassicBaselineMutex);
                ClassicBaseline = std::move(next);
                return ClassicBaseline.ready;
            }
            catch (...)
            {
                return false;
            }
        }

        void ClearClassicBaseline() noexcept
        {
            std::lock_guard<std::mutex> lock(ClassicBaselineMutex);
            ClassicBaseline = {};
        }

        void UpdateCompatPresentationState(IDirect3DDevice9* device,
            const D3DPRESENT_PARAMETERS* params) noexcept
        {
            if (!device || !params) return;
            CompatWindowed.store(params->Windowed != FALSE,
                std::memory_order_release);
            HWND window = params->hDeviceWindow;
            if (!window)
            {
                D3DDEVICE_CREATION_PARAMETERS creation{};
                if (SUCCEEDED(device->GetCreationParameters(&creation)))
                    window = creation.hFocusWindow;
            }
            CompatFocusWindow.store(window, std::memory_order_release);
        }

        bool RestoreClassicResetState(IDirect3DDevice9* device) noexcept
        {
            if (!device) return false;
            std::uint32_t failures = 0;
            {
                std::lock_guard<std::mutex> lock(ClassicBaselineMutex);
                if (!ClassicBaseline.ready) return false;
                for (const auto& item : ClassicBaseline.render)
                    if (FAILED(device->SetRenderState(
                            static_cast<D3DRENDERSTATETYPE>(item.state),
                            item.value)))
                        ++failures;
                for (const auto& item : ClassicBaseline.textureStage)
                    if (FAILED(device->SetTextureStageState(item.stage,
                            static_cast<D3DTEXTURESTAGESTATETYPE>(item.state),
                            item.value)))
                        ++failures;
                for (const auto& item : ClassicBaseline.sampler)
                    if (FAILED(device->SetSamplerState(item.stage,
                            static_cast<D3DSAMPLERSTATETYPE>(item.state),
                            item.value)))
                        ++failures;
            }

            D3DCAPS9 caps{};
            const UINT streams = SUCCEEDED(device->GetDeviceCaps(&caps))
                ? std::min<UINT>(caps.MaxStreams, 16u) : 16u;
            // Classic D3D9 exposes eight fixed-function texture stages.
            // Do not count VS sampler aliases (16..19) or invalid pixel stages
            // as Reset replay failures.
            for (DWORD stage = 0; stage < 8; ++stage)
                if (FAILED(device->SetTexture(stage, nullptr))) ++failures;
            for (UINT stream = 0; stream < streams; ++stream)
            {
                if (FAILED(device->SetStreamSource(stream, nullptr, 0, 0)))
                    ++failures;
                if (FAILED(device->SetStreamSourceFreq(stream, 1)))
                    ++failures;
            }
            if (FAILED(device->SetIndices(nullptr))) ++failures;
            if (FAILED(device->SetVertexShader(nullptr))) ++failures;
            if (FAILED(device->SetPixelShader(nullptr))) ++failures;
            // A null declaration restores the fixed-function/default declaration
            // boundary expected after classic Reset. Some drivers reject it when
            // no declaration path exists, so treat that call as best-effort.
            device->SetVertexDeclaration(nullptr);

            IDirect3DSurface9* backBuffer = nullptr;
            D3DSURFACE_DESC desc{};
            if (SUCCEEDED(device->GetBackBuffer(0, 0,
                    D3DBACKBUFFER_TYPE_MONO, &backBuffer)) && backBuffer)
            {
                if (SUCCEEDED(backBuffer->GetDesc(&desc)) &&
                    desc.Width && desc.Height)
                {
                    D3DVIEWPORT9 viewport{};
                    viewport.Width = desc.Width;
                    viewport.Height = desc.Height;
                    viewport.MinZ = 0.0f;
                    viewport.MaxZ = 1.0f;
                    if (FAILED(device->SetViewport(&viewport))) ++failures;
                    RECT scissor{ 0, 0, static_cast<LONG>(desc.Width),
                        static_cast<LONG>(desc.Height) };
                    if (FAILED(device->SetScissorRect(&scissor))) ++failures;
                }
                backBuffer->Release();
            }

            if (failures == 0)
            {
                ++ClassicResetStateRestores;
                return true;
            }
            ++ClassicResetStateRestoreFailures;
            if (!FirstResetStateRestoreFailureLogged.exchange(true))
            {
                spdlog::warn(
                    "VR D3D9Ex compat: classic Reset state replay completed with {} rejected state writes; game/VR caches still re-prime from live state",
                    failures);
            }
            return false;
        }

        bool IsCompatDevice(IDirect3DDevice9* device) noexcept
        {
            return device && CompatDevice.load(std::memory_order_acquire) == device;
        }

        bool IsSystemModuleForAddress(const void* address, HMODULE& module) noexcept
        {
            module = nullptr;
            if (!address || !GetModuleHandleExW(
                    GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                    reinterpret_cast<LPCWSTR>(address), &module) || !module)
                return false;

            wchar_t modulePath[MAX_PATH]{};
            wchar_t systemDir[MAX_PATH]{};
            const DWORD moduleLength = GetModuleFileNameW(module, modulePath, MAX_PATH);
            const UINT systemLength = GetSystemDirectoryW(systemDir, MAX_PATH);
            if (!moduleLength || moduleLength >= MAX_PATH || !systemLength || systemLength >= MAX_PATH)
                return false;

            const std::size_t dirLength = std::wcslen(systemDir);
            if (_wcsnicmp(modulePath, systemDir, dirLength) != 0)
                return false;
            const wchar_t separator = modulePath[dirLength];
            return separator == L'\\' || separator == L'/';
        }

        D3DDISPLAYMODEEX* BuildFullscreenMode(
            IDirect3DDevice9Ex* deviceEx,
            D3DPRESENT_PARAMETERS* params,
            D3DDISPLAYMODEEX& fullscreen) noexcept
        {
            if (!params || params->Windowed)
                return nullptr;

            fullscreen = {};
            fullscreen.Size = sizeof(fullscreen);
            fullscreen.Width = params->BackBufferWidth;
            fullscreen.Height = params->BackBufferHeight;
            fullscreen.RefreshRate = params->FullScreen_RefreshRateInHz;
            fullscreen.Format = params->BackBufferFormat;
            fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_UNKNOWN;

            if (deviceEx)
            {
                D3DDEVICE_CREATION_PARAMETERS creation{};
                D3DDISPLAYROTATION rotation = D3DDISPLAYROTATION_IDENTITY;
                D3DDISPLAYMODEEX current{};
                current.Size = sizeof(current);
                if (SUCCEEDED(deviceEx->GetCreationParameters(&creation)) &&
                    SUCCEEDED(deviceEx->GetDisplayModeEx(0, &current, &rotation)))
                {
                    if (!fullscreen.Width) fullscreen.Width = current.Width;
                    if (!fullscreen.Height) fullscreen.Height = current.Height;
                    if (fullscreen.Format == D3DFMT_UNKNOWN) fullscreen.Format = current.Format;
                    if (!fullscreen.RefreshRate) fullscreen.RefreshRate = current.RefreshRate;
                    fullscreen.ScanLineOrdering = current.ScanLineOrdering;
                }
            }
            if (fullscreen.ScanLineOrdering == D3DSCANLINEORDERING_UNKNOWN)
                fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;
            return &fullscreen;
        }

        HRESULT __stdcall TestCooperativeLevelCompatDest(
            IDirect3DDevice9* device)
        {
            if (!IsCompatDevice(device))
                return TestCooperativeLevelCompatHook.stdcall<HRESULT>(device);

            IDirect3DDevice9Ex* deviceEx = nullptr;
            if (FAILED(device->QueryInterface(__uuidof(IDirect3DDevice9Ex),
                    reinterpret_cast<void**>(&deviceEx))) || !deviceEx)
                return TestCooperativeLevelCompatHook.stdcall<HRESULT>(device);

            HWND window = CompatFocusWindow.load(std::memory_order_acquire);
            if (!window) window = GetDesktopWindow();
            const HRESULT state = deviceEx->CheckDeviceState(window);
            deviceEx->Release();
            ++CooperativeLevelTranslations;

            HRESULT translated = D3D_OK;
            if (state == S_PRESENT_MODE_CHANGED)
                translated = D3DERR_DEVICENOTRESET;
            else if (state == S_PRESENT_OCCLUDED)
                translated = CompatWindowed.load(std::memory_order_acquire)
                    ? D3D_OK : D3DERR_DEVICELOST;
            else if (state == D3DERR_DEVICELOST)
                translated = D3DERR_DEVICELOST;
            else if (state == D3DERR_DEVICEHUNG ||
                state == D3DERR_DEVICEREMOVED)
                translated = D3DERR_DRIVERINTERNALERROR;
            else if (FAILED(state))
                translated = D3DERR_DRIVERINTERNALERROR;

            if (!FirstCooperativeTranslationLogged.exchange(true))
                spdlog::info(
                    "VR D3D9Ex compat: TestCooperativeLevel is translated from CheckDeviceState for legacy lost-device recovery");
            return translated;
        }

        HRESULT __stdcall EvictManagedResourcesCompatDest(
            IDirect3DDevice9* device)
        {
            if (IsCompatDevice(device))
                return D3D_OK;
            return EvictManagedResourcesCompatHook.stdcall<HRESULT>(device);
        }

        HRESULT __stdcall ResetCompatDest(IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params)
        {
            if (!IsCompatDevice(device) || !params)
                return ResetCompatHook.stdcall<HRESULT>(device, params);

            IDirect3DDevice9Ex* deviceEx = nullptr;
            const HRESULT qi = device->QueryInterface(__uuidof(IDirect3DDevice9Ex), reinterpret_cast<void**>(&deviceEx));
            if (FAILED(qi) || !deviceEx)
                return ResetCompatHook.stdcall<HRESULT>(device, params);

            D3DDISPLAYMODEEX fullscreen{};
            D3DDISPLAYMODEEX* fullscreenPtr = BuildFullscreenMode(deviceEx, params, fullscreen);
            const HRESULT hr = deviceEx->ResetEx(params, fullscreenPtr);
            deviceEx->Release();
            if (SUCCEEDED(hr))
            {
                UpdateCompatPresentationState(device, params);
                RestoreClassicResetState(device);
            }
            ++ResetExRedirects;
            spdlog::info(
                "VR D3D9Ex compat: IDirect3DDevice9::Reset redirected to ResetEx hr=0x{:08X}; emulated MANAGED resources remain persistent",
                static_cast<unsigned>(hr));
            return hr;
        }

        HRESULT __stdcall CreateVertexBufferCompatDest(
            IDirect3DDevice9* device, UINT length, DWORD usage, DWORD fvf, D3DPOOL pool,
            IDirect3DVertexBuffer9** buffer, HANDLE* sharedHandle)
        {
            if (!IsCompatDevice(device) || pool != D3DPOOL_MANAGED)
                return CreateVertexBufferCompatHook.stdcall<HRESULT>(
                    device, length, usage, fvf, pool, buffer, sharedHandle);

            const HRESULT hr = CreateVertexBufferCompatHook.stdcall<HRESULT>(
                device, length, usage, fvf, D3DPOOL_DEFAULT, buffer, sharedHandle);
            ++ManagedVertexBufferCreates;
            if (FAILED(hr)) ++ManagedCreateFailures;
            if (ManagedVertexBufferCreates.load() == 1)
            {
                spdlog::info(
                    "VR D3D9Ex compat: MANAGED vertex buffer translated to DEFAULT (length={} usage=0x{:08X} hr=0x{:08X})",
                    length, static_cast<unsigned>(usage), static_cast<unsigned>(hr));
            }
            return hr;
        }

        HRESULT __stdcall CreateIndexBufferCompatDest(
            IDirect3DDevice9* device, UINT length, DWORD usage, D3DFORMAT format, D3DPOOL pool,
            IDirect3DIndexBuffer9** buffer, HANDLE* sharedHandle)
        {
            if (!IsCompatDevice(device) || pool != D3DPOOL_MANAGED)
                return CreateIndexBufferCompatHook.stdcall<HRESULT>(
                    device, length, usage, format, pool, buffer, sharedHandle);

            const HRESULT hr = CreateIndexBufferCompatHook.stdcall<HRESULT>(
                device, length, usage, format, D3DPOOL_DEFAULT, buffer, sharedHandle);
            ++ManagedIndexBufferCreates;
            if (FAILED(hr)) ++ManagedCreateFailures;
            if (ManagedIndexBufferCreates.load() == 1)
            {
                spdlog::info(
                    "VR D3D9Ex compat: MANAGED index buffer translated to DEFAULT (length={} usage=0x{:08X} fmt={} hr=0x{:08X})",
                    length, static_cast<unsigned>(usage), static_cast<int>(format), static_cast<unsigned>(hr));
            }
            return hr;
        }

        template <typename CreateFn>
        HRESULT CreateManagedTextureCompat(
            const char* label,
            std::atomic<std::uint64_t>& counter,
            DWORD usage,
            bool allowNonDynamicFallback,
            CreateFn&& create)
        {
            const DWORD dynamicUsage = usage | D3DUSAGE_DYNAMIC;
            HRESULT hr = create(dynamicUsage, D3DPOOL_DEFAULT);
            ++counter;
            if (SUCCEEDED(hr))
            {
                if (counter.load() == 1)
                {
                    spdlog::info(
                        "VR D3D9Ex compat: MANAGED {} translated to lockable DEFAULT|DYNAMIC (usage 0x{:08X}->0x{:08X})",
                        label, static_cast<unsigned>(usage), static_cast<unsigned>(dynamicUsage));
                }
                return hr;
            }

            // R14 provides an independent CPU shadow for 2D textures, so those
            // resources can safely fall back to non-dynamic DEFAULT. Cube/volume
            // textures do not yet have that shadow contract: fail creation rather
            // than return an object whose later Lock* semantics silently differ
            // from legacy MANAGED.
            if (!allowNonDynamicFallback)
            {
                ++ManagedCreateFailures;
                spdlog::warn(
                    "VR D3D9Ex compat: MANAGED {} requires a non-dynamic fallback that cannot preserve Lock semantics; failing closed hr=0x{:08X}",
                    label, static_cast<unsigned>(hr));
                return hr;
            }
            ++ManagedTextureDynamicFallbacks;
            hr = create(usage, D3DPOOL_DEFAULT);
            if (FAILED(hr)) ++ManagedCreateFailures;
            spdlog::warn(
                "VR D3D9Ex compat: {} DYNAMIC retry path used; final hr=0x{:08X} usage=0x{:08X}. A later Lock* on a non-dynamic DEFAULT texture may require shadow emulation.",
                label, static_cast<unsigned>(hr), static_cast<unsigned>(usage));
            return hr;
        }

        HRESULT __stdcall CreateTextureCompatDest(
            IDirect3DDevice9* device, UINT width, UINT height, UINT levels, DWORD usage,
            D3DFORMAT format, D3DPOOL pool, IDirect3DTexture9** texture, HANDLE* sharedHandle)
        {
            if (!IsCompatDevice(device) || pool != D3DPOOL_MANAGED)
                return CreateTextureCompatHook.stdcall<HRESULT>(
                    device, width, height, levels, usage, format, pool, texture, sharedHandle);

            return CreateManagedTextureCompat("texture", ManagedTextureCreates, usage, true,
                [&](DWORD translatedUsage, D3DPOOL translatedPool)
                {
                    return CreateTextureCompatHook.stdcall<HRESULT>(
                        device, width, height, levels, translatedUsage, format,
                        translatedPool, texture, sharedHandle);
                });
        }

        HRESULT __stdcall CreateVolumeTextureCompatDest(
            IDirect3DDevice9* device, UINT width, UINT height, UINT depth, UINT levels, DWORD usage,
            D3DFORMAT format, D3DPOOL pool, IDirect3DVolumeTexture9** texture, HANDLE* sharedHandle)
        {
            if (!IsCompatDevice(device) || pool != D3DPOOL_MANAGED)
                return CreateVolumeTextureCompatHook.stdcall<HRESULT>(
                    device, width, height, depth, levels, usage, format, pool, texture, sharedHandle);

            return CreateManagedTextureCompat("volume texture", ManagedVolumeTextureCreates, usage, false,
                [&](DWORD translatedUsage, D3DPOOL translatedPool)
                {
                    return CreateVolumeTextureCompatHook.stdcall<HRESULT>(
                        device, width, height, depth, levels, translatedUsage, format,
                        translatedPool, texture, sharedHandle);
                });
        }

        HRESULT __stdcall CreateCubeTextureCompatDest(
            IDirect3DDevice9* device, UINT edgeLength, UINT levels, DWORD usage,
            D3DFORMAT format, D3DPOOL pool, IDirect3DCubeTexture9** texture, HANDLE* sharedHandle)
        {
            if (!IsCompatDevice(device) || pool != D3DPOOL_MANAGED)
                return CreateCubeTextureCompatHook.stdcall<HRESULT>(
                    device, edgeLength, levels, usage, format, pool, texture, sharedHandle);

            return CreateManagedTextureCompat("cube texture", ManagedCubeTextureCreates, usage, false,
                [&](DWORD translatedUsage, D3DPOOL translatedPool)
                {
                    return CreateCubeTextureCompatHook.stdcall<HRESULT>(
                        device, edgeLength, levels, translatedUsage, format,
                        translatedPool, texture, sharedHandle);
                });
        }

        void ClearCompatHooks() noexcept
        {
            CompatDevice.store(nullptr, std::memory_order_release);
            CompatFocusWindow.store(nullptr, std::memory_order_release);
            TestCooperativeLevelCompatHook = {};
            EvictManagedResourcesCompatHook = {};
            ResetCompatHook = {};
            CreateTextureCompatHook = {};
            CreateVolumeTextureCompatHook = {};
            CreateCubeTextureCompatHook = {};
            CreateVertexBufferCompatHook = {};
            CreateIndexBufferCompatHook = {};
            ClearClassicBaseline();
        }

        bool InstallManagedResourceCompat(IDirect3DDevice9* baseDevice)
        {
            if (!baseDevice)
                return false;
            IDirect3DDevice9* const existing =
                CompatDevice.load(std::memory_order_acquire);
            if (existing && existing != baseDevice)
            {
                spdlog::warn(
                    "VR D3D9Ex compat: a second promoted game device was requested; keeping the first compatibility owner and forcing the new device back to classic D3D9");
                return false;
            }
            if (!CaptureClassicBaseline(baseDevice))
            {
                spdlog::error(
                    "VR D3D9Ex compat: could not capture the fresh-device classic state baseline; rejecting Ex promotion");
                return false;
            }
            void** vtable = *reinterpret_cast<void***>(baseDevice);
            if (!vtable)
                return false;

            const auto disabled = safetyhook::InlineHook::StartDisabled;
            TestCooperativeLevelCompatHook = safetyhook::create_inline(
                vtable[TestCooperativeLevelVtableIndex],
                TestCooperativeLevelCompatDest, disabled);
            EvictManagedResourcesCompatHook = safetyhook::create_inline(
                vtable[EvictManagedResourcesVtableIndex],
                EvictManagedResourcesCompatDest, disabled);
            ResetCompatHook = safetyhook::create_inline(
                vtable[ResetVtableIndex], ResetCompatDest, disabled);
            CreateTextureCompatHook = safetyhook::create_inline(vtable[CreateTextureVtableIndex], CreateTextureCompatDest, disabled);
            CreateVolumeTextureCompatHook = safetyhook::create_inline(vtable[CreateVolumeTextureVtableIndex], CreateVolumeTextureCompatDest, disabled);
            CreateCubeTextureCompatHook = safetyhook::create_inline(vtable[CreateCubeTextureVtableIndex], CreateCubeTextureCompatDest, disabled);
            CreateVertexBufferCompatHook = safetyhook::create_inline(vtable[CreateVertexBufferVtableIndex], CreateVertexBufferCompatDest, disabled);
            CreateIndexBufferCompatHook = safetyhook::create_inline(vtable[CreateIndexBufferVtableIndex], CreateIndexBufferCompatDest, disabled);

            SafetyHookInline* hooks[]{
                &TestCooperativeLevelCompatHook, &EvictManagedResourcesCompatHook,
                &ResetCompatHook, &CreateTextureCompatHook,
                &CreateVolumeTextureCompatHook, &CreateCubeTextureCompatHook,
                &CreateVertexBufferCompatHook, &CreateIndexBufferCompatHook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                {
                    spdlog::error(
                        "VR D3D9Ex compat: compatibility hook transaction was partial; rejecting Ex device");
                    ClearCompatHooks();
                    return false;
                }
            }

            CompatDevice.store(baseDevice, std::memory_order_release);
            spdlog::info(
                "VR D3D9Ex compat: legacy contract hooks installed (TestCooperativeLevel/EvictManaged/Reset/resources); fresh-device state baseline captured; MANAGED 2D -> R14 shadow, cube/volume fail closed if DYNAMIC is unavailable");
            return true;
        }

        class Direct3D9ExCompat final : public IDirect3D9
        {
        public:
            explicit Direct3D9ExCompat(IDirect3D9Ex* ex) noexcept
                : ex_(ex)
            {
            }

            HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void** object) override
            {
                if (!object) return E_POINTER;
                *object = nullptr;
                if (riid == IID_IUnknown || riid == IID_IDirect3D9)
                {
                    *object = static_cast<IDirect3D9*>(this);
                    AddRef();
                    return S_OK;
                }
                if (riid == __uuidof(IDirect3D9Ex) && ex_)
                    return ex_->QueryInterface(riid, object);
                return ex_ ? ex_->QueryInterface(riid, object) : E_NOINTERFACE;
            }

            ULONG STDMETHODCALLTYPE AddRef() override
            {
                return static_cast<ULONG>(InterlockedIncrement(&refs_));
            }

            ULONG STDMETHODCALLTYPE Release() override
            {
                const LONG refs = InterlockedDecrement(&refs_);
                if (refs == 0)
                {
                    if (ex_) ex_->Release();
                    delete this;
                    return 0;
                }
                return static_cast<ULONG>(refs);
            }

            HRESULT STDMETHODCALLTYPE RegisterSoftwareDevice(void* initializeFunction) override
            {
                return ex_->RegisterSoftwareDevice(initializeFunction);
            }
            UINT STDMETHODCALLTYPE GetAdapterCount() override { return ex_->GetAdapterCount(); }
            HRESULT STDMETHODCALLTYPE GetAdapterIdentifier(UINT a, DWORD f, D3DADAPTER_IDENTIFIER9* i) override
            { return ex_->GetAdapterIdentifier(a, f, i); }
            UINT STDMETHODCALLTYPE GetAdapterModeCount(UINT a, D3DFORMAT f) override
            { return ex_->GetAdapterModeCount(a, f); }
            HRESULT STDMETHODCALLTYPE EnumAdapterModes(UINT a, D3DFORMAT f, UINT m, D3DDISPLAYMODE* mode) override
            { return ex_->EnumAdapterModes(a, f, m, mode); }
            HRESULT STDMETHODCALLTYPE GetAdapterDisplayMode(UINT a, D3DDISPLAYMODE* mode) override
            { return ex_->GetAdapterDisplayMode(a, mode); }
            HRESULT STDMETHODCALLTYPE CheckDeviceType(UINT a, D3DDEVTYPE t, D3DFORMAT af, D3DFORMAT bf, BOOL w) override
            { return ex_->CheckDeviceType(a, t, af, bf, w); }
            HRESULT STDMETHODCALLTYPE CheckDeviceFormat(UINT a, D3DDEVTYPE t, D3DFORMAT af, DWORD u, D3DRESOURCETYPE r, D3DFORMAT cf) override
            { return ex_->CheckDeviceFormat(a, t, af, u, r, cf); }
            HRESULT STDMETHODCALLTYPE CheckDeviceMultiSampleType(UINT a, D3DDEVTYPE t, D3DFORMAT sf, BOOL w,
                D3DMULTISAMPLE_TYPE mt, DWORD* q) override
            { return ex_->CheckDeviceMultiSampleType(a, t, sf, w, mt, q); }
            HRESULT STDMETHODCALLTYPE CheckDepthStencilMatch(UINT a, D3DDEVTYPE t, D3DFORMAT af,
                D3DFORMAT rf, D3DFORMAT df) override
            { return ex_->CheckDepthStencilMatch(a, t, af, rf, df); }
            HRESULT STDMETHODCALLTYPE CheckDeviceFormatConversion(UINT a, D3DDEVTYPE t, D3DFORMAT s, D3DFORMAT d) override
            { return ex_->CheckDeviceFormatConversion(a, t, s, d); }
            HRESULT STDMETHODCALLTYPE GetDeviceCaps(UINT a, D3DDEVTYPE t, D3DCAPS9* caps) override
            { return ex_->GetDeviceCaps(a, t, caps); }
            HMONITOR STDMETHODCALLTYPE GetAdapterMonitor(UINT a) override
            { return ex_->GetAdapterMonitor(a); }

            HRESULT STDMETHODCALLTYPE CreateDevice(UINT adapter, D3DDEVTYPE type, HWND focusWindow,
                DWORD behaviorFlags, D3DPRESENT_PARAMETERS* params, IDirect3DDevice9** device) override
            {
                if (!device || !params)
                    return D3DERR_INVALIDCALL;
                *device = nullptr;

                spdlog::info(
                    "VR DX12 STRICT: CreateDevice request adapter={} type={} flags=0x{:08X} windowed={} backbuffer={}x{} fmt={} count={} swap={} interval={} autoDepth={} depthFmt={}",
                    adapter,
                    static_cast<unsigned>(type),
                    static_cast<unsigned>(behaviorFlags),
                    params->Windowed ? 1 : 0,
                    params->BackBufferWidth,
                    params->BackBufferHeight,
                    static_cast<int>(params->BackBufferFormat),
                    params->BackBufferCount,
                    static_cast<int>(params->SwapEffect),
                    params->PresentationInterval,
                    params->EnableAutoDepthStencil ? 1 : 0,
                    static_cast<int>(params->AutoDepthStencilFormat));

                if (!FinalCompatOverlayReady.load(std::memory_order_acquire))
                {
                    spdlog::error(
                        "VR DX12 STRICT FAIL stage=CreateDevice reason=compat-overlay-not-ready hr=0x{:08X}; no D3D9Ex/classic fallback will be attempted",
                        static_cast<unsigned>(D3DERR_NOTAVAILABLE));
                    return D3DERR_NOTAVAILABLE;
                }

                if ((behaviorFlags & D3DCREATE_PUREDEVICE) != 0)
                {
                    spdlog::error(
                        "VR DX12 STRICT FAIL stage=CreateDevice reason=pure-device-request flags=0x{:08X} hr=0x{:08X}; request is left unmodified for diagnosis",
                        static_cast<unsigned>(behaviorFlags),
                        static_cast<unsigned>(D3DERR_NOTAVAILABLE));
                    return D3DERR_NOTAVAILABLE;
                }

                D3DDISPLAYMODEEX fullscreen{};
                D3DDISPLAYMODEEX* fullscreenPtr = nullptr;
                if (!params->Windowed)
                {
                    fullscreen.Size = sizeof(fullscreen);
                    fullscreen.Width = params->BackBufferWidth;
                    fullscreen.Height = params->BackBufferHeight;
                    fullscreen.RefreshRate = params->FullScreen_RefreshRateInHz;
                    fullscreen.Format = params->BackBufferFormat;
                    fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_UNKNOWN;
                    if (ex_)
                    {
                        D3DDISPLAYROTATION rotation = D3DDISPLAYROTATION_IDENTITY;
                        D3DDISPLAYMODEEX current{};
                        current.Size = sizeof(current);
                        const HRESULT modeHr =
                            ex_->GetAdapterDisplayModeEx(adapter, &current, &rotation);
                        spdlog::info(
                            "VR DX12 STRICT: GetAdapterDisplayModeEx hr=0x{:08X} current={}x{} fmt={} refresh={} scan={}",
                            static_cast<unsigned>(modeHr),
                            current.Width,
                            current.Height,
                            static_cast<int>(current.Format),
                            current.RefreshRate,
                            static_cast<int>(current.ScanLineOrdering));
                        if (SUCCEEDED(modeHr))
                        {
                            if (!fullscreen.Width) fullscreen.Width = current.Width;
                            if (!fullscreen.Height) fullscreen.Height = current.Height;
                            if (fullscreen.Format == D3DFMT_UNKNOWN) fullscreen.Format = current.Format;
                            if (!fullscreen.RefreshRate) fullscreen.RefreshRate = current.RefreshRate;
                            fullscreen.ScanLineOrdering = current.ScanLineOrdering;
                        }
                    }
                    if (fullscreen.ScanLineOrdering == D3DSCANLINEORDERING_UNKNOWN)
                        fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;
                    fullscreenPtr = &fullscreen;
                }

                const D3DPRESENT_PARAMETERS originalParams = *params;
                D3DPRESENT_PARAMETERS attemptedParams = originalParams;
                IDirect3DDevice9* baseDevice = nullptr;
                HRESULT hr = ex_ ? ex_->CreateDevice(
                    adapter, type, focusWindow, behaviorFlags,
                    &attemptedParams, &baseDevice) : E_POINTER;

                spdlog::info(
                    "VR DX12 STRICT: D3D9On12 base CreateDevice returned hr=0x{:08X} device={:p} count={} interval={} window={:p}",
                    static_cast<unsigned>(hr), fmt::ptr(baseDevice),
                    attemptedParams.BackBufferCount,
                    attemptedParams.PresentationInterval,
                    fmt::ptr(attemptedParams.hDeviceWindow));

                // D3D9On12 must preserve the legacy CreateDevice contract. If
                // the runtime rejects OutRun's double-buffer/window parameters,
                // retry once with the smallest compatibility normalization while
                // staying on the same D3D9On12 provider (never native D3D9).
                if (FAILED(hr) || !baseDevice)
                {
                    if (baseDevice)
                    {
                        baseDevice->Release();
                        baseDevice = nullptr;
                    }
                    D3DPRESENT_PARAMETERS safe = originalParams;
                    if (safe.Windowed)
                    {
                        safe.FullScreen_RefreshRateInHz = 0;
                        if (!safe.hDeviceWindow)
                            safe.hDeviceWindow = focusWindow;
                    }
                    if (safe.BackBufferCount > 1)
                        safe.BackBufferCount = 1;
                    safe.PresentationInterval = D3DPRESENT_INTERVAL_DEFAULT;

                    spdlog::warn(
                        "VR DX12 STRICT: retrying D3D9On12 CreateDevice with compatibility presentation count={} interval={} window={:p}",
                        safe.BackBufferCount,
                        safe.PresentationInterval,
                        fmt::ptr(safe.hDeviceWindow));

                    hr = ex_ ? ex_->CreateDevice(
                        adapter, type, focusWindow, behaviorFlags,
                        &safe, &baseDevice) : E_POINTER;
                    attemptedParams = safe;
                    spdlog::info(
                        "VR DX12 STRICT: compatibility CreateDevice returned hr=0x{:08X} device={:p}",
                        static_cast<unsigned>(hr), fmt::ptr(baseDevice));
                }

                if (FAILED(hr) || !baseDevice)
                {
                    if (!FirstDeviceFailureLogged.exchange(true))
                        spdlog::error(
                            "VR DX12 STRICT FAIL stage=CreateDeviceOn12 hr=0x{:08X} adapter={} type={} flags=0x{:08X}; native D3D9 fallback remains disabled",
                            static_cast<unsigned>(hr), adapter,
                            static_cast<unsigned>(type),
                            static_cast<unsigned>(behaviorFlags));
                    if (baseDevice) baseDevice->Release();
                    return FAILED(hr) ? hr : E_FAIL;
                }

                IDirect3DDevice9On12* on12 = nullptr;
                const HRESULT on12Qi = baseDevice->QueryInterface(
                    __uuidof(IDirect3DDevice9On12),
                    reinterpret_cast<void**>(&on12));
                if (FAILED(on12Qi) || !on12)
                {
                    spdlog::error(
                        "VR DX12 STRICT FAIL stage=VerifyOn12 reason=IDirect3DDevice9On12-QI hr=0x{:08X}; refusing non-D3D9On12 device",
                        static_cast<unsigned>(on12Qi));
                    if (on12) on12->Release();
                    baseDevice->Release();
                    return FAILED(on12Qi) ? on12Qi : E_NOINTERFACE;
                }

                ID3D12Device* underlying12 = nullptr;
                const HRESULT d12Hr = on12->GetD3D12Device(
                    __uuidof(ID3D12Device),
                    reinterpret_cast<void**>(&underlying12));
                if (FAILED(d12Hr) || !underlying12)
                {
                    spdlog::error(
                        "VR DX12 STRICT FAIL stage=VerifyOn12 reason=GetD3D12Device hr=0x{:08X}; refusing device without an underlying D3D12 device",
                        static_cast<unsigned>(d12Hr));
                    if (underlying12) underlying12->Release();
                    on12->Release();
                    baseDevice->Release();
                    return FAILED(d12Hr) ? d12Hr : E_NOINTERFACE;
                }

                const LUID luid = underlying12->GetAdapterLuid();
                spdlog::info(
                    "VR DX12 STRICT: verified IDirect3DDevice9On12 + ID3D12Device adapterLuid={:08X}:{:08X} nodeCount={}",
                    static_cast<std::uint32_t>(luid.HighPart),
                    luid.LowPart,
                    underlying12->GetNodeCount());

                underlying12->Release();
                on12->Release();

                if (!InstallManagedResourceCompat(baseDevice))
                {
                    spdlog::error(
                        "VR DX12 STRICT FAIL stage=CompatInstall reason=managed-resource-compat-install-failed; native D3D9 fallback remains disabled");
                    baseDevice->Release();
                    return E_FAIL;
                }

                // CreateDevice is in/out. Publish the actual presentation values
                // accepted by D3D9On12 so the game's Reset path sees the same
                // swap-chain contract that was really created.
                *params = attemptedParams;
                *device = baseDevice;
                UpdateCompatPresentationState(*device, params);
                if (!OutRunVRD3D12Bridge::Attach(*device))
                {
                    spdlog::warn(
                        "VR DX12 STRICT: core D3D9On12 device is valid but native D3D12 VR transport bridge initialization failed; 2D rendering remains usable and bridge diagnostics will stay disabled");
                }
                if (!FirstUpgradeLogged.exchange(true))
                {
                    spdlog::info(
                        "VR DX12 STRICT PASS: OutRun game device is D3D9On12-backed D3D12 through legacy CreateDevice semantics; no native D3D9 fallback path exists");
                }
                return hr;
            }

        private:
            volatile LONG refs_ = 1;
            IDirect3D9Ex* ex_ = nullptr;
        };

        IDirect3D9* WINAPI HookedDirect3DCreate9(UINT sdkVersion)
        {
            if (!OriginalDirect3DCreate9)
            {
                spdlog::error(
                    "VR DX12 STRICT FAIL stage=Direct3DCreate9 reason=original-import-null");
                return nullptr;
            }

            HMODULE provider = nullptr;
            if (!IsSystemModuleForAddress(
                    reinterpret_cast<const void*>(OriginalDirect3DCreate9),
                    provider))
            {
                HMODULE discovered = nullptr;
                GetModuleHandleExW(
                    GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                    reinterpret_cast<LPCWSTR>(OriginalDirect3DCreate9),
                    &discovered);
                wchar_t modulePath[MAX_PATH]{};
                if (discovered)
                    GetModuleFileNameW(discovered, modulePath, MAX_PATH);
                spdlog::error(
                    "VR DX12 STRICT FAIL stage=Provider reason=non-system-d3d9 provider={} sdkVersion={}; third-party/native fallback is disabled",
                    modulePath[0] ? std::filesystem::path(modulePath).string() : std::string("<unknown>"),
                    sdkVersion);
                return nullptr;
            }

            wchar_t providerPath[MAX_PATH]{};
            GetModuleFileNameW(provider, providerPath, MAX_PATH);
            spdlog::info(
                "VR DX12 STRICT: Direct3DCreate9 intercepted sdkVersion={} provider={}",
                sdkVersion,
                providerPath[0] ? std::filesystem::path(providerPath).string() : std::string("<unknown>"));

            const auto createOn12Ex =
                reinterpret_cast<PFN_Direct3DCreate9On12Ex>(
                    GetProcAddress(provider, "Direct3DCreate9On12Ex"));
            if (!createOn12Ex)
            {
                const DWORD error = GetLastError();
                if (!FirstOn12FailureLogged.exchange(true))
                    spdlog::error(
                        "VR DX12 STRICT FAIL stage=GetProcAddress reason=Direct3DCreate9On12Ex-missing win32Error={}; no D3D9Ex/classic fallback",
                        error);
                return nullptr;
            }

            D3D9ON12_ARGS args{};
            args.Enable9On12 = TRUE;
            args.pD3D12Device = nullptr;
            args.NumQueues = 0;
            args.NodeMask = 0;

            IDirect3D9Ex* on12 = nullptr;
            const HRESULT on12Hr = createOn12Ex(
                sdkVersion, &args, 1, &on12);
            spdlog::info(
                "VR DX12 STRICT: Direct3DCreate9On12Ex returned hr=0x{:08X} interface={:p} enable9on12={} queues={} nodeMask={}",
                static_cast<unsigned>(on12Hr),
                fmt::ptr(on12),
                args.Enable9On12 ? 1 : 0,
                args.NumQueues,
                args.NodeMask);

            if (FAILED(on12Hr) || !on12)
            {
                if (!FirstOn12FailureLogged.exchange(true))
                    spdlog::error(
                        "VR DX12 STRICT FAIL stage=Direct3DCreate9On12Ex hr=0x{:08X} interface={:p}; D3D9Ex/classic fallback REMOVED",
                        static_cast<unsigned>(on12Hr), fmt::ptr(on12));
                if (on12) on12->Release();
                return nullptr;
            }

            auto* wrapper = new (std::nothrow) Direct3D9ExCompat(on12);
            if (!wrapper)
            {
                spdlog::error(
                    "VR DX12 STRICT FAIL stage=WrapperAlloc reason=out-of-memory; releasing D3D9On12 interface");
                on12->Release();
                return nullptr;
            }

            if (!FirstOn12Logged.exchange(true))
                spdlog::info(
                    "VR DX12 STRICT PASS stage=Direct3DCreate9On12Ex; only D3D9On12 -> D3D12 is allowed on this branch");
            return wrapper;
        }

        bool PatchDirect3DCreate9Import() noexcept
        {
            auto* base = reinterpret_cast<std::uint8_t*>(Module::ExeHandle);
            if (!base) return false;
            auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
            if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0) return false;
            auto* nt = reinterpret_cast<IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
            if (nt->Signature != IMAGE_NT_SIGNATURE) return false;
            const auto& importDirectory = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
            if (!importDirectory.VirtualAddress || !importDirectory.Size) return false;

            auto* descriptor = reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(base + importDirectory.VirtualAddress);
            for (; descriptor->Name; ++descriptor)
            {
                const char* moduleName = reinterpret_cast<const char*>(base + descriptor->Name);
                if (_stricmp(moduleName, "d3d9.dll") != 0) continue;
                if (!descriptor->FirstThunk || !descriptor->OriginalFirstThunk) return false;

                auto* names = reinterpret_cast<IMAGE_THUNK_DATA*>(base + descriptor->OriginalFirstThunk);
                auto* thunks = reinterpret_cast<IMAGE_THUNK_DATA*>(base + descriptor->FirstThunk);
                for (; names->u1.AddressOfData; ++names, ++thunks)
                {
                    if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal)) continue;
                    auto* import = reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(base + names->u1.AddressOfData);
                    if (std::strcmp(reinterpret_cast<const char*>(import->Name), "Direct3DCreate9") != 0)
                        continue;

                    OriginalDirect3DCreate9 = reinterpret_cast<Direct3DCreate9Fn>(thunks->u1.Function);
                    DWORD oldProtect = 0;
                    if (!VirtualProtect(&thunks->u1.Function, sizeof(thunks->u1.Function), PAGE_READWRITE, &oldProtect))
                        return false;
                    thunks->u1.Function = reinterpret_cast<ULONG_PTR>(&HookedDirect3DCreate9);
                    FlushInstructionCache(GetCurrentProcess(), &thunks->u1.Function, sizeof(thunks->u1.Function));
                    DWORD ignored = 0;
                    VirtualProtect(&thunks->u1.Function, sizeof(thunks->u1.Function), oldProtect, &ignored);
                    return true;
                }
            }
            return false;
        }
    }

    void SetFinalCompatOverlayReady(bool ready) noexcept
    {
        FinalCompatOverlayReady.store(ready, std::memory_order_release);
    }

    class D3D9ExUpgradeHook final : public Hook
    {
    public:
        std::string_view description() override { return "OpenXRVRD3D9ExUpgrade"; }
        void declare_settings() override {}
        bool validate() override { return true; }
        bool apply() override
        {
            if (!PatchDirect3DCreate9Import())
            {
                spdlog::error("VR DX12 STRICT FAIL stage=IATPatch reason=Direct3DCreate9-import-not-found; DX12 branch cannot start");
                return false;
            }
            spdlog::info("VR DX12 STRICT: Direct3DCreate9 IAT hook armed; only D3D9On12 -> D3D12 is permitted, all D3D9Ex/classic fallbacks removed");
            return true;
        }

        static D3D9ExUpgradeHook instance;
    };

    D3D9ExUpgradeHook D3D9ExUpgradeHook::instance;
}