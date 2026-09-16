// R14 D3D9Ex managed-texture compatibility overlay.
//
// D3D9Ex has no D3DPOOL_MANAGED. The R13 compatibility layer translates legacy
// MANAGED 2D textures to DEFAULT|DYNAMIC, but a few drivers/resources still
// reject LockRect on those translated GPU textures. R14 keeps a SYSTEMMEM CPU
// shadow for every successfully translated MANAGED 2D texture and services the
// game's LockRect/UnlockRect against that shadow. Written regions are uploaded
// to the DEFAULT texture with UpdateSurface (UpdateTexture fallback).
//
// This makes the high-quality D3D9Ex shared-eye transport substantially safer
// without pretending that every possible legacy resource class has been proven:
// cube/volume MANAGED resources remain on the R13 compatibility path and the
// whole Ex promotion can still fail closed to classic D3D9 during device setup.

#include "ex_device_upgrade_r13.cpp"

namespace OutRunVRD3D9ExUpgradeR13
{
    namespace
    {
        constexpr std::size_t R14ShadowCapacity = 256;
        constexpr std::uint32_t R14MaxTrackedLevels = 32;

        SafetyHookInline R14CreateTextureR13Hook{};
        SafetyHookInline R14TextureLockR13Hook{};
        SafetyHookInline R14TextureUnlockR13Hook{};

        struct R14ShadowEntry
        {
            IDirect3DTexture9* gpu = nullptr;
            IDirect3DTexture9* cpu = nullptr;
            IDirect3DDevice9* device = nullptr;
            std::uint32_t lockedMask = 0;
            std::uint32_t readOnlyMask = 0;
            RECT lockRect[R14MaxTrackedLevels]{};
            bool lockRectValid[R14MaxTrackedLevels]{};
        };

        std::array<R14ShadowEntry, R14ShadowCapacity> R14Shadows{};
        std::size_t R14ShadowCursor = 0;
        std::uint64_t R14ShadowCreated = 0;
        std::uint64_t R14ShadowCreateFailed = 0;
        std::uint64_t R14ShadowLocks = 0;
        std::uint64_t R14ShadowUploads = 0;
        std::uint64_t R14ShadowUploadFailed = 0;
        bool R14FirstActiveLogged = false;
        bool R14FirstFallbackLogged = false;
        bool R14FirstUploadFailureLogged = false;

        void R14ReleaseEntry(R14ShadowEntry& entry) noexcept
        {
            if (entry.cpu)
            {
                entry.cpu->Release();
                entry.cpu = nullptr;
            }
            entry = {};
        }

        R14ShadowEntry* R14Find(IDirect3DTexture9* texture) noexcept
        {
            if (!texture) return nullptr;
            for (auto& entry : R14Shadows)
                if (entry.gpu == texture && entry.cpu)
                    return &entry;
            return nullptr;
        }

        void R14Track(IDirect3DDevice9* device, IDirect3DTexture9* gpu,
            IDirect3DTexture9* cpu) noexcept
        {
            if (!device || !gpu || !cpu) return;
            R14ShadowEntry* slot = nullptr;
            for (auto& entry : R14Shadows)
            {
                if (entry.gpu == gpu)
                {
                    slot = &entry;
                    break;
                }
            }
            if (!slot)
                slot = &R14Shadows[R14ShadowCursor++ % R14Shadows.size()];
            R14ReleaseEntry(*slot);
            slot->gpu = gpu;
            slot->cpu = cpu;
            slot->device = device;
            ++R14ShadowCreated;

            if (!R14FirstActiveLogged)
            {
                R14FirstActiveLogged = true;
                spdlog::info(
                    "VR R14 EX: MANAGED 2D CPU-shadow upload path ACTIVE; LockRect no longer depends on translated DEFAULT texture lockability");
            }
        }

