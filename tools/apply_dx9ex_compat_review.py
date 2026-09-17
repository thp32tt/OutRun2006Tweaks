from pathlib import Path


def replace(path, old, new, count=1):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    n = text.count(old)
    if n < count:
        raise SystemExit(f'{path}: expected at least {count} occurrence(s), found {n}: {old[:120]!r}')
    text = text.replace(old, new, count)
    p.write_text(text, encoding='utf-8')

# -----------------------------------------------------------------------------
# ex_device_upgrade.cpp: legacy D3D9 contract over D3D9Ex.
# -----------------------------------------------------------------------------
p = 'src/vr/d3d9/ex_device_upgrade.cpp'
replace(p, '#include <new>\n', '#include <new>\n#include <mutex>\n#include <vector>\n')
replace(p,
'''        constexpr std::size_t ResetVtableIndex = 16;\n        constexpr std::size_t CreateTextureVtableIndex = 23;''',
'''        constexpr std::size_t TestCooperativeLevelVtableIndex = 3;\n        constexpr std::size_t EvictManagedResourcesVtableIndex = 5;\n        constexpr std::size_t ResetVtableIndex = 16;\n        constexpr std::size_t CreateTextureVtableIndex = 23;''')
replace(p,
'''        SafetyHookInline ResetCompatHook{};\n        SafetyHookInline CreateTextureCompatHook{};''',
'''        SafetyHookInline TestCooperativeLevelCompatHook{};\n        SafetyHookInline EvictManagedResourcesCompatHook{};\n        SafetyHookInline ResetCompatHook{};\n        SafetyHookInline CreateTextureCompatHook{};''')
replace(p,
'''        std::atomic<std::uint64_t> ResetExRedirects{0};\n\n        bool IsCompatDevice(IDirect3DDevice9* device) noexcept''',
'''        std::atomic<std::uint64_t> ResetExRedirects{0};\n        std::atomic<std::uint64_t> CooperativeLevelTranslations{0};\n        std::atomic<std::uint64_t> ClassicResetStateRestores{0};\n        std::atomic<std::uint64_t> ClassicResetStateRestoreFailures{0};\n        std::atomic<bool> CompatWindowed{true};\n        std::atomic<HWND> CompatFocusWindow{nullptr};\n        std::atomic<bool> FirstCooperativeTranslationLogged{false};\n        std::atomic<bool> FirstResetStateRestoreFailureLogged{false};\n\n        struct CompatStateValue\n        {\n            DWORD state = 0;\n            DWORD value = 0;\n        };\n        struct CompatStageStateValue\n        {\n            DWORD stage = 0;\n            DWORD state = 0;\n            DWORD value = 0;\n        };\n        struct CompatClassicBaseline\n        {\n            std::vector<CompatStateValue> render;\n            std::vector<CompatStageStateValue> textureStage;\n            std::vector<CompatStageStateValue> sampler;\n            bool ready = false;\n        };\n        CompatClassicBaseline ClassicBaseline{};\n        std::mutex ClassicBaselineMutex;\n\n        bool CaptureClassicBaseline(IDirect3DDevice9* device) noexcept\n        {\n            if (!device) return false;\n            try\n            {\n                CompatClassicBaseline next{};\n                next.render.reserve(192);\n                for (DWORD state = 1; state <= 255; ++state)\n                {\n                    DWORD value = 0;\n                    if (SUCCEEDED(device->GetRenderState(\n                            static_cast<D3DRENDERSTATETYPE>(state), &value)))\n                        next.render.push_back({ state, value });\n                }\n                for (DWORD stage = 0; stage < 8; ++stage)\n                {\n                    for (DWORD state = 1; state <= 32; ++state)\n                    {\n                        DWORD value = 0;\n                        if (SUCCEEDED(device->GetTextureStageState(stage,\n                                static_cast<D3DTEXTURESTAGESTATETYPE>(state),\n                                &value)))\n                            next.textureStage.push_back({ stage, state, value });\n                    }\n                }\n                for (DWORD sampler = 0; sampler < 16; ++sampler)\n                {\n                    for (DWORD state = 1; state <= 16; ++state)\n                    {\n                        DWORD value = 0;\n                        if (SUCCEEDED(device->GetSamplerState(sampler,\n                                static_cast<D3DSAMPLERSTATETYPE>(state), &value)))\n                            next.sampler.push_back({ sampler, state, value });\n                    }\n                }\n                next.ready = !next.render.empty();\n                std::lock_guard<std::mutex> lock(ClassicBaselineMutex);\n                ClassicBaseline = std::move(next);\n                return ClassicBaseline.ready;\n            }\n            catch (...)\n            {\n                return false;\n            }\n        }\n\n        void ClearClassicBaseline() noexcept\n        {\n            std::lock_guard<std::mutex> lock(ClassicBaselineMutex);\n            ClassicBaseline = {};\n        }\n\n        void UpdateCompatPresentationState(IDirect3DDevice9* device,\n            const D3DPRESENT_PARAMETERS* params) noexcept\n        {\n            if (!device || !params) return;\n            CompatWindowed.store(params->Windowed != FALSE,\n                std::memory_order_release);\n            HWND window = params->hDeviceWindow;\n            if (!window)\n            {\n                D3DDEVICE_CREATION_PARAMETERS creation{};\n                if (SUCCEEDED(device->GetCreationParameters(&creation)))\n                    window = creation.hFocusWindow;\n            }\n            CompatFocusWindow.store(window, std::memory_order_release);\n        }\n\n        bool RestoreClassicResetState(IDirect3DDevice9* device) noexcept\n        {\n            if (!device) return false;\n            std::uint32_t failures = 0;\n            {\n                std::lock_guard<std::mutex> lock(ClassicBaselineMutex);\n                if (!ClassicBaseline.ready) return false;\n                for (const auto& item : ClassicBaseline.render)\n                    if (FAILED(device->SetRenderState(\n                            static_cast<D3DRENDERSTATETYPE>(item.state),\n                            item.value)))\n                        ++failures;\n                for (const auto& item : ClassicBaseline.textureStage)\n                    if (FAILED(device->SetTextureStageState(item.stage,\n                            static_cast<D3DTEXTURESTAGESTATETYPE>(item.state),\n                            item.value)))\n                        ++failures;\n                for (const auto& item : ClassicBaseline.sampler)\n                    if (FAILED(device->SetSamplerState(item.stage,\n                            static_cast<D3DSAMPLERSTATETYPE>(item.state),\n                            item.value)))\n                        ++failures;\n            }\n\n            D3DCAPS9 caps{};\n            const UINT streams = SUCCEEDED(device->GetDeviceCaps(&caps))\n                ? std::min<UINT>(caps.MaxStreams, 16u) : 16u;\n            for (DWORD stage = 0; stage < 16; ++stage)\n                if (FAILED(device->SetTexture(stage, nullptr))) ++failures;\n            for (UINT stream = 0; stream < streams; ++stream)\n            {\n                if (FAILED(device->SetStreamSource(stream, nullptr, 0, 0)))\n                    ++failures;\n                if (FAILED(device->SetStreamSourceFreq(stream, 1)))\n                    ++failures;\n            }\n            if (FAILED(device->SetIndices(nullptr))) ++failures;\n            if (FAILED(device->SetVertexShader(nullptr))) ++failures;\n            if (FAILED(device->SetPixelShader(nullptr))) ++failures;\n            // A null declaration restores the fixed-function/default declaration\n            // boundary expected after classic Reset. Some drivers reject it when\n            // no declaration path exists, so treat that call as best-effort.\n            device->SetVertexDeclaration(nullptr);\n\n            IDirect3DSurface9* backBuffer = nullptr;\n            D3DSURFACE_DESC desc{};\n            if (SUCCEEDED(device->GetBackBuffer(0, 0,\n                    D3DBACKBUFFER_TYPE_MONO, &backBuffer)) && backBuffer)\n            {\n                if (SUCCEEDED(backBuffer->GetDesc(&desc)) &&\n                    desc.Width && desc.Height)\n                {\n                    D3DVIEWPORT9 viewport{};\n                    viewport.Width = desc.Width;\n                    viewport.Height = desc.Height;\n                    viewport.MinZ = 0.0f;\n                    viewport.MaxZ = 1.0f;\n                    if (FAILED(device->SetViewport(&viewport))) ++failures;\n                    RECT scissor{ 0, 0, static_cast<LONG>(desc.Width),\n                        static_cast<LONG>(desc.Height) };\n                    if (FAILED(device->SetScissorRect(&scissor))) ++failures;\n                }\n                backBuffer->Release();\n            }\n\n            if (failures == 0)\n            {\n                ++ClassicResetStateRestores;\n                return true;\n            }\n            ++ClassicResetStateRestoreFailures;\n            if (!FirstResetStateRestoreFailureLogged.exchange(true))\n            {\n                spdlog::warn(\n                    "VR D3D9Ex compat: classic Reset state replay completed with {} rejected state writes; game/VR caches still re-prime from live state",\n                    failures);\n            }\n            return false;\n        }\n\n        bool IsCompatDevice(IDirect3DDevice9* device) noexcept''')

