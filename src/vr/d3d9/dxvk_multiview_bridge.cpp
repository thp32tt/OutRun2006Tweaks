#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <mutex>
#include <unordered_map>
#include <vector>

#include <spdlog/spdlog.h>

#include "plugin.hpp"
#include "vr/core/render_backend.hpp"
#include "vr/d3d9/dxvk_multiview_bridge.hpp"
#include "vr/d3d9/dxvk_openrbrvr_interop.hpp"
#include "vr/d3d9/dxvk_probe.hpp"

namespace Settings
{
    extern Setting<int> VRRenderBackend;
}

namespace OutRunVRDxvkMultiview
{
    namespace
    {
        using namespace OutRunVR::OpenRbrDxvk;

        constexpr std::uint32_t OutRunWvpRegister = 64;
        constexpr std::uint32_t OutRunWvpVectors = 4;
        constexpr std::uint32_t MaxD3D9VsFloatConstants = 256;
        constexpr std::uint32_t MinimumPatchedRegister = 128;

        thread_local std::uint32_t InternalProviderDepth = 0;

        struct InternalProviderScope
        {
            InternalProviderScope() noexcept { ++InternalProviderDepth; }
            ~InternalProviderScope() { --InternalProviderDepth; }
        };

        template <typename T>
        void ReleaseCom(T*& value) noexcept
        {
            if (value)
            {
                value->Release();
                value = nullptr;
            }
        }

        void ReplaceRef(IDirect3DSurface9*& slot, IDirect3DSurface9* value) noexcept
        {
            if (value)
                value->AddRef();
            ReleaseCom(slot);
            slot = value;
        }

        struct ShaderPatch
        {
            IDirect3DVertexShader9* original{};
            IDirect3DVertexShader9* patched{};
            std::uint32_t destinationRegister{};

            void Reset() noexcept
            {
                ReleaseCom(patched);
                ReleaseCom(original);
                destinationRegister = 0;
            }
        };

        std::recursive_mutex BridgeMutex;
        IDirect3DDevice9* CachedDevice = nullptr;
        IDirect3DVR9OutRun* Provider = nullptr;
        bool ProviderAttempted = false;

        HMODULE PatcherModule = nullptr;
        ChangeSpirvMultiViewFn ChangeSpirvMultiView = nullptr;
        OptimizeSpirvFn OptimizeSpirv = nullptr;
        bool PatcherAttempted = false;

        IDirect3DSurface9* LayeredColor = nullptr;
        IDirect3DSurface9* LayeredDepth = nullptr;
        IDirect3DSurface9* LogicalLeftColor = nullptr;
        IDirect3DSurface9* LogicalRightColor = nullptr;
        IDirect3DSurface9* LogicalLeftDepth = nullptr;
        IDirect3DSurface9* LogicalRightDepth = nullptr;
        D3DSURFACE_DESC LayeredColorDesc{};
        D3DSURFACE_DESC LayeredDepthDesc{};
        bool FrameTargetsReady = false;
        std::uint32_t BoundLayer = AllLayers;

        std::unordered_map<IDirect3DVertexShader9*, ShaderPatch> ShaderPatches;

        bool Armed = false;
        IDirect3DVertexShader9* ArmedOriginalShader = nullptr;

        std::atomic<std::uint64_t> ArmAttempts{0};
        std::atomic<std::uint64_t> ArmSuccess{0};
        std::atomic<std::uint64_t> ArmRejected{0};
        std::atomic<std::uint64_t> DrawSuccess{0};
        std::atomic<std::uint64_t> DrawFailure{0};
        std::atomic<std::uint64_t> Cancels{0};
        std::atomic<std::uint64_t> InterfaceMisses{0};
        std::atomic<std::uint64_t> ProtocolMismatches{0};
        std::atomic<std::uint64_t> CapabilityMisses{0};
        std::atomic<std::uint64_t> TargetCreates{0};
        std::atomic<std::uint64_t> TargetCreateFailures{0};
        std::atomic<std::uint64_t> TargetBinds{0};
        std::atomic<std::uint64_t> TargetFlushes{0};
        std::atomic<std::uint64_t> ShaderPatchAttempts{0};
        std::atomic<std::uint64_t> ShaderPatchSuccess{0};
        std::atomic<std::uint64_t> ShaderPatchFailures{0};
        std::atomic<std::uint64_t> ProviderDraws{0};
        std::atomic<std::uint64_t> TwoPassArrayDraws{0};