        bool R14CreateCpuShadow(IDirect3DDevice9* device,
            IDirect3DTexture9* gpu, IDirect3DTexture9*& shadow) noexcept
        {
            shadow = nullptr;
            if (!device || !gpu) return false;
            D3DSURFACE_DESC desc{};
            if (FAILED(gpu->GetLevelDesc(0, &desc)) ||
                desc.Width == 0 || desc.Height == 0)
                return false;
            const UINT levels = gpu->GetLevelCount();
            if (levels == 0 || levels > R14MaxTrackedLevels)
                return false;

            // SYSTEMMEM is deliberately created with usage=0. Legacy MANAGED
            // textures cannot be render targets/depth surfaces, and stripping
            // DYNAMIC/AUTOGEN flags avoids invalid SYSTEMMEM combinations.
            const HRESULT hr = device->CreateTexture(
                desc.Width, desc.Height, levels, 0, desc.Format,
                D3DPOOL_SYSTEMMEM, &shadow, nullptr);
            return SUCCEEDED(hr) && shadow;
        }

        HRESULT __stdcall CreateTextureCompatDestR14(
            IDirect3DDevice9* device, UINT width, UINT height, UINT levels,
            DWORD usage, D3DFORMAT format, D3DPOOL pool,
            IDirect3DTexture9** texture, HANDLE* sharedHandle)
        {
            const HRESULT hr = R14CreateTextureR13Hook.stdcall<HRESULT>(
                device, width, height, levels, usage, format, pool,
                texture, sharedHandle);
            if (FAILED(hr) || pool != D3DPOOL_MANAGED || !texture || !*texture ||
                !OutRunVRD3D9ExUpgrade::IsCompatDevice(device))
                return hr;

            IDirect3DTexture9* shadow = nullptr;
            if (R14CreateCpuShadow(device, *texture, shadow))
            {
                R14Track(device, *texture, shadow);
            }
            else
            {
                ++R14ShadowCreateFailed;
                if (!R14FirstFallbackLogged)
                {
                    R14FirstFallbackLogged = true;
                    spdlog::warn(
                        "VR R14 EX: CPU shadow unavailable for one MANAGED 2D texture; retaining R13 DEFAULT|DYNAMIC LockRect compatibility for that resource");
                }
            }
            return hr;
        }

        DWORD R14SanitizeLockFlags(DWORD flags) noexcept
        {
            // DISCARD/NOOVERWRITE are GPU-dynamic hints and are invalid or
            // meaningless on SYSTEMMEM. NODIRTYUPDATE would suppress the dirty
            // tracking UpdateTexture may rely on, so R14 owns that policy too.
            return flags & ~(D3DLOCK_DISCARD | D3DLOCK_NOOVERWRITE |
                D3DLOCK_NODIRTYUPDATE);
        }

        HRESULT __stdcall TextureLockRectR14(IDirect3DTexture9* texture,
            UINT level, D3DLOCKED_RECT* locked, const RECT* rect, DWORD flags)
        {
            R14ShadowEntry* entry = R14Find(texture);
            if (!entry || level >= R14MaxTrackedLevels)
                return R14TextureLockR13Hook.stdcall<HRESULT>(
                    texture, level, locked, rect, flags);

            const DWORD sanitized = R14SanitizeLockFlags(flags);
            const HRESULT hr = entry->cpu->LockRect(
                level, locked, rect, sanitized);
            if (FAILED(hr))
            {
                // Fail open to the proven R13 dynamic-texture path. This keeps
                // startup compatible on drivers that reject the SYSTEMMEM form.
                return R14TextureLockR13Hook.stdcall<HRESULT>(
                    texture, level, locked, rect, flags);
            }

            const std::uint32_t bit = 1u << level;
            entry->lockedMask |= bit;
            if ((flags & D3DLOCK_READONLY) != 0) entry->readOnlyMask |= bit;
            else entry->readOnlyMask &= ~bit;
            if (rect)
            {
                entry->lockRect[level] = *rect;
                entry->lockRectValid[level] = true;
            }
            else
            {
                entry->lockRect[level] = {};
                entry->lockRectValid[level] = false;
            }
            ++R14ShadowLocks;
            return hr;
        }