replace(p,
'''            fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;\n\n            if ((fullscreen.Width == 0 || fullscreen.Height == 0 || fullscreen.Format == D3DFMT_UNKNOWN) && deviceEx)\n            {\n                D3DDEVICE_CREATION_PARAMETERS creation{};\n                D3DDISPLAYROTATION rotation = D3DDISPLAYROTATION_IDENTITY;\n                D3DDISPLAYMODEEX current{};\n                current.Size = sizeof(current);\n                if (SUCCEEDED(deviceEx->GetCreationParameters(&creation)) &&\n                    SUCCEEDED(deviceEx->GetDisplayModeEx(0, &current, &rotation)))\n                {\n                    if (!fullscreen.Width) fullscreen.Width = current.Width;\n                    if (!fullscreen.Height) fullscreen.Height = current.Height;\n                    if (fullscreen.Format == D3DFMT_UNKNOWN) fullscreen.Format = current.Format;\n                    if (!fullscreen.RefreshRate) fullscreen.RefreshRate = current.RefreshRate;\n                }\n            }''',
'''            fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_UNKNOWN;\n\n            if (deviceEx)\n            {\n                D3DDEVICE_CREATION_PARAMETERS creation{};\n                D3DDISPLAYROTATION rotation = D3DDISPLAYROTATION_IDENTITY;\n                D3DDISPLAYMODEEX current{};\n                current.Size = sizeof(current);\n                if (SUCCEEDED(deviceEx->GetCreationParameters(&creation)) &&\n                    SUCCEEDED(deviceEx->GetDisplayModeEx(0, &current, &rotation)))\n                {\n                    if (!fullscreen.Width) fullscreen.Width = current.Width;\n                    if (!fullscreen.Height) fullscreen.Height = current.Height;\n                    if (fullscreen.Format == D3DFMT_UNKNOWN) fullscreen.Format = current.Format;\n                    if (!fullscreen.RefreshRate) fullscreen.RefreshRate = current.RefreshRate;\n                    fullscreen.ScanLineOrdering = current.ScanLineOrdering;\n                }\n            }\n            if (fullscreen.ScanLineOrdering == D3DSCANLINEORDERING_UNKNOWN)\n                fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;''')

replace(p,
'''        HRESULT __stdcall ResetCompatDest(IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params)''',
'''        HRESULT __stdcall TestCooperativeLevelCompatDest(\n            IDirect3DDevice9* device)\n        {\n            if (!IsCompatDevice(device))\n                return TestCooperativeLevelCompatHook.stdcall<HRESULT>(device);\n\n            IDirect3DDevice9Ex* deviceEx = nullptr;\n            if (FAILED(device->QueryInterface(__uuidof(IDirect3DDevice9Ex),\n                    reinterpret_cast<void**>(&deviceEx))) || !deviceEx)\n                return TestCooperativeLevelCompatHook.stdcall<HRESULT>(device);\n\n            HWND window = CompatFocusWindow.load(std::memory_order_acquire);\n            if (!window) window = GetDesktopWindow();\n            const HRESULT state = deviceEx->CheckDeviceState(window);\n            deviceEx->Release();\n            ++CooperativeLevelTranslations;\n\n            HRESULT translated = D3D_OK;\n            if (state == S_PRESENT_MODE_CHANGED)\n                translated = D3DERR_DEVICENOTRESET;\n            else if (state == S_PRESENT_OCCLUDED)\n                translated = CompatWindowed.load(std::memory_order_acquire)\n                    ? D3D_OK : D3DERR_DEVICELOST;\n            else if (state == D3DERR_DEVICELOST)\n                translated = D3DERR_DEVICELOST;\n            else if (FAILED(state))\n                translated = D3DERR_DEVICELOST;\n\n            if (!FirstCooperativeTranslationLogged.exchange(true))\n                spdlog::info(\n                    "VR D3D9Ex compat: TestCooperativeLevel is translated from CheckDeviceState for legacy lost-device recovery");\n            return translated;\n        }\n\n        HRESULT __stdcall EvictManagedResourcesCompatDest(\n            IDirect3DDevice9* device)\n        {\n            if (IsCompatDevice(device))\n                return D3D_OK;\n            return EvictManagedResourcesCompatHook.stdcall<HRESULT>(device);\n        }\n\n        HRESULT __stdcall ResetCompatDest(IDirect3DDevice9* device, D3DPRESENT_PARAMETERS* params)''')

replace(p,
'''            const HRESULT hr = deviceEx->ResetEx(params, fullscreenPtr);\n            deviceEx->Release();\n            ++ResetExRedirects;''',
'''            const HRESULT hr = deviceEx->ResetEx(params, fullscreenPtr);\n            deviceEx->Release();\n            if (SUCCEEDED(hr))\n            {\n                UpdateCompatPresentationState(device, params);\n                RestoreClassicResetState(device);\n            }\n            ++ResetExRedirects;''', 1)

replace(p,
'''        HRESULT CreateManagedTextureCompat(\n            const char* label,\n            std::atomic<std::uint64_t>& counter,\n            DWORD usage,\n            CreateFn&& create)''',
'''        HRESULT CreateManagedTextureCompat(\n            const char* label,\n            std::atomic<std::uint64_t>& counter,\n            DWORD usage,\n            bool allowNonDynamicFallback,\n            CreateFn&& create)''')
replace(p,
'''            // Some legacy formats reject DYNAMIC even though a DEFAULT texture is valid.\n            // Retry without DYNAMIC so non-locking resources can still render. If the game\n            // later requires LockRect on such a texture the failure will remain visible in\n            // the game log instead of crashing at creation time.\n            ++ManagedTextureDynamicFallbacks;\n            hr = create(usage, D3DPOOL_DEFAULT);''',
'''            // R14 provides an independent CPU shadow for 2D textures, so those\n            // resources can safely fall back to non-dynamic DEFAULT. Cube/volume\n            // textures do not yet have that shadow contract: fail creation rather\n            // than return an object whose later Lock* semantics silently differ\n            // from legacy MANAGED.\n            if (!allowNonDynamicFallback)\n            {\n                ++ManagedCreateFailures;\n                spdlog::warn(\n                    "VR D3D9Ex compat: MANAGED {} requires a non-dynamic fallback that cannot preserve Lock semantics; failing closed hr=0x{:08X}",\n                    label, static_cast<unsigned>(hr));\n                return hr;\n            }\n            ++ManagedTextureDynamicFallbacks;\n            hr = create(usage, D3DPOOL_DEFAULT);''')
replace(p, 'return CreateManagedTextureCompat("texture", ManagedTextureCreates, usage,\n', 'return CreateManagedTextureCompat("texture", ManagedTextureCreates, usage, true,\n')
replace(p, 'return CreateManagedTextureCompat("volume texture", ManagedVolumeTextureCreates, usage,\n', 'return CreateManagedTextureCompat("volume texture", ManagedVolumeTextureCreates, usage, false,\n')
replace(p, 'return CreateManagedTextureCompat("cube texture", ManagedCubeTextureCreates, usage,\n', 'return CreateManagedTextureCompat("cube texture", ManagedCubeTextureCreates, usage, false,\n')

