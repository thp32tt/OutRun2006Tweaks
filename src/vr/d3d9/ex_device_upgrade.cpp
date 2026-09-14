#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <atomic>
#include <cstdint>
#include <cstring>
#include <cwchar>
#include <new>

#include <spdlog/spdlog.h>

#include "hook_mgr.hpp"
#include "plugin.hpp"

namespace Settings
{
    extern Setting<bool> VRPreferD3D9Ex;
}

namespace OutRunVRD3D9ExUpgrade
{
    namespace
    {
        using Direct3DCreate9Fn = IDirect3D9* (WINAPI*)(UINT);
        using Direct3DCreate9ExFn = HRESULT (WINAPI*)(UINT, IDirect3D9Ex**);

        constexpr std::size_t ResetVtableIndex = 16;
        constexpr std::size_t CreateTextureVtableIndex = 23;
        constexpr std::size_t CreateVolumeTextureVtableIndex = 24;
        constexpr std::size_t CreateCubeTextureVtableIndex = 25;
        constexpr std::size_t CreateVertexBufferVtableIndex = 26;
        constexpr std::size_t CreateIndexBufferVtableIndex = 27;

        Direct3DCreate9Fn OriginalDirect3DCreate9 = nullptr;
        std::atomic<bool> FirstUpgradeLogged{false};
        std::atomic<bool> FirstFallbackLogged{false};
        std::atomic<bool> ThirdPartyLogged{false};
        std::atomic<IDirect3DDevice9*> CompatDevice{nullptr};

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
            fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;