        HRESULT R14UploadLevel(R14ShadowEntry& entry, UINT level) noexcept
        {
            if (!entry.device || !entry.cpu || !entry.gpu)
                return E_FAIL;

            IDirect3DSurface9* src = nullptr;
            IDirect3DSurface9* dst = nullptr;
            HRESULT hr = entry.cpu->GetSurfaceLevel(level, &src);
            if (SUCCEEDED(hr)) hr = entry.gpu->GetSurfaceLevel(level, &dst);
            if (SUCCEEDED(hr) && src && dst)
            {
                const RECT* rect = entry.lockRectValid[level]
                    ? &entry.lockRect[level] : nullptr;
                POINT point{};
                POINT* dstPoint = nullptr;
                if (rect)
                {
                    point.x = rect->left;
                    point.y = rect->top;
                    dstPoint = &point;
                }
                hr = entry.device->UpdateSurface(src, rect, dst, dstPoint);
            }
            if (src) src->Release();
            if (dst) dst->Release();

            // Some compressed/driver-specific resources reject UpdateSurface
            // but accept the documented SYSTEMMEM -> DEFAULT UpdateTexture path.
            if (FAILED(hr))
                hr = entry.device->UpdateTexture(entry.cpu, entry.gpu);
            return hr;
        }

        HRESULT __stdcall TextureUnlockRectR14(IDirect3DTexture9* texture,
            UINT level)
        {
            R14ShadowEntry* entry = R14Find(texture);
            if (!entry || level >= R14MaxTrackedLevels)
                return R14TextureUnlockR13Hook.stdcall<HRESULT>(texture, level);

            const std::uint32_t bit = 1u << level;
            if ((entry->lockedMask & bit) == 0)
                return R14TextureUnlockR13Hook.stdcall<HRESULT>(texture, level);

            const bool readOnly = (entry->readOnlyMask & bit) != 0;
            const HRESULT unlockHr = entry->cpu->UnlockRect(level);
            entry->lockedMask &= ~bit;
            entry->readOnlyMask &= ~bit;
            if (FAILED(unlockHr) || readOnly)
                return unlockHr;

            const HRESULT uploadHr = R14UploadLevel(*entry, level);
            entry->lockRectValid[level] = false;
            if (SUCCEEDED(uploadHr))
            {
                ++R14ShadowUploads;
                return unlockHr;
            }

            ++R14ShadowUploadFailed;
            if (!R14FirstUploadFailureLogged)
            {
                R14FirstUploadFailureLogged = true;
                spdlog::error(
                    "VR R14 EX: first CPU-shadow upload failed hr=0x{:08x}; texture remains tracked but direct D3D9Ex compatibility is not hardware-proven",
                    static_cast<unsigned>(uploadHr));
            }
            return uploadHr;
        }

        void R14RollbackHooks() noexcept
        {
            R14TextureUnlockR13Hook = {};
            R14TextureLockR13Hook = {};
            R14CreateTextureR13Hook = {};
        }

        class VRD3D9ExUpgradeR14Hook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRD3D9ExUpgradeR14";
            }
            bool validate() override
            {
                return Settings::VRPreferD3D9Ex;
            }
            bool apply() override
            {
                const auto disabled = safetyhook::InlineHook::StartDisabled;
                R14CreateTextureR13Hook = safetyhook::create_inline(
                    reinterpret_cast<void*>(&CreateTextureCompatDestR13),
                    CreateTextureCompatDestR14, disabled);
                R14TextureLockR13Hook = safetyhook::create_inline(
                    reinterpret_cast<void*>(&TextureLockRectR13),
                    TextureLockRectR14, disabled);
                R14TextureUnlockR13Hook = safetyhook::create_inline(
                    reinterpret_cast<void*>(&TextureUnlockRectR13),
                    TextureUnlockRectR14, disabled);

                SafetyHookInline* hooks[]{
                    &R14CreateTextureR13Hook,
                    &R14TextureLockR13Hook,
                    &R14TextureUnlockR13Hook
                };
                for (auto* hook : hooks)
                {
                    if (!*hook || !hook->enable().has_value())
                    {
                        R14RollbackHooks();
                        spdlog::error(
                            "VR R14 EX: CPU-shadow hook transaction failed; R13 remains active");
                        return false;
                    }
                }
                spdlog::info(
                    "VR R14 EX: MANAGED 2D CPU-shadow compatibility armed before D3D9Ex device promotion");
                return true;
            }
            static VRD3D9ExUpgradeR14Hook instance;
        };

        VRD3D9ExUpgradeR14Hook VRD3D9ExUpgradeR14Hook::instance;
    }
}