replace(p,
'''        void ClearCompatHooks() noexcept\n        {\n            CompatDevice.store(nullptr, std::memory_order_release);\n            ResetCompatHook = {};''',
'''        void ClearCompatHooks() noexcept\n        {\n            CompatDevice.store(nullptr, std::memory_order_release);\n            CompatFocusWindow.store(nullptr, std::memory_order_release);\n            TestCooperativeLevelCompatHook = {};\n            EvictManagedResourcesCompatHook = {};\n            ResetCompatHook = {};''')
replace(p, '            CreateIndexBufferCompatHook = {};\n        }', '            CreateIndexBufferCompatHook = {};\n            ClearClassicBaseline();\n        }', 1)

replace(p,
'''            auto* baseDevice = static_cast<IDirect3DDevice9*>(deviceEx);\n            void** vtable = *reinterpret_cast<void***>(baseDevice);''',
'''            auto* baseDevice = static_cast<IDirect3DDevice9*>(deviceEx);\n            IDirect3DDevice9* const existing =\n                CompatDevice.load(std::memory_order_acquire);\n            if (existing && existing != baseDevice)\n            {\n                spdlog::warn(\n                    "VR D3D9Ex compat: a second promoted game device was requested; keeping the first compatibility owner and forcing the new device back to classic D3D9");\n                return false;\n            }\n            if (!CaptureClassicBaseline(baseDevice))\n            {\n                spdlog::error(\n                    "VR D3D9Ex compat: could not capture the fresh-device classic state baseline; rejecting Ex promotion");\n                return false;\n            }\n            void** vtable = *reinterpret_cast<void***>(baseDevice);''')

replace(p,
'''            ResetCompatHook = safetyhook::create_inline(vtable[ResetVtableIndex], ResetCompatDest);\n            CreateTextureCompatHook = safetyhook::create_inline(vtable[CreateTextureVtableIndex], CreateTextureCompatDest);''',
'''            const auto disabled = safetyhook::InlineHook::StartDisabled;\n            TestCooperativeLevelCompatHook = safetyhook::create_inline(\n                vtable[TestCooperativeLevelVtableIndex],\n                TestCooperativeLevelCompatDest, disabled);\n            EvictManagedResourcesCompatHook = safetyhook::create_inline(\n                vtable[EvictManagedResourcesVtableIndex],\n                EvictManagedResourcesCompatDest, disabled);\n            ResetCompatHook = safetyhook::create_inline(\n                vtable[ResetVtableIndex], ResetCompatDest, disabled);\n            CreateTextureCompatHook = safetyhook::create_inline(vtable[CreateTextureVtableIndex], CreateTextureCompatDest, disabled);''')
replace(p, 'CreateVolumeTextureCompatHook = safetyhook::create_inline(vtable[CreateVolumeTextureVtableIndex], CreateVolumeTextureCompatDest);', 'CreateVolumeTextureCompatHook = safetyhook::create_inline(vtable[CreateVolumeTextureVtableIndex], CreateVolumeTextureCompatDest, disabled);')
replace(p, 'CreateCubeTextureCompatHook = safetyhook::create_inline(vtable[CreateCubeTextureVtableIndex], CreateCubeTextureCompatDest);', 'CreateCubeTextureCompatHook = safetyhook::create_inline(vtable[CreateCubeTextureVtableIndex], CreateCubeTextureCompatDest, disabled);')
replace(p, 'CreateVertexBufferCompatHook = safetyhook::create_inline(vtable[CreateVertexBufferVtableIndex], CreateVertexBufferCompatDest);', 'CreateVertexBufferCompatHook = safetyhook::create_inline(vtable[CreateVertexBufferVtableIndex], CreateVertexBufferCompatDest, disabled);')
replace(p, 'CreateIndexBufferCompatHook = safetyhook::create_inline(vtable[CreateIndexBufferVtableIndex], CreateIndexBufferCompatDest);', 'CreateIndexBufferCompatHook = safetyhook::create_inline(vtable[CreateIndexBufferVtableIndex], CreateIndexBufferCompatDest, disabled);')
replace(p,
'''            if (!ResetCompatHook || !CreateTextureCompatHook || !CreateVolumeTextureCompatHook ||\n                !CreateCubeTextureCompatHook || !CreateVertexBufferCompatHook || !CreateIndexBufferCompatHook)\n            {\n                spdlog::error("VR D3D9Ex compat: failed to install one or more managed-resource hooks; rejecting Ex device");\n                ClearCompatHooks();\n                return false;\n            }\n\n            CompatDevice.store(baseDevice, std::memory_order_release);''',
'''            SafetyHookInline* hooks[]{\n                &TestCooperativeLevelCompatHook, &EvictManagedResourcesCompatHook,\n                &ResetCompatHook, &CreateTextureCompatHook,\n                &CreateVolumeTextureCompatHook, &CreateCubeTextureCompatHook,\n                &CreateVertexBufferCompatHook, &CreateIndexBufferCompatHook\n            };\n            for (auto* hook : hooks)\n            {\n                if (!*hook || !hook->enable().has_value())\n                {\n                    spdlog::error(\n                        "VR D3D9Ex compat: compatibility hook transaction was partial; rejecting Ex device");\n                    ClearCompatHooks();\n                    return false;\n                }\n            }\n\n            CompatDevice.store(baseDevice, std::memory_order_release);''')
replace(p,
'''                "VR D3D9Ex compat: managed-resource compatibility hooks installed (Reset/CreateTexture/Volume/Cube/VB/IB); MANAGED buffers -> DEFAULT, MANAGED textures -> DEFAULT|DYNAMIC");''',
'''                "VR D3D9Ex compat: legacy contract hooks installed (TestCooperativeLevel/EvictManaged/Reset/resources); fresh-device state baseline captured; MANAGED 2D -> R14 shadow, cube/volume fail closed if DYNAMIC is unavailable");''')

replace(p,
'''                    fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;\n                    if ((fullscreen.Width == 0 || fullscreen.Height == 0 || fullscreen.Format == D3DFMT_UNKNOWN) && ex_)\n                    {''',
'''                    fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_UNKNOWN;\n                    if (ex_)\n                    {''')
replace(p,
'''                            if (!fullscreen.RefreshRate) fullscreen.RefreshRate = current.RefreshRate;\n                        }\n                    }\n                    fullscreenPtr = &fullscreen;''',
'''                            if (!fullscreen.RefreshRate) fullscreen.RefreshRate = current.RefreshRate;\n                            fullscreen.ScanLineOrdering = current.ScanLineOrdering;\n                        }\n                    }\n                    if (fullscreen.ScanLineOrdering == D3DSCANLINEORDERING_UNKNOWN)\n                        fullscreen.ScanLineOrdering = D3DSCANLINEORDERING_PROGRESSIVE;\n                    fullscreenPtr = &fullscreen;''', 1)
replace(p,
'''                    *device = static_cast<IDirect3DDevice9*>(deviceEx);\n                    if (!FirstUpgradeLogged.exchange(true))''',
'''                    *device = static_cast<IDirect3DDevice9*>(deviceEx);\n                    UpdateCompatPresentationState(*device, params);\n                    if (!FirstUpgradeLogged.exchange(true))''')

# -----------------------------------------------------------------------------
# ex_device_upgrade_r13.cpp: ResetEx + classic state replay is authoritative.
# -----------------------------------------------------------------------------
p = 'src/vr/d3d9/ex_device_upgrade_r13.cpp'
replace(p,
'''        result = deviceEx->ResetEx(params, fullscreenPtr);\n        deviceEx->Release();\n        ++OutRunVRD3D9ExUpgrade::ResetExRedirects;''',
'''        result = deviceEx->ResetEx(params, fullscreenPtr);\n        deviceEx->Release();\n        if (SUCCEEDED(result))\n        {\n            OutRunVRD3D9ExUpgrade::UpdateCompatPresentationState(device, params);\n            OutRunVRD3D9ExUpgrade::RestoreClassicResetState(device);\n        }\n        ++OutRunVRD3D9ExUpgrade::ResetExRedirects;''')
replace(p,
'''            "VR D3D9Ex R13: authoritative stereo Reset path called ResetEx hr=0x{:08X}; no competing Reset inline hook",''',
'''            "VR D3D9Ex R13: authoritative stereo Reset path called ResetEx + classic-state replay hr=0x{:08X}; no competing Reset inline hook",''')

# -----------------------------------------------------------------------------
# R14: keep shadow across read-only GetSurfaceLevel; retire on actual external writes.
# -----------------------------------------------------------------------------
p = 'src/vr/d3d9/ex_device_upgrade_r14.cpp'
replace(p,
'''        constexpr std::size_t R14DeviceUpdateSurfaceVtableIndex = 30;\n        constexpr std::size_t R14DeviceUpdateTextureVtableIndex = 31;''',
'''        constexpr std::size_t R14DeviceUpdateSurfaceVtableIndex = 30;\n        constexpr std::size_t R14DeviceUpdateTextureVtableIndex = 31;\n        constexpr std::size_t R14DeviceStretchRectVtableIndex = 34;\n        constexpr std::size_t R14DeviceColorFillVtableIndex = 35;\n        constexpr std::size_t R14SurfaceLockRectVtableIndex = 13;\n        constexpr std::size_t R14SurfaceGetDCVtableIndex = 15;''')
replace(p,
'''        SafetyHookInline R14DeviceUpdateSurfaceHook{};\n        SafetyHookInline R14DeviceUpdateTextureHook{};''',
'''        SafetyHookInline R14DeviceUpdateSurfaceHook{};\n        SafetyHookInline R14DeviceUpdateTextureHook{};\n        SafetyHookInline R14DeviceStretchRectHook{};\n        SafetyHookInline R14DeviceColorFillHook{};\n        SafetyHookInline R14SurfaceLockRectHook{};\n        SafetyHookInline R14SurfaceGetDCHook{};''')
replace(p,
'''        void* R14DeviceUpdateSurfaceTarget = nullptr;\n        void* R14DeviceUpdateTextureTarget = nullptr;''',
'''        void* R14DeviceUpdateSurfaceTarget = nullptr;\n        void* R14DeviceUpdateTextureTarget = nullptr;\n        void* R14DeviceStretchRectTarget = nullptr;\n        void* R14DeviceColorFillTarget = nullptr;\n        void* R14SurfaceLockRectTarget = nullptr;\n        void* R14SurfaceGetDCTarget = nullptr;''')

replace(p,
'''        HRESULT __stdcall TextureGetSurfaceLevelDestR14(\n            IDirect3DTexture9* texture, UINT level, IDirect3DSurface9** surface)\n        {\n            const R14EntryPtr entry = R14Find(texture);\n            if (entry && !R14RetireShadow(entry, "external GetSurfaceLevel"))\n            {\n                if (surface) *surface = nullptr;\n                return D3DERR_INVALIDCALL;\n            }\n            return R14TextureGetSurfaceLevelHook.stdcall<HRESULT>(\n                texture, level, surface);\n        }''',
'''        bool R14EnsureSurfaceHooks(IDirect3DSurface9* surface) noexcept;\n\n        HRESULT __stdcall TextureGetSurfaceLevelDestR14(\n            IDirect3DTexture9* texture, UINT level, IDirect3DSurface9** surface)\n        {\n            const R14EntryPtr entry = R14Find(texture);\n            const HRESULT hr = R14TextureGetSurfaceLevelHook.stdcall<HRESULT>(\n                texture, level, surface);\n            if (!entry || FAILED(hr) || !surface || !*surface)\n                return hr;\n\n            // Merely borrowing a level surface is not a write. Keep the CPU\n            // shadow alive when we can observe the surface's mutating entry\n            // points; otherwise retire before exposing an untracked alias.\n            if (R14EnsureSurfaceHooks(*surface))\n                return hr;\n            if (R14RetireShadow(entry, "untracked external level surface"))\n                return hr;\n\n            (*surface)->Release();\n            *surface = nullptr;\n            return D3DERR_INVALIDCALL;\n        }''')

# Only retire after successful external device writes.
replace(p, '            if (destination && R14InternalUploadDepth == 0)\n', '            if (SUCCEEDED(hr) && destination && R14InternalUploadDepth == 0)\n', 2)

insert_anchor = '''        bool InstallManagedResourceCompatR14(IDirect3DDevice9Ex* deviceEx)\n'''
insert_code = r'''        void R14MarkSurfaceExternalWrite(IDirect3DSurface9* surface,
            const char* reason) noexcept
        {
            if (!surface) return;
            IDirect3DTexture9* texture = nullptr;
            if (SUCCEEDED(surface->GetContainer(__uuidof(IDirect3DTexture9),
                    reinterpret_cast<void**>(&texture))) && texture)
            {
                R14MarkExternalGpuWrite(texture, reason);
                texture->Release();
            }
        }

        HRESULT __stdcall SurfaceLockRectDestR14(IDirect3DSurface9* surface,
            D3DLOCKED_RECT* locked, const RECT* rect, DWORD flags)
        {
            const HRESULT hr = R14SurfaceLockRectHook.stdcall<HRESULT>(
                surface, locked, rect, flags);
            if (SUCCEEDED(hr) && (flags & D3DLOCK_READONLY) == 0)
                R14MarkSurfaceExternalWrite(surface, "external level-surface LockRect");
            return hr;
        }

        HRESULT __stdcall SurfaceGetDCDestR14(IDirect3DSurface9* surface,
            HDC* dc)
        {
            const HRESULT hr = R14SurfaceGetDCHook.stdcall<HRESULT>(surface, dc);
            if (SUCCEEDED(hr))
                R14MarkSurfaceExternalWrite(surface, "external level-surface GetDC");
            return hr;
        }

        bool R14EnsureSurfaceHooks(IDirect3DSurface9* surface) noexcept
        {
            if (!surface) return false;
            std::lock_guard<std::mutex> installLock(R14ResourceHookMutex);
            void** vtable = *reinterpret_cast<void***>(surface);
            if (!vtable) return false;
            if (R14SurfaceLockRectHook && R14SurfaceGetDCHook)
            {
                return R14SurfaceLockRectTarget ==
                        vtable[R14SurfaceLockRectVtableIndex] &&
                    R14SurfaceGetDCTarget == vtable[R14SurfaceGetDCVtableIndex];
            }
            const auto disabled = safetyhook::InlineHook::StartDisabled;
            R14SurfaceLockRectHook = safetyhook::create_inline(
                vtable[R14SurfaceLockRectVtableIndex], SurfaceLockRectDestR14,
                disabled);
            R14SurfaceGetDCHook = safetyhook::create_inline(
                vtable[R14SurfaceGetDCVtableIndex], SurfaceGetDCDestR14,
                disabled);
            if (!R14SurfaceLockRectHook || !R14SurfaceGetDCHook ||
                !R14SurfaceLockRectHook.enable().has_value() ||
                !R14SurfaceGetDCHook.enable().has_value())
            {
                R14SurfaceGetDCHook = {};
                R14SurfaceLockRectHook = {};
                R14SurfaceLockRectTarget = nullptr;
                R14SurfaceGetDCTarget = nullptr;
                return false;
            }
            R14SurfaceLockRectTarget = vtable[R14SurfaceLockRectVtableIndex];
            R14SurfaceGetDCTarget = vtable[R14SurfaceGetDCVtableIndex];
            return true;
        }

        HRESULT __stdcall StretchRectDestR14(IDirect3DDevice9* device,
            IDirect3DSurface9* source, const RECT* sourceRect,
            IDirect3DSurface9* destination, const RECT* destinationRect,
            D3DTEXTUREFILTERTYPE filter)
        {
            const HRESULT hr = R14DeviceStretchRectHook.stdcall<HRESULT>(
                device, source, sourceRect, destination, destinationRect, filter);
            if (SUCCEEDED(hr) && destination && R14InternalUploadDepth == 0)
                R14MarkSurfaceExternalWrite(destination, "external StretchRect");
            return hr;
        }

        HRESULT __stdcall ColorFillDestR14(IDirect3DDevice9* device,
            IDirect3DSurface9* surface, const RECT* rect, D3DCOLOR color)
        {
            const HRESULT hr = R14DeviceColorFillHook.stdcall<HRESULT>(
                device, surface, rect, color);
            if (SUCCEEDED(hr) && surface && R14InternalUploadDepth == 0)
                R14MarkSurfaceExternalWrite(surface, "external ColorFill");
            return hr;
        }

'''
replace(p, insert_anchor, insert_code + insert_anchor)

replace(p,
'''                R14TextureAddDirtyRectHook && R14DeviceUpdateSurfaceHook &&\n                R14DeviceUpdateTextureHook)''',
'''                R14TextureAddDirtyRectHook && R14DeviceUpdateSurfaceHook &&\n                R14DeviceUpdateTextureHook && R14DeviceStretchRectHook &&\n                R14DeviceColorFillHook)''')
replace(p,
'''                    R14DeviceUpdateTextureTarget ==\n                        deviceVtable[R14DeviceUpdateTextureVtableIndex];''',
'''                    R14DeviceUpdateTextureTarget ==\n                        deviceVtable[R14DeviceUpdateTextureVtableIndex] &&\n                    R14DeviceStretchRectTarget ==\n                        deviceVtable[R14DeviceStretchRectVtableIndex] &&\n                    R14DeviceColorFillTarget ==\n                        deviceVtable[R14DeviceColorFillVtableIndex];''')
replace(p,
'''            R14DeviceUpdateTextureHook = safetyhook::create_inline(\n                deviceVtable[R14DeviceUpdateTextureVtableIndex],\n                UpdateTextureDestR14, disabled);''',
'''            R14DeviceUpdateTextureHook = safetyhook::create_inline(\n                deviceVtable[R14DeviceUpdateTextureVtableIndex],\n                UpdateTextureDestR14, disabled);\n            R14DeviceStretchRectHook = safetyhook::create_inline(\n                deviceVtable[R14DeviceStretchRectVtableIndex],\n                StretchRectDestR14, disabled);\n            R14DeviceColorFillHook = safetyhook::create_inline(\n                deviceVtable[R14DeviceColorFillVtableIndex],\n                ColorFillDestR14, disabled);''')
replace(p,
'''                &R14DeviceUpdateSurfaceHook,\n                &R14DeviceUpdateTextureHook\n            };''',
'''                &R14DeviceUpdateSurfaceHook,\n                &R14DeviceUpdateTextureHook,\n                &R14DeviceStretchRectHook,\n                &R14DeviceColorFillHook\n            };''')
replace(p,
'''                    R14DeviceUpdateTextureHook = {};\n                    R14DeviceUpdateSurfaceHook = {};''',
'''                    R14DeviceColorFillHook = {};\n                    R14DeviceStretchRectHook = {};\n                    R14DeviceUpdateTextureHook = {};\n                    R14DeviceUpdateSurfaceHook = {};''')
replace(p,
'''                    R14DeviceUpdateTextureTarget = nullptr;\n                    return false;''',
'''                    R14DeviceUpdateTextureTarget = nullptr;\n                    R14DeviceStretchRectTarget = nullptr;\n                    R14DeviceColorFillTarget = nullptr;\n                    return false;''')
replace(p,
'''            R14DeviceUpdateTextureTarget =\n                deviceVtable[R14DeviceUpdateTextureVtableIndex];\n            return true;''',
'''            R14DeviceUpdateTextureTarget =\n                deviceVtable[R14DeviceUpdateTextureVtableIndex];\n            R14DeviceStretchRectTarget =\n                deviceVtable[R14DeviceStretchRectVtableIndex];\n            R14DeviceColorFillTarget =\n                deviceVtable[R14DeviceColorFillVtableIndex];\n            return true;''')

# -----------------------------------------------------------------------------
# R32: cache deterministic DirectGPU copy rejection and trim telemetry overhead.
# -----------------------------------------------------------------------------
p = 'src/vr/d3d9/stereo_renderer_r32.cpp'
replace(p,
'''        bool R32FirstPendingFenceLogged = false;\n\n        std::uint32_t R32DirectHostPid = 0;''',
'''        bool R32FirstPendingFenceLogged = false;\n        bool R32FirstDirectCopyRejectLogged = false;\n        bool R32DirectCopyPathRejected = false;\n        HRESULT R32DirectCopyRejectHr = D3D_OK;\n\n        std::uint32_t R32DirectHostPid = 0;''')

