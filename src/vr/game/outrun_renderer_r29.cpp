// R29 renderer correctness overlay.
//
// R23/R28 widened the upload-time world path too far: once target/projection
// looked like perspective world it bypassed R13's fragile-effect policy, and a
// partial c64..c67 write could reuse rows observed in an older eligibility
// generation. R29 restores R13 as the authoritative classifier and makes the
// stock WVP shadow frame/generation local.
//
// Important policy:
//  * stock c64..c67 is tracked even while stereo eligibility is closed;
//  * a partial write first seeds all four current device rows, then applies the
//    incoming rows, so old rows can never be mixed into a new generation;
//  * every eligible WVP candidate flows through R13 again. Alpha-tested/two-
//    sided translucent effects therefore remain stock/zero-disparity;
//  * R28 projection snapshots are kept only when R13 actually accepted a
//    verified world WVP. No draw-time shader identity substitution is needed.

#include "outrun_renderer_r23.cpp"

namespace OutRunVRRenderer
{
    namespace
    {
        SafetyHookInline R29BeginSceneR23Hook{};
        SafetyHookInline R29WvpR23Hook{};
        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R29RendererInstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint64_t R29RawWvpGeneration = 1;
        std::uint64_t R29RawWvpSeeds = 0;
        std::uint64_t R29RawWvpSeedFailures = 0;
        std::uint64_t R29R13ClassifiedUploads = 0;
        std::uint64_t R29PartialFullRebuilds = 0;
        bool R29FirstSeedLogged = false;
        bool R29FirstR13RestoreLogged = false;

        void R29InvalidateRawWvpGenerationImpl() noexcept
        {
            std::memset(R28RawWvp, 0, sizeof(R28RawWvp));
            R28RawWvpMask = 0;
            R28InvalidateProjectionSnapshot();
            if (++R29RawWvpGeneration == 0)
                ++R29RawWvpGeneration;
        }

        bool R29SeedCurrentStockWvp(IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return false;

            float current[16]{};
            if (FAILED(device->GetVertexShaderConstantF(
                    OutRunWvpRegister, current, OutRunWvpRegisterCount)))
            {
                ++R29RawWvpSeedFailures;
                R28RawWvpMask = 0;
                R28InvalidateProjectionSnapshot();
                return false;
            }

            std::memcpy(R28RawWvp, current, sizeof(R28RawWvp));
            R28RawWvpMask = 0x0Fu;
            ++R29RawWvpSeeds;
            if (!R29FirstSeedLogged)
            {
                R29FirstSeedLogged = true;
                spdlog::info(
                    "VR R29 WVP: first partial c64..c67 write seeds the complete current device block before rebuilding; stale cross-generation rows are forbidden");
            }
            return true;
        }

        HRESULT __stdcall BeginSceneDestR29(IDirect3DDevice9* device)
        {
            // BeginScene is the cheapest authoritative generation boundary we
            // already have on the render thread. Never carry a raw-row mask
            // across frames/stages/recovery transitions.
            if (IsGameDevice(device) &&
                !OutRunVRStereo::IsInternalStereoPassActive())
            {
                R29InvalidateRawWvpGenerationImpl();
            }
            return R29BeginSceneR23Hook.stdcall<HRESULT>(device);
        }

        HRESULT __stdcall SetVertexShaderConstantFDestR29(
            IDirect3DDevice9* device, UINT startRegister,
            const float* constantData, UINT vector4fCount)
        {
            // Preserve R23's render-thread cleanup before inspecting eligibility.
            R23ServiceRenderThreadCleanup();

            const bool candidateWvp = IsGameDevice(device) && constantData &&
                !OutRunVRStereo::IsInternalStereoPassActive() &&
                UploadTouchesOutRunWvp(startRegister, vector4fCount);
            if (!candidateWvp)
            {
                return R29WvpR23Hook.stdcall<HRESULT>(
                    device, startRegister, constantData, vector4fCount);
            }

            const bool partialWvp =
                !UploadContainsOutRunWvp(startRegister, vector4fCount);

            // This deliberately happens BEFORE the R23 eligibility gate. The
            // old implementation returned early while closed and silently lost
            // stock row updates, leaving an old 0xF mask reusable later.
            if (partialWvp && !R28RawWvpComplete())
                R29SeedCurrentStockWvp(device);
            R28TrackRawWvpWrite(startRegister, constantData, vector4fCount);

            // During installation/recovery retain all R23 bookkeeping and its
            // stock-visible warmup policy. Because R29 pre-tracked the write,
            // R23 can no longer resurrect rows from an earlier generation.
            if (!R23WvpEligibilityReady.load(std::memory_order_acquire) ||
                !OutRunVR::RuntimeEligibility::MayInjectStereo())
            {
                const HRESULT hr = R29WvpR23Hook.stdcall<HRESULT>(
                    device, startRegister, constantData, vector4fCount);
                if (SUCCEEDED(hr) && partialWvp && R28RawWvpComplete() &&
                    !OutRunVR::RuntimeEligibility::MayInjectStereo())
                {
                    // Make recovery/warmup coherent even if only one row was
                    // written after a previously head-patched device state.
                    return R28RestoreStockWvp(device);
                }
                return hr;
            }

            // R13 is again the only authority for an eligible c64 upload. This
            // removes R27's "perspective means world regardless of alpha/cull"
            // shortcut. Fragile shadow/billboard/cutout passes are invalidated
            // and written stock by R13; only verified world WVPs survive.
            HRESULT hr = D3D_OK;
            if (partialWvp)
            {
                if (!R28RawWvpComplete())
                {
                    InvalidateVerifiedWvp();
                    R28InvalidateProjectionSnapshot();
                    return R23WvpEligibilityHook.stdcall<HRESULT>(
                        device, startRegister, constantData, vector4fCount);
                }

                hr = R23WvpEligibilityHook.stdcall<HRESULT>(
                    device, OutRunWvpRegister, R28RawWvp,
                    OutRunWvpRegisterCount);
                if (SUCCEEDED(hr))
                    ++R29PartialFullRebuilds;
            }
            else
            {
                hr = R23WvpEligibilityHook.stdcall<HRESULT>(
                    device, startRegister, constantData, vector4fCount);
            }

            ++R29R13ClassifiedUploads;
            if (SUCCEEDED(hr))
                R28CaptureVerifiedProjection();
            else
                R28InvalidateProjectionSnapshot();

            if (!R29FirstR13RestoreLogged)
            {
                R29FirstR13RestoreLogged = true;
                spdlog::info(
                    "VR R29 EFFECT: eligible WVP uploads restored to R13 classification; fragile alpha/billboard/shadow passes are no longer promoted merely because projection is perspective");
            }
            return hr;
        }

        void R29RollbackRendererHooks() noexcept
        {
            R29WvpR23Hook = {};
            R29BeginSceneR23Hook = {};
        }

        bool R29EnableRendererHooks() noexcept
        {
            SafetyHookInline* hooks[]{ &R29BeginSceneR23Hook, &R29WvpR23Hook };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R29RendererInstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R29RendererInstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r23 = R23RendererInstallState.load(std::memory_order_acquire);
                if (r23 == State::Failed)
                {
                    R29RendererInstallState.store(State::Failed, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRRendererR29", false);
                    spdlog::error(
                        "VR R29 RENDERER: R23 prerequisite failed; conservative WVP overlay not installed");
                    return 0;
                }

                if (r23 == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R29BeginSceneR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&BeginSceneDestR23),
                        BeginSceneDestR29, disabled);
                    R29WvpR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&SetVertexShaderConstantFDestR23),
                        SetVertexShaderConstantFDestR29, disabled);

                    if (!R29EnableRendererHooks())
                    {
                        R29RollbackRendererHooks();
                        R29RendererInstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult("OpenXRVRRendererR29", false);
                        spdlog::error(
                            "VR R29 RENDERER: disabled-first transaction failed; R23 remains authoritative");
                        return 0;
                    }

                    R29RendererInstallState.store(State::Ready,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRRendererR29", true);
                    spdlog::info(
                        "VR R29 RENDERER: generation-local stock WVP shadow + R13 fragile-effect authority ACTIVE");
                    return 0;
                }
                Sleep(25);
            }

            R29RendererInstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRRendererR29", false);
            spdlog::error(
                "VR R29 RENDERER: timed out waiting for R23; R23 remains active");
            return 0;
        }

        class VRRendererR29Hook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRRendererR29";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R29RendererInstallState.store(State::Pending,
                    std::memory_order_release);
                HANDLE thread = CreateThread(nullptr, 0,
                    R29RendererInstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R29RendererInstallState.store(State::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRRendererR29Hook instance;
        };

        VRRendererR29Hook VRRendererR29Hook::instance;
    }

    void R29InvalidateRawWvpGeneration() noexcept
    {
        R29InvalidateRawWvpGenerationImpl();
    }
}