        bool FirstEnabledLogged = false;
        bool FirstMissingLogged = false;
        bool FirstPatcherMissingLogged = false;
        bool FirstPatchFailureLogged = false;
        bool FirstTargetsLogged = false;
        bool FirstFlushFailureLogged = false;

        bool BackendAllowsDxvk() noexcept
        {
            const auto requested = OutRunVR::RenderBackendFromSetting(
                Settings::VRRenderBackend.get());
            if (requested == OutRunVR::RenderBackend::D3D9TwoPass ||
                requested == OutRunVR::RenderBackend::Dx12)
                return false;
            return requested == OutRunVR::RenderBackend::Dxvk ||
                OutRunVRDxvkProbe::IsDxvkDetected();
        }

        bool SameSurfaceDesc(
            const D3DSURFACE_DESC& a,
            const D3DSURFACE_DESC& b) noexcept
        {
            return a.Width == b.Width &&
                a.Height == b.Height &&
                a.Format == b.Format &&
                a.MultiSampleType == b.MultiSampleType &&
                a.MultiSampleQuality == b.MultiSampleQuality;
        }

        bool ReadDesc(IDirect3DSurface9* surface, D3DSURFACE_DESC& desc) noexcept
        {
            desc = {};
            return surface && SUCCEEDED(surface->GetDesc(&desc));
        }

        void ReleaseShaderPatches() noexcept
        {
            for (auto& [_, patch] : ShaderPatches)
                patch.Reset();
            ShaderPatches.clear();
            ReleaseCom(ArmedOriginalShader);
            Armed = false;
        }

        void ReleaseFrameTargetsUnlocked() noexcept
        {
            FrameTargetsReady = false;
            BoundLayer = AllLayers;
            ReleaseCom(LayeredColor);
            ReleaseCom(LayeredDepth);
            ReleaseCom(LogicalLeftColor);
            ReleaseCom(LogicalRightColor);
            ReleaseCom(LogicalLeftDepth);
            ReleaseCom(LogicalRightDepth);
            LayeredColorDesc = {};
            LayeredDepthDesc = {};
        }

        void ReleaseProviderUnlocked() noexcept
        {
            ReleaseFrameTargetsUnlocked();
            ReleaseShaderPatches();
            ReleaseCom(Provider);
            CachedDevice = nullptr;
            ProviderAttempted = false;
            if (PatcherModule)
            {
                FreeLibrary(PatcherModule);
                PatcherModule = nullptr;
            }
            ChangeSpirvMultiView = nullptr;
            OptimizeSpirv = nullptr;
            PatcherAttempted = false;
        }

        IDirect3DVR9OutRun* ResolveProviderUnlocked(
            IDirect3DDevice9* device) noexcept
        {
            if (!device || !BackendAllowsDxvk())
                return nullptr;

            if (CachedDevice != device)
                ReleaseProviderUnlocked();
            if (Provider)
                return Provider;
            if (ProviderAttempted)
                return nullptr;

            ProviderAttempted = true;
            CachedDevice = device;

            HMODULE d3d9 = GetModuleHandleW(L"d3d9.dll");
            if (!d3d9)
            {
                ++InterfaceMisses;
                return nullptr;
            }

            const auto createVr = reinterpret_cast<Direct3DCreateVrFn>(
                GetProcAddress(d3d9, "Direct3DCreateVR"));
            if (!createVr)
            {
                ++InterfaceMisses;
                if (!FirstMissingLogged)
                {
                    FirstMissingLogged = true;
                    spdlog::info(
                        "VR DXVK MULTIVIEW: Direct3DCreateVR export not found; stock DXVK/system D3D9 stays on validated two-pass");
                }
                return nullptr;
            }

            IDirect3DVR9OutRun* provider = nullptr;
            const HRESULT hr = createVr(device, &provider);
            if (FAILED(hr) || !provider)
            {
                ++InterfaceMisses;
                if (!FirstMissingLogged)
                {
                    FirstMissingLogged = true;
                    spdlog::warn(
                        "VR DXVK MULTIVIEW: dxvk-openRBRVR provider creation failed hr=0x{:08X}; validated two-pass remains active",
                        static_cast<unsigned>(hr));
                }
                return nullptr;
            }

            Provider = provider;
            if (!FirstEnabledLogged)
            {
                FirstEnabledLogged = true;
                spdlog::info(
                    "VR DXVK MULTIVIEW: dxvk-openRBRVR IDirect3DVR9 negotiated; layered targets + SPIR-V ViewIndex path enabled with fail-closed two-pass fallback");
            }
            return Provider;
        }

        bool ResolvePatcherUnlocked() noexcept
        {
            if (ChangeSpirvMultiView)
                return true;
            if (PatcherAttempted)
                return false;
            PatcherAttempted = true;

            const wchar_t* candidates[] = {
                L"multiviewpatcher.dll",
                L"Plugins\\openRBRVR\\multiviewpatcher.dll",
            };
            for (const wchar_t* path : candidates)
            {
                PatcherModule = LoadLibraryW(path);
                if (PatcherModule)
                    break;
            }

            if (!PatcherModule)
            {
                if (!FirstPatcherMissingLogged)
                {
                    FirstPatcherMissingLogged = true;
                    spdlog::warn(
                        "VR DXVK MULTIVIEW: multiviewpatcher.dll (MPL-2.0, Detegr/RBR-spirvpatcher) not found; layered two-pass remains usable but true one-draw world multiview is disabled");
                }
                return false;
            }

            ChangeSpirvMultiView =
                reinterpret_cast<ChangeSpirvMultiViewFn>(
                    GetProcAddress(
                        PatcherModule,
                        "ChangeSPIRVMultiViewDataAccessLocation"));
            OptimizeSpirv = reinterpret_cast<OptimizeSpirvFn>(
                GetProcAddress(PatcherModule, "OptimizeSPIRV"));

            if (!ChangeSpirvMultiView)
            {
                FreeLibrary(PatcherModule);
                PatcherModule = nullptr;
                if (!FirstPatcherMissingLogged)
                {
                    FirstPatcherMissingLogged = true;
                    spdlog::warn(
                        "VR DXVK MULTIVIEW: SPIR-V patcher export missing; true multiview disabled");
                }
                return false;
            }

            spdlog::info(
                "VR DXVK MULTIVIEW: MPL SPIR-V patcher loaded; OutRun c64-c67 will be redirected to per-view constants only on verified programmable world shaders");
            return true;
        }

        bool SetSurfaceLayerUnlocked(
            IDirect3DSurface9* surface,
            std::uint32_t layer) noexcept
        {
            if (!surface || !Provider)
                return false;
            return SUCCEEDED(
                Provider->SetMultiviewSurfaceLayer(surface, layer));
        }

        bool BindColorLayerUnlocked(
            IDirect3DDevice9* device,
            std::uint32_t layer) noexcept
        {
            if (!device || !FrameTargetsReady || !LayeredColor ||
                !SetSurfaceLayerUnlocked(LayeredColor, layer))
                return false;

            InternalProviderScope scope;
            const HRESULT hr = device->SetRenderTarget(0, LayeredColor);
            if (SUCCEEDED(hr))
            {
                BoundLayer = layer;
                ++TargetBinds;
                return true;
            }
            return false;
        }

        bool BindDepthLayerUnlocked(
            IDirect3DDevice9* device,
            std::uint32_t layer) noexcept
        {
            if (!device || !FrameTargetsReady)
                return false;
            if (!LayeredDepth)
            {
                InternalProviderScope scope;
                return SUCCEEDED(device->SetDepthStencilSurface(nullptr));
            }
            if (!SetSurfaceLayerUnlocked(LayeredDepth, layer))
                return false;

            InternalProviderScope scope;
            const HRESULT hr = device->SetDepthStencilSurface(LayeredDepth);
            if (SUCCEEDED(hr))
            {
                ++TargetBinds;
                return true;
            }
            return false;
        }

        bool BindEyeLayerUnlocked(
            IDirect3DDevice9* device,
            std::uint32_t layer) noexcept
        {
            if (!BindColorLayerUnlocked(device, layer))
                return false;
            if (!BindDepthLayerUnlocked(device, layer))
                return false;
            BoundLayer = layer;
            return true;
        }

        std::uint32_t Align4(std::uint32_t value) noexcept
        {
            return (value + 3u) & ~3u;
        }

        ShaderPatch* EnsureShaderPatchUnlocked(
            IDirect3DDevice9* device,
            IDirect3DVertexShader9* original) noexcept
        {
            if (!device || !original || !Provider ||
                !ResolvePatcherUnlocked())
                return nullptr;

            if (auto it = ShaderPatches.find(original);
                it != ShaderPatches.end())
                return it->second.patched ? &it->second : nullptr;

            ++ShaderPatchAttempts;

            UINT byteCount = 0;
            if (FAILED(original->GetFunction(nullptr, &byteCount)) ||
                byteCount < sizeof(DWORD) * 2)
            {
                ++ShaderPatchFailures;
                return nullptr;
            }

            std::vector<DWORD> bytecode(
                (byteCount + sizeof(DWORD) - 1) / sizeof(DWORD));
            if (FAILED(original->GetFunction(
                    bytecode.data(), &byteCount)))
            {
                ++ShaderPatchFailures;
                return nullptr;
            }
            bytecode.resize(byteCount / sizeof(DWORD));
            if (bytecode.empty())
            {
                ++ShaderPatchFailures;
                return nullptr;
            }

            // Force DXVK to create a distinct shader object instead of resolving
            // the clone to its existing shader cache entry.
            if (bytecode.back() == 0x0000ffffu)
                bytecode.pop_back();
            bytecode.push_back(0x0000fffeu); // zero-length COMMENT
            bytecode.push_back(0x0000ffffu); // END

            IDirect3DVertexShader9* patched = nullptr;
            {
                InternalProviderScope scope;
                if (FAILED(device->CreateVertexShader(
                        bytecode.data(), &patched)) || !patched)
                {
                    ++ShaderPatchFailures;
                    return nullptr;
                }
            }

            std::uint32_t originalConstantCount = 0;
            if (FAILED(Provider->GetShaderConstantCount(
                    patched, &originalConstantCount)))
            {
                ReleaseCom(patched);
                ++ShaderPatchFailures;
                return nullptr;
            }

            std::uint32_t destinationRegister = Align4(
                std::max(originalConstantCount, MinimumPatchedRegister));
            if (destinationRegister < OutRunWvpRegister)
                destinationRegister = OutRunWvpRegister;
            if (destinationRegister + OutRunWvpVectors * 2 >
                MaxD3D9VsFloatConstants)
            {
                ReleaseCom(patched);
                ++ShaderPatchFailures;
                if (!FirstPatchFailureLogged)
                {
                    FirstPatchFailureLogged = true;
                    spdlog::warn(
                        "VR DXVK MULTIVIEW: shader needs {} constants; no safe room for two c64 matrices below D3D9's 256-float4 limit",
                        originalConstantCount);
                }
                return nullptr;
            }

            const std::uint32_t expandedCount =
                destinationRegister + OutRunWvpVectors * 2;
            if (FAILED(Provider->SetShaderConstantCount(
                    patched, expandedCount)))
            {
                ReleaseCom(patched);
                ++ShaderPatchFailures;
                return nullptr;
            }

            std::uint32_t spirvSize = 0;
            if (FAILED(Provider->GetSPIRVShaderCode(
                    patched, nullptr, &spirvSize)) ||
                spirvSize == 0)
            {
                ReleaseCom(patched);
                ++ShaderPatchFailures;
                return nullptr;
            }

            std::vector<std::uint32_t> spirv(spirvSize);
            if (FAILED(Provider->GetSPIRVShaderCode(
                    patched, spirv.data(), &spirvSize)) ||
                spirvSize == 0)
            {
                ReleaseCom(patched);
                ++ShaderPatchFailures;
                return nullptr;
            }
            spirv.resize(spirvSize);

            const std::uint32_t offset =
                destinationRegister - OutRunWvpRegister;
            std::uint32_t patchedSize = 0;
            if (ChangeSpirvMultiView(
                    spirv.data(),
                    static_cast<std::uint32_t>(spirv.size()),
                    nullptr,
                    &patchedSize,
                    OutRunWvpRegister,
                    offset,
                    1) != 0 ||
                patchedSize == 0)
            {
                ReleaseCom(patched);
                ++ShaderPatchFailures;
                return nullptr;
            }

            std::vector<std::uint32_t> patchedSpirv(patchedSize);
            if (ChangeSpirvMultiView(
                    spirv.data(),
                    static_cast<std::uint32_t>(spirv.size()),
                    patchedSpirv.data(),
                    &patchedSize,
                    OutRunWvpRegister,
                    offset,
                    1) != 0 ||
                patchedSize == 0 ||
                FAILED(Provider->PatchSPIRVToVertexShader(
                    patched, patchedSpirv.data(), patchedSize)))
            {
                ReleaseCom(patched);
                ++ShaderPatchFailures;
                if (!FirstPatchFailureLogged)
                {
                    FirstPatchFailureLogged = true;
                    spdlog::warn(
                        "VR DXVK MULTIVIEW: first OutRun c64 SPIR-V patch failed; that shader remains on validated two-pass");
                }
                return nullptr;
            }

            ShaderPatch cache{};
            cache.original = original;
            cache.original->AddRef();
            cache.patched = patched;
            cache.destinationRegister = destinationRegister;
            auto [it, inserted] = ShaderPatches.emplace(original, cache);
            if (!inserted)
            {
                cache.Reset();
                return it->second.patched ? &it->second : nullptr;
            }

            ++ShaderPatchSuccess;
            spdlog::info(
                "VR DXVK MULTIVIEW: patched verified OutRun VS c64-c67 -> c{}-c{} via BuiltIn ViewIndex; originalConstants={} expandedConstants={}",
                destinationRegister,
                destinationRegister + 7,
                originalConstantCount,
                expandedCount);
            return &it->second;
        }

        bool OutputPairMatchesUnlocked(
            IDirect3DSurface9* leftColor,
            IDirect3DSurface9* rightColor,
            IDirect3DSurface9* leftDepth,
            IDirect3DSurface9* rightDepth) noexcept
        {
            return FrameTargetsReady &&
                LogicalLeftColor == leftColor &&
                LogicalRightColor == rightColor &&
                LogicalLeftDepth == leftDepth &&
                LogicalRightDepth == rightDepth;
        }
    }

    bool IsInternalProviderCall() noexcept
    {
        return InternalProviderDepth != 0;
    }

    bool IsProviderAvailable(IDirect3DDevice9* device) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        return ResolveProviderUnlocked(device) != nullptr;
    }

    bool EnsureFrameTargets(
        IDirect3DDevice9* device,
        IDirect3DSurface9* leftColorTarget,
        IDirect3DSurface9* rightColorTarget,
        IDirect3DSurface9* leftDepthTarget,
        IDirect3DSurface9* rightDepthTarget) noexcept
    {
        if (!device || !leftColorTarget || !rightColorTarget)
            return false;

        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        if (!ResolveProviderUnlocked(device))
            return false;

        if (OutputPairMatchesUnlocked(
                leftColorTarget, rightColorTarget,
                leftDepthTarget, rightDepthTarget))
            return true;

        D3DSURFACE_DESC leftColorDesc{}, rightColorDesc{};
        if (!ReadDesc(leftColorTarget, leftColorDesc) ||
            !ReadDesc(rightColorTarget, rightColorDesc) ||
            !SameSurfaceDesc(leftColorDesc, rightColorDesc))
            return false;

        D3DSURFACE_DESC leftDepthDesc{}, rightDepthDesc{};
        if ((leftDepthTarget == nullptr) != (rightDepthTarget == nullptr))
            return false;
        if (leftDepthTarget)
        {
            if (!ReadDesc(leftDepthTarget, leftDepthDesc) ||
                !ReadDesc(rightDepthTarget, rightDepthDesc) ||
                !SameSurfaceDesc(leftDepthDesc, rightDepthDesc) ||
                leftDepthDesc.Width != leftColorDesc.Width ||
                leftDepthDesc.Height != leftColorDesc.Height ||
                leftDepthDesc.MultiSampleType != leftColorDesc.MultiSampleType ||
                leftDepthDesc.MultiSampleQuality !=
                    leftColorDesc.MultiSampleQuality)
                return false;
        }

        ReleaseFrameTargetsUnlocked();

        IDirect3DSurface9* layeredColor = nullptr;
        HRESULT hr = Provider->CreateMultiViewRenderTarget(
            leftColorDesc.Width,
            leftColorDesc.Height,
            leftColorDesc.Format,
            leftColorDesc.MultiSampleType,
            leftColorDesc.MultiSampleQuality,
            FALSE,
            &layeredColor,
            nullptr,
            2);
        if (FAILED(hr) || !layeredColor)
        {
            ++TargetCreateFailures;
            return false;
        }

        IDirect3DSurface9* layeredDepth = nullptr;
        if (leftDepthTarget)
        {
            hr = Provider->CreateMultiViewDepthStencilSurface(
                leftDepthDesc.Width,
                leftDepthDesc.Height,
                leftDepthDesc.Format,
                leftDepthDesc.MultiSampleType,
                leftDepthDesc.MultiSampleQuality,
                FALSE,
                &layeredDepth,
                nullptr,
                2);
            if (FAILED(hr) || !layeredDepth)
            {
                ReleaseCom(layeredColor);
                ++TargetCreateFailures;
                return false;
            }
        }

        LayeredColor = layeredColor;
        LayeredDepth = layeredDepth;
        LayeredColorDesc = leftColorDesc;
        LayeredDepthDesc = leftDepthDesc;
        ReplaceRef(LogicalLeftColor, leftColorTarget);
        ReplaceRef(LogicalRightColor, rightColorTarget);
        ReplaceRef(LogicalLeftDepth, leftDepthTarget);
        ReplaceRef(LogicalRightDepth, rightDepthTarget);
        FrameTargetsReady = true;
        BoundLayer = AllLayers;
        ++TargetCreates;

        if (!FirstTargetsLogged)
        {
            FirstTargetsLogged = true;
            spdlog::info(
                "VR DXVK MULTIVIEW: persistent 2-layer frame targets ready {}x{} colorFmt={} depthFmt={} msaa={}; world=1 draw, fallback passes=layered 2-pass, Present=layer copy",
                leftColorDesc.Width,
                leftColorDesc.Height,
                static_cast<int>(leftColorDesc.Format),
                leftDepthTarget ? static_cast<int>(leftDepthDesc.Format) : -1,
                static_cast<int>(leftColorDesc.MultiSampleType));
        }
        return true;
    }

    bool HasFrameTargets() noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        return FrameTargetsReady && LayeredColor != nullptr;
    }

    bool BindColorLayer(
        IDirect3DDevice9* device,
        std::uint32_t layer) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        return BindColorLayerUnlocked(device, layer);
    }

    bool BindDepthLayer(
        IDirect3DDevice9* device,
        std::uint32_t layer) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        return BindDepthLayerUnlocked(device, layer);
    }

    bool BindEyeLayer(
        IDirect3DDevice9* device,
        std::uint32_t layer) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        return BindEyeLayerUnlocked(device, layer);
    }

    bool FlushFrameTargets(
        IDirect3DDevice9* device,
        bool copyDepth) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        if (!device || !FrameTargetsReady || !Provider ||
            !LayeredColor || !LogicalLeftColor || !LogicalRightColor)
            return false;

        IDirect3DSurface9* colors[2] = {
            LogicalLeftColor, LogicalRightColor
        };
        HRESULT colorHr = Provider->CopySurfaceLayers(
            LayeredColor, colors, 2);
        HRESULT depthHr = D3D_OK;
        if (copyDepth && LayeredDepth &&
            LogicalLeftDepth && LogicalRightDepth)
        {
            IDirect3DSurface9* depths[2] = {
                LogicalLeftDepth, LogicalRightDepth
            };
            depthHr = Provider->CopySurfaceLayers(
                LayeredDepth, depths, 2);
        }

        {
            InternalProviderScope scope;
            if (LogicalLeftColor)
                device->SetRenderTarget(0, LogicalLeftColor);
            device->SetDepthStencilSurface(LogicalLeftDepth);
        }

        if (SUCCEEDED(colorHr) &&
            (!copyDepth || SUCCEEDED(depthHr)))
        {
            ++TargetFlushes;
            return true;
        }

        if (!FirstFlushFailureLogged)
        {
            FirstFlushFailureLogged = true;
            spdlog::warn(
                "VR DXVK MULTIVIEW: layered target flush failed color=0x{:08X} depth=0x{:08X}; current stereo frame will fail closed",
                static_cast<unsigned>(colorHr),
                static_cast<unsigned>(depthHr));
        }
        return false;
    }

    bool IsLogicalLeftColor(IDirect3DSurface9* surface) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        return FrameTargetsReady && surface &&
            surface == LogicalLeftColor;
    }

    bool IsLogicalLeftDepth(IDirect3DSurface9* surface) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        return FrameTargetsReady &&
            surface == LogicalLeftDepth;
    }

    bool TryArmWorldDraw(
        IDirect3DDevice9* device,
        IDirect3DSurface9* rightColorTarget,
        IDirect3DSurface9* rightDepthTarget,
        const float* leftWvp,
        const float* rightWvp,
        std::uint64_t poseSequence,
        std::uint64_t drawToken,
        std::uint32_t eligibilityFlags) noexcept
    {
        (void)drawToken;
        (void)eligibilityFlags;

        if (!BackendAllowsDxvk() || !device || !rightColorTarget ||
            !leftWvp || !rightWvp || poseSequence == 0)
            return false;

        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        ++ArmAttempts;

        if (!ResolveProviderUnlocked(device) ||
            !FrameTargetsReady ||
            rightColorTarget != LogicalRightColor ||
            rightDepthTarget != LogicalRightDepth)
        {
            ++ArmRejected;
            return false;
        }

        IDirect3DVertexShader9* original = nullptr;
        if (FAILED(device->GetVertexShader(&original)) || !original)
        {
            ++ArmRejected;
            return false;
        }

        ShaderPatch* patch = EnsureShaderPatchUnlocked(device, original);
        if (!patch)
        {
            original->Release();
            ++ArmRejected;
            return false;
        }

        bool ok = true;
        {
            InternalProviderScope scope;

            if (FAILED(Provider->EnableMultiView(true)))
                ok = false;

            if (ok && !SetSurfaceLayerUnlocked(LayeredColor, AllLayers))
                ok = false;
            if (ok && LayeredDepth &&
                !SetSurfaceLayerUnlocked(LayeredDepth, AllLayers))
                ok = false;

            if (ok && FAILED(device->SetRenderTarget(0, LayeredColor)))
                ok = false;
            if (ok && FAILED(device->SetDepthStencilSurface(LayeredDepth)))
                ok = false;
            if (ok && FAILED(device->SetVertexShader(patch->patched)))
                ok = false;
            if (ok && FAILED(device->SetVertexShaderConstantF(
                    patch->destinationRegister,
                    leftWvp,
                    OutRunWvpVectors)))
                ok = false;
            if (ok && FAILED(device->SetVertexShaderConstantF(
                    patch->destinationRegister + OutRunWvpVectors,
                    rightWvp,
                    OutRunWvpVectors)))
                ok = false;
        }

        if (!ok)
        {
            InternalProviderScope scope;
            device->SetVertexShader(original);
            Provider->EnableMultiView(false);
            SetSurfaceLayerUnlocked(LayeredColor, 0);
            if (LayeredDepth)
                SetSurfaceLayerUnlocked(LayeredDepth, 0);
            device->SetRenderTarget(0, LayeredColor);
            device->SetDepthStencilSurface(LayeredDepth);
            original->Release();
            ++ArmRejected;
            return false;
        }

        ReleaseCom(ArmedOriginalShader);
        ArmedOriginalShader = original;
        Armed = true;
        BoundLayer = AllLayers;
        ++ArmSuccess;
        ++ProviderDraws;
        return true;
    }

    void FinishArmedDraw(bool drawSucceeded) noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        if (!Armed)
            return;

        if (drawSucceeded)
            ++DrawSuccess;
        else
        {
            ++DrawFailure;
            ++Cancels;
        }

        if (CachedDevice && Provider)
        {
            InternalProviderScope scope;
            if (ArmedOriginalShader)
                CachedDevice->SetVertexShader(ArmedOriginalShader);
            Provider->EnableMultiView(false);

            if (FrameTargetsReady && LayeredColor)
            {
                SetSurfaceLayerUnlocked(LayeredColor, 0);
                if (LayeredDepth)
                    SetSurfaceLayerUnlocked(LayeredDepth, 0);
                CachedDevice->SetRenderTarget(0, LayeredColor);
                CachedDevice->SetDepthStencilSurface(LayeredDepth);
                BoundLayer = 0;
            }
        }

        ReleaseCom(ArmedOriginalShader);
        Armed = false;
    }

    void NoteTwoPassArrayDraw() noexcept
    {
        ++TwoPassArrayDraws;
    }

    void InvalidateFrameTargets() noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        if (Armed)
            FinishArmedDraw(false);
        ReleaseFrameTargetsUnlocked();
    }

    void InvalidateDevice() noexcept
    {
        std::lock_guard<std::recursive_mutex> lock(BridgeMutex);
        if (Armed)
            FinishArmedDraw(false);
        ReleaseProviderUnlocked();
    }

    Telemetry GetTelemetry() noexcept
    {
        Telemetry out{};
        out.armAttempts = ArmAttempts.load(std::memory_order_acquire);
        out.armSuccess = ArmSuccess.load(std::memory_order_acquire);
        out.armRejected = ArmRejected.load(std::memory_order_acquire);
        out.drawSuccess = DrawSuccess.load(std::memory_order_acquire);
        out.drawFailure = DrawFailure.load(std::memory_order_acquire);
        out.cancels = Cancels.load(std::memory_order_acquire);
        out.interfaceMisses = InterfaceMisses.load(std::memory_order_acquire);
        out.protocolMismatches =
            ProtocolMismatches.load(std::memory_order_acquire);
        out.capabilityMisses =
            CapabilityMisses.load(std::memory_order_acquire);
        out.targetCreates = TargetCreates.load(std::memory_order_acquire);
        out.targetCreateFailures =
            TargetCreateFailures.load(std::memory_order_acquire);
        out.targetBinds = TargetBinds.load(std::memory_order_acquire);
        out.targetFlushes = TargetFlushes.load(std::memory_order_acquire);
        out.shaderPatchAttempts =
            ShaderPatchAttempts.load(std::memory_order_acquire);
        out.shaderPatchSuccess =
            ShaderPatchSuccess.load(std::memory_order_acquire);
        out.shaderPatchFailures =
            ShaderPatchFailures.load(std::memory_order_acquire);
        out.providerDraws = ProviderDraws.load(std::memory_order_acquire);
        out.twoPassArrayDraws =
            TwoPassArrayDraws.load(std::memory_order_acquire);
        return out;
    }
}