replace(p,
'''            LARGE_INTEGER frequency{};\n            LARGE_INTEGER start{};\n            const bool highResolutionClock =\n                QueryPerformanceFrequency(&frequency) != FALSE &&\n                frequency.QuadPart > 0 &&\n                QueryPerformanceCounter(&start) != FALSE;''',
'''            static const LONGLONG qpcFrequency = []() noexcept {\n                LARGE_INTEGER value{};\n                return QueryPerformanceFrequency(&value) != FALSE\n                    ? value.QuadPart : 0;\n            }();\n            LARGE_INTEGER start{};\n            const bool highResolutionClock = qpcFrequency > 0 &&\n                QueryPerformanceCounter(&start) != FALSE;''')
replace(p, '                ? (frequency.QuadPart *\n', '                ? (qpcFrequency *\n')
replace(p, '                ++R32DirectFenceSuccess;\n                return true;', '                if (Settings::VRTelemetry) ++R32DirectFenceSuccess;\n                return true;', 2)
replace(p, '                    ++R32DirectFenceBudgetFallbacks;\n', '                    if (Settings::VRTelemetry) ++R32DirectFenceBudgetFallbacks;\n')
replace(p, '                ++R32PendingFenceErrors;\n                return false;', '                if (Settings::VRTelemetry) ++R32PendingFenceErrors;\n                return false;', 1)
replace(p, '                ++R32PendingFenceDrains;\n                return true;', '                if (Settings::VRTelemetry) ++R32PendingFenceDrains;\n                return true;')
replace(p, '                ++R32PendingFenceBlocks;\n', '                if (Settings::VRTelemetry) ++R32PendingFenceBlocks;\n')
replace(p, '            ++R32PendingFenceErrors;\n            return false;', '            if (Settings::VRTelemetry) ++R32PendingFenceErrors;\n            return false;', 1)
replace(p, '                ++R32DirectProbeCacheHits;\n                return true;', '                if (Settings::VRTelemetry) ++R32DirectProbeCacheHits;\n                return true;')

replace(p,
'''        void R32InvalidateDirectInteropOnly() noexcept\n        {\n            R32ClearPendingProducerFences();''',
'''        void R32InvalidateDirectInteropOnly() noexcept\n        {\n            R32ClearPendingProducerFences();\n            R32DirectCopyPathRejected = false;\n            R32DirectCopyRejectHr = D3D_OK;''')

replace(p,
'''            if (!frameId || !R32EnsureDirectResources(device) ||\n                !BackBuffer || !RightEyeSurface)\n                return false;''',
'''            if (!frameId || R32DirectCopyPathRejected ||\n                !R32EnsureDirectResources(device) ||\n                !BackBuffer || !RightEyeSurface)\n                return false;''')
replace(p,
'''            {\n                InternalPassScope guard;\n                if (FAILED(device->StretchRect(BackBuffer, nullptr,\n                        slot.leftSurface, nullptr, D3DTEXF_NONE)) ||\n                    FAILED(device->StretchRect(RightEyeSurface, nullptr,\n                        slot.rightSurface, nullptr, D3DTEXF_NONE)) ||\n                    FAILED(slot.fence->Issue(D3DISSUE_END)))\n                    return false;\n            }''',
'''            {\n                InternalPassScope guard;\n                const HRESULT leftCopy = device->StretchRect(BackBuffer, nullptr,\n                    slot.leftSurface, nullptr, D3DTEXF_NONE);\n                const HRESULT rightCopy = SUCCEEDED(leftCopy)\n                    ? device->StretchRect(RightEyeSurface, nullptr,\n                        slot.rightSurface, nullptr, D3DTEXF_NONE)\n                    : leftCopy;\n                if (FAILED(leftCopy) || FAILED(rightCopy))\n                {\n                    R32DirectCopyPathRejected = true;\n                    R32DirectCopyRejectHr = FAILED(leftCopy)\n                        ? leftCopy : rightCopy;\n                    if (!R32FirstDirectCopyRejectLogged)\n                    {\n                        R32FirstDirectCopyRejectLogged = true;\n                        spdlog::warn(\n                            "VR R32 D3D9Ex: shared-eye StretchRect rejected hr=0x{:08X}; DirectGPU copy path is disabled until Reset/interop revalidation instead of retrying every Present",\n                            static_cast<unsigned>(R32DirectCopyRejectHr));\n                    }\n                    return false;\n                }\n                if (FAILED(slot.fence->Issue(D3DISSUE_END)))\n                    return false;\n            }''')
replace(p,
'''            R32ForgetDirectIdentity();\n            R32ClearPendingProducerFences();\n        }''',
'''            R32ForgetDirectIdentity();\n            R32ClearPendingProducerFences();\n            R32DirectCopyPathRejected = false;\n            R32DirectCopyRejectHr = D3D_OK;\n        }''', 1)

# -----------------------------------------------------------------------------
# Settings text: reflect hardened but still opt-in Ex path.
# -----------------------------------------------------------------------------
p = 'src/vr/settings.cpp'
replace(p,
'''\tSetting<bool> VRPreferD3D9Ex{ "VR", "PreferD3D9Ex", false,\n\t\t"Opt-in guarded D3D9Ex shared-eye transport. R14 binds MANAGED 2D CPU shadows to texture lifetime and retires them on unmirrorable writes, but hardware validation is still required before making this the default." };''',
'''\tSetting<bool> VRPreferD3D9Ex{ "VR", "PreferD3D9Ex", false,\n\t\t"Opt-in guarded D3D9Ex shared-eye transport. Legacy lost-device/Reset semantics are translated, R14 tracks actual external 2D writes, and unsupported cube/volume lock fallbacks fail closed; hardware validation is still required before making this the default." };''')

print('DX9Ex compatibility review patch applied')