            if ((fullscreen.Width == 0 || fullscreen.Height == 0 || fullscreen.Format == D3DFMT_UNKNOWN) && deviceEx)
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
                }
            }
            return &fullscreen;
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

            // Some legacy formats reject DYNAMIC even though a DEFAULT texture is valid.
            // Retry without DYNAMIC so non-locking resources can still render. If the game
            // later requires LockRect on such a texture the failure will remain visible in
            // the game log instead of crashing at creation time.
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

            return CreateManagedTextureCompat("texture", ManagedTextureCreates, usage,
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

            return CreateManagedTextureCompat("volume texture", ManagedVolumeTextureCreates, usage,
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

            return CreateManagedTextureCompat("cube texture", ManagedCubeTextureCreates, usage,
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
            ResetCompatHook = {};
            CreateTextureCompatHook = {};
            CreateVolumeTextureCompatHook = {};
            CreateCubeTextureCompatHook = {};
            CreateVertexBufferCompatHook = {};
            CreateIndexBufferCompatHook = {};
        }

        bool InstallManagedResourceCompat(IDirect3DDevice9Ex* deviceEx)
        {
            if (!deviceEx)
                return false;

            auto* baseDevice = static_cast<IDirect3DDevice9*>(deviceEx);
            void** vtable = *reinterpret_cast<void***>(baseDevice);
            if (!vtable)
                return false;

            ResetCompatHook = safetyhook::create_inline(vtable[ResetVtableIndex], ResetCompatDest);
            CreateTextureCompatHook = safetyhook::create_inline(vtable[CreateTextureVtableIndex], CreateTextureCompatDest);
            CreateVolumeTextureCompatHook = safetyhook::create_inline(vtable[CreateVolumeTextureVtableIndex], CreateVolumeTextureCompatDest);
            CreateCubeTextureCompatHook = safetyhook::create_inline(vtable[CreateCubeTextureVtableIndex], CreateCubeTextureCompatDest);
            CreateVertexBufferCompatHook = safetyhook::create_inline(vtable[CreateVertexBufferVtableIndex], CreateVertexBufferCompatDest);
            CreateIndexBufferCompatHook = safetyhook::create_inline(vtable[CreateIndexBufferVtableIndex], CreateIndexBufferCompatDest);

            if (!ResetCompatHook || !CreateTextureCompatHook || !CreateVolumeTextureCompatHook ||
                !CreateCubeTextureCompatHook || !CreateVertexBufferCompatHook || !CreateIndexBufferCompatHook)
            {
                spdlog::error("VR D3D9Ex compat: failed to install one or more managed-resource hooks; rejecting Ex device");
                ClearCompatHooks();
                return false;
            }

            CompatDevice.store(baseDevice, std::memory_order_release);
            spdlog::info(
                "VR D3D9Ex compat: managed-resource compatibility hooks installed (Reset/CreateTexture/Volume/Cube/VB/IB); MANAGED buffers -> DEFAULT, MANAGED textures -> DEFAULT|DYNAMIC");
            return true;
        }

        class Direct3D9ExCompat final : public IDirect3D9
        {
        public:
            Direct3D9ExCompat(IDirect3D9Ex* ex, IDirect3D9* fallback) noexcept
                : ex_(ex), fallback_(fallback)
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
                return fallback_ ? fallback_->QueryInterface(riid, object) : E_NOINTERFACE;
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
                    if (fallback_) fallback_->Release();
                    if (ex_) ex_->Release();
                    delete this;
                    return 0;
                }
                return static_cast<ULONG>(refs);
            }

            HRESULT STDMETHODCALLTYPE RegisterSoftwareDevice(void* initializeFunction) override
            {
                return fallback_->RegisterSoftwareDevice(initializeFunction);
            }
            UINT STDMETHODCALLTYPE GetAdapterCount() override { return fallback_->GetAdapterCount(); }
            HRESULT STDMETHODCALLTYPE GetAdapterIdentifier(UINT a, DWORD f, D3DADAPTER_IDENTIFIER9* i) override
            { return fallback_->GetAdapterIdentifier(a, f, i); }
            UINT STDMETHODCALLTYPE GetAdapterModeCount(UINT a, D3DFORMAT f) override
            { return fallback_->GetAdapterModeCount(a, f); }
            HRESULT STDMETHODCALLTYPE EnumAdapterModes(UINT a, D3DFORMAT f, UINT m, D3DDISPLAYMODE* mode) override
            { return fallback_->EnumAdapterModes(a, f, m, mode); }
            HRESULT STDMETHODCALLTYPE GetAdapterDisplayMode(UINT a, D3DDISPLAYMODE* mode) override
            { return fallback_->GetAdapterDisplayMode(a, mode); }
            HRESULT STDMETHODCALLTYPE CheckDeviceType(UINT a, D3DDEVTYPE t, D3DFORMAT af, D3DFORMAT bf, BOOL w) override
            { return fallback_->CheckDeviceType(a, t, af, bf, w); }
            HRESULT STDMETHODCALLTYPE CheckDeviceFormat(UINT a, D3DDEVTYPE t, D3DFORMAT af, DWORD u, D3DRESOURCETYPE r, D3DFORMAT cf) override
            { return fallback_->CheckDeviceFormat(a, t, af, u, r, cf); }
            HRESULT STDMETHODCALLTYPE CheckDeviceMultiSampleType(UINT a, D3DDEVTYPE t, D3DFORMAT sf, BOOL w,
                D3DMULTISAMPLE_TYPE mt, DWORD* q) override
            { return fallback_->CheckDeviceMultiSampleType(a, t, sf, w, mt, q); }
            HRESULT STDMETHODCALLTYPE CheckDepthStencilMatch(UINT a, D3DDEVTYPE t, D3DFORMAT af,
                D3DFORMAT rf, D3DFORMAT df) override
            { return fallback_->CheckDepthStencilMatch(a, t, af, rf, df); }
            HRESULT STDMETHODCALLTYPE CheckDeviceFormatConversion(UINT a, D3DDEVTYPE t, D3DFORMAT s, D3DFORMAT d) override
            { return fallback_->CheckDeviceFormatConversion(a, t, s, d); }
            HRESULT STDMETHODCALLTYPE GetDeviceCaps(UINT a, D3DDEVTYPE t, D3DCAPS9* caps) override
            { return fallback_->GetDeviceCaps(a, t, caps); }
            HMONITOR STDMETHODCALLTYPE GetAdapterMonitor(UINT a) override
            { return fallback_->GetAdapterMonitor(a); }

            HRESULT STDMETHODCALLTYPE CreateDevice(UINT adapter, D3DDEVTYPE type, HWND focusWindow,
                DWORD behaviorFlags, D3DPRESENT_PARAMETERS* params, IDirect3DDevice9** device) override
            {
                if (!device || !params) return D3DERR_INVALIDCALL;
                *device = nullptr;

                D3DDISPLAYMODEEX fullscreen{};
                D3DDISPLAYMODEEX* fullscreenPtr = nullptr;
                if (!params->Windowed)
                {
                    fullscreen.Size = sizeof(fullscreen);
                    fullscreen.Width = params->BackBufferWidth;
                    fullscreen.Height = params->BackBufferHeight;
                    fullscreen.RefreshRate = params->FullScreen_RefreshRateInHz;
                    fullscreen.Format = params->BackBufferFormat;
                    fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;
                    if ((fullscreen.Width == 0 || fullscreen.Height == 0 || fullscreen.Format == D3DFMT_UNKNOWN) && ex_)
                    {
                        D3DDISPLAYROTATION rotation = D3DDISPLAYROTATION_IDENTITY;
                        D3DDISPLAYMODEEX current{};
                        current.Size = sizeof(current);
                        if (SUCCEEDED(ex_->GetAdapterDisplayModeEx(adapter, &current, &rotation)))
                        {
                            if (!fullscreen.Width) fullscreen.Width = current.Width;
                            if (!fullscreen.Height) fullscreen.Height = current.Height;
                            if (fullscreen.Format == D3DFMT_UNKNOWN) fullscreen.Format = current.Format;
                            if (!fullscreen.RefreshRate) fullscreen.RefreshRate = current.RefreshRate;
                        }
                    }
                    fullscreenPtr = &fullscreen;
                }

                IDirect3DDevice9Ex* deviceEx = nullptr;
                HRESULT hr = ex_ ? ex_->CreateDeviceEx(adapter, type, focusWindow, behaviorFlags,
                    params, fullscreenPtr, &deviceEx) : E_FAIL;
                if (SUCCEEDED(hr) && deviceEx)
                {
                    if (!InstallManagedResourceCompat(deviceEx))
                    {
                        deviceEx->Release();
                        deviceEx = nullptr;
                        if (!FirstFallbackLogged.exchange(true))
                        {
                            spdlog::warn(
                                "VR D3D9Ex upgrade: Ex device created but managed-resource compatibility layer could not be installed; falling back to original D3D9 device");
                        }
                        return fallback_->CreateDevice(adapter, type, focusWindow, behaviorFlags, params, device);
                    }

                    *device = static_cast<IDirect3DDevice9*>(deviceEx);
                    if (!FirstUpgradeLogged.exchange(true))
                    {
                        spdlog::info(
                            "VR D3D9Ex upgrade: game CreateDevice promoted to CreateDeviceEx with managed-resource compatibility; existing 4-slot zero-copy eye transport is eligible");
                    }
                    return hr;
                }

                if (!FirstFallbackLogged.exchange(true))
                {
                    spdlog::warn(
                        "VR D3D9Ex upgrade: CreateDeviceEx failed HRESULT=0x{:08X}; falling back to original IDirect3D9::CreateDevice",
                        static_cast<unsigned>(hr));
                }
                return fallback_->CreateDevice(adapter, type, focusWindow, behaviorFlags, params, device);
            }

        private:
            volatile LONG refs_ = 1;
            IDirect3D9Ex* ex_ = nullptr;
            IDirect3D9* fallback_ = nullptr;
        };

        IDirect3D9* WINAPI HookedDirect3DCreate9(UINT sdkVersion)
        {
            if (!OriginalDirect3DCreate9)
                return nullptr;

            IDirect3D9* fallback = OriginalDirect3DCreate9(sdkVersion);
            if (!fallback || !Settings::VRPreferD3D9Ex)
                return fallback;

            HMODULE provider = nullptr;
            if (!IsSystemModuleForAddress(reinterpret_cast<const void*>(OriginalDirect3DCreate9), provider))
            {
                if (!ThirdPartyLogged.exchange(true))
                    spdlog::warn("VR D3D9Ex upgrade: third-party d3d9 provider detected; device upgrade skipped to preserve wrapper compatibility");
                return fallback;
            }

            const auto createEx = reinterpret_cast<Direct3DCreate9ExFn>(
                GetProcAddress(provider, "Direct3DCreate9Ex"));
            if (!createEx)
                return fallback;

            IDirect3D9Ex* ex = nullptr;
            const HRESULT hr = createEx(sdkVersion, &ex);
            if (FAILED(hr) || !ex)
                return fallback;

            auto* wrapper = new (std::nothrow) Direct3D9ExCompat(ex, fallback);
            if (!wrapper)
            {
                ex->Release();
                return fallback;
            }
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

    class D3D9ExUpgradeHook final : public Hook
    {
    public:
        std::string_view description() override { return "OpenXRVRD3D9ExUpgrade"; }
        void declare_settings() override { Settings::VRPreferD3D9Ex.needs_restart(); }
        bool validate() override { return Settings::VRPreferD3D9Ex; }
        bool apply() override
        {
            if (!PatchDirect3DCreate9Import())
            {
                spdlog::warn("VR D3D9Ex upgrade: Direct3DCreate9 IAT entry was not found/patched; original D3D9 path remains active");
                return true;
            }
            spdlog::info("VR D3D9Ex upgrade: Direct3DCreate9 IAT hook armed before game device creation");
            return true;
        }

        static D3D9ExUpgradeHook instance;
    };

    D3D9ExUpgradeHook D3D9ExUpgradeHook::instance;
}