// R30 screen-space asymmetric-FOV correction overlay.
//
// R29 restores conservative world/effect classification and removes the steady-
// state third mono draw. R30 fixes the remaining HUD convergence problem without
// moving the world image: only main-backbuffer orthographic/ScreenSpace2D draws
// receive an eye-specific clip-space X affine. The affine maps one common
// head-relative tangent-angle interval into each eye's actual asymmetric OpenXR
// FOV, so the same HUD feature lands on the same visual ray in both eyes.
//
// This is intentionally an interim projection-layer HUD solution. It does not
// pretend to be XrCompositionLayerQuad: perspective world draws and fragile
// perspective effects remain entirely owned by R29/R13.

#include "stereo_renderer_r29.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R30DrawPrimitiveR29Hook{};
        SafetyHookInline R30DrawIndexedPrimitiveR29Hook{};
        SafetyHookInline R30DrawPrimitiveUPR29Hook{};
        SafetyHookInline R30DrawIndexedPrimitiveUPR29Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R30InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint64_t R30ScreenSpaceFovDraws = 0;
        std::uint64_t R30ScreenSpaceFallbacks = 0;
        std::uint64_t R30ScreenSpaceBuildFailures = 0;
        bool R30FirstScreenSpaceLogged = false;

        bool R30CurrentPassIsScreenSpace2D() noexcept
        {
            if (!TargetIsBackBuffer())
                return false;

            float projection[16]{};
            if (!OutRunVRRenderer::GetRendererBaseProjection(projection))
                return false;

            const auto projectionClass =
                OutRunVR::PassPolicy::ClassifyProjectionSignature(
                    projection[11], projection[15]);
            return projectionClass ==
                OutRunVR::PassPolicy::ProjectionClass::Orthographic2D;
        }

        bool R30BuildScreenSpaceEyeConstants(
            IDirect3DDevice9* device,
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            float original[16], float eyeConstants[2][16],
            float eyeScale[2], float eyeOffset[2]) noexcept
        {
            if (!device ||
                CurrentVertexShaderIdentity.load(std::memory_order_acquire) == 0)
                return false;

            if (FAILED(device->GetVertexShaderConstantF(
                    OutRunWvpRegister, original, OutRunWvpRegisterCount)))
                return false;

            float tanLeft[2]{};
            float tanRight[2]{};
            float width[2]{};
            for (int eye = 0; eye < 2; ++eye)
            {
                tanLeft[eye] = std::tan(stereo.eyeFov[eye].angleLeft);
                tanRight[eye] = std::tan(stereo.eyeFov[eye].angleRight);
                width[eye] = tanRight[eye] - tanLeft[eye];
                if (!std::isfinite(tanLeft[eye]) ||
                    !std::isfinite(tanRight[eye]) ||
                    !std::isfinite(width[eye]) || width[eye] <= 0.05f)
                    return false;
            }

            // Average the two physical eye frusta in tangent space. For a Quest
            // style outward-biased pair this produces a head-centered frustum.
            // Mapping each eye from that common interval removes the false HUD
            // disparity caused by submitting identical pixels with asymmetric
            // projection FOVs.
            const float commonLeft = 0.5f * (tanLeft[0] + tanLeft[1]);
            const float commonRight = 0.5f * (tanRight[0] + tanRight[1]);
            const float commonWidth = commonRight - commonLeft;
            const float commonSum = commonRight + commonLeft;
            if (!std::isfinite(commonWidth) || commonWidth <= 0.05f)
                return false;

            D3DMATRIX uploadedT{};
            std::memcpy(&uploadedT, original, sizeof(uploadedT));
            const D3DMATRIX stockWvp = TransposeMatrix(uploadedT);
            if (!MatrixFinite(stockWvp))
                return false;

            for (int eye = 0; eye < 2; ++eye)
            {
                const float eyeSum = tanRight[eye] + tanLeft[eye];
                const float scale = commonWidth / width[eye];
                const float offset = (commonSum - eyeSum) / width[eye];

                // These bounds are deliberately broad enough for Quest-class
                // asymmetric frusta but fail closed on corrupt/stale FOV data.
                if (!std::isfinite(scale) || !std::isfinite(offset) ||
                    scale < 0.50f || scale > 1.50f ||
                    std::fabs(offset) > 0.50f)
                    return false;

                D3DMATRIX clipCorrection{};
                clipCorrection._11 = scale;
                clipCorrection._22 = 1.0f;
                clipCorrection._33 = 1.0f;
                clipCorrection._44 = 1.0f;
                // Row-vector clip transform: x' = scale*x + offset*w.
                clipCorrection._41 = offset;

                const D3DMATRIX corrected =
                    MultiplyMatrix(stockWvp, clipCorrection);
                if (!MatrixFinite(corrected))
                    return false;

                const D3DMATRIX correctedT = TransposeMatrix(corrected);
                std::memcpy(eyeConstants[eye], &correctedT,
                    sizeof(correctedT));
                eyeScale[eye] = scale;
                eyeOffset[eye] = offset;
            }
            return true;
        }

        template <typename ActualDraw>
        HRESULT R30TryScreenSpaceFovDraw(
            IDirect3DDevice9* device, ActualDraw&& actualDraw,
            const char* site)
        {
            if (!R29StableStereoBase(device) ||
                !R30CurrentPassIsScreenSpace2D())
                return E_NOTIMPL;

            if (!EnsureStereoResources(device))
                return E_NOTIMPL;

            if (TrackedDepthStencil &&
                (!RightDepthSynchronized || !RightStencilSynchronized))
                TryBootstrapRightDepthFromRecentClear(device);
            if (TrackedDepthStencil && !RightDepthSynchronized &&
                DepthTestActive(device))
                return E_NOTIMPL;
            if (TrackedDepthStencil && !RightStencilSynchronized &&
                StencilTestActive(device))
                return E_NOTIMPL;

            OutRunVRRenderer::LatchedStereoFrame stereo{};
            if (!OutRunVRRenderer::GetLatchedStereoFrame(stereo) ||
                stereo.poseSequence == 0)
                return E_NOTIMPL;

            // If perspective world geometry already established this Present's
            // pose sequence, screen-space correction must use that exact packet.
            if (FrameStereoPoseSequence != 0 &&
                FrameStereoPoseSequence != stereo.poseSequence)
                return E_NOTIMPL;

            float original[16]{};
            float eyeConstants[2][16]{};
            float eyeScale[2]{};
            float eyeOffset[2]{};
            if (!R30BuildScreenSpaceEyeConstants(device, stereo,
                    original, eyeConstants, eyeScale, eyeOffset))
            {
                ++R30ScreenSpaceBuildFailures;
                return E_NOTIMPL;
            }

            D3DVIEWPORT9 savedViewport{};
            if (FAILED(device->GetViewport(&savedViewport)))
                return E_NOTIMPL;

            // From this point the draw is owned by R30. The steady-state frame
            // intentionally has no complete independent mono history.
            ++R9DrawCalls;
            R9MonoBackupGap = true;
            if (LeftDrawMayWriteDepth(device) ||
                LeftDrawMayWriteStencil(device))
                ++R9MainDepthContentSerial;

            bool leftWvpOk = false;
            {
                InternalPassScope guard;
                leftWvpOk = SetWvpOneRegisterAtATime(
                    device, eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool restored = false;
                {
                    InternalPassScope guard;
                    restored = SetWvpOneRegisterAtATime(device, original);
                }
                if (!restored)
                {
                    R9Poison(OutRunVR::StereoFailureRestoreFailed,
                        "R30/HUD-left-WVP-rollback");
                    R29ArmMonoSafety();
                    return E_FAIL;
                }
                --R9DrawCalls;
                return E_NOTIMPL;
            }

            const HRESULT leftHr = actualDraw();
            if (FAILED(leftHr))
            {
                bool restored = false;
                {
                    InternalPassScope guard;
                    restored = SetWvpOneRegisterAtATime(device, original);
                }
                R9Poison(OutRunVR::StereoFailureLeftDrawFailed,
                    site, leftHr);
                if (!restored)
                    NoteRestoreFailure("R30 HUD left draw c64");
                R29ArmMonoSafety();
                return leftHr;
            }

            IDirect3DSurface9* savedRt = TrackedRenderTarget;
            IDirect3DSurface9* savedDepth = TrackedDepthStencil;
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                InternalPassScope guard;
                rightHr = SetRenderTargetHook.stdcall<HRESULT>(
                    device, 0u, RightEyeSurface);
                if (SUCCEEDED(rightHr))
                {
                    rightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(
                        device, TrackedDepthStencil ? RightEyeDepth : nullptr);
                }
                if (SUCCEEDED(rightHr))
                    rightHr = device->SetViewport(&savedViewport);
                if (SUCCEEDED(rightHr) &&
                    !SetWvpOneRegisterAtATime(device, eyeConstants[1]))
                {
                    rightFailure =
                        OutRunVR::StereoFailureRightWvpUploadFailed;
                    rightHr = E_FAIL;
                }
                if (SUCCEEDED(rightHr))
                {
                    rightFailure = OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = actualDraw();
                }
                restoreOk = RestoreRightPassState(device, savedRt, savedDepth,
                    savedViewport, original, true);
            }

            FrameHadDuplicatedDraw = true;
            ++DuplicatedDraws;
            ++NonWorldDuplicatedDraws;
            ++R29StableTwoEyeDraws;
            ++R30ScreenSpaceFovDraws;

            if (!R30FirstScreenSpaceLogged)
            {
                R30FirstScreenSpaceLogged = true;
                spdlog::info(
                    "VR R30 HUD: orthographic ScreenSpace2D asymmetric-FOV correction ACTIVE scale[L/R]={:.4f}/{:.4f} offset[L/R]={:.4f}/{:.4f}; world/effect passes unchanged",
                    eyeScale[0], eyeScale[1], eyeOffset[0], eyeOffset[1]);
            }

            if (FAILED(rightHr))
            {
                FrameRightDrawFailed = true;
                InvalidateRightDepthStencilIfLeftMayWrite(device);
                R9Poison(rightFailure, site, rightHr);
                R29ArmMonoSafety();
            }
            if (!restoreOk)
            {
                InvalidateRightDepthStencilIfLeftMayWrite(device);
                NoteRestoreFailure("R30 HUD right-eye draw");
                R29ArmMonoSafety();
            }
            return leftHr;
        }

        template <typename ActualDraw, typename R29Draw>
        HRESULT R30GuardScreenSpace(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, R29Draw&& r29Draw,
            const char* site)
        {
            const HRESULT hr = R30TryScreenSpaceFovDraw(
                device, std::forward<ActualDraw>(actualDraw), site);
            if (hr != E_NOTIMPL)
                return hr;
            ++R30ScreenSpaceFallbacks;
            return r29Draw();
        }

        HRESULT __stdcall DrawPrimitiveDestR30(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto r29 = [&]() {
                return R30DrawPrimitiveR29Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR30(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto r29 = [&]() {
                return R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR30(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT primitiveCount, const void* data, UINT stride)
        {
            auto actual = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto r29 = [&]() {
                return R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR30(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            auto r29 = [&]() {
                return R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>(device,
                    type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawIndexedPrimitiveUP");
        }

        void R30RollbackHooks() noexcept
        {
            R30DrawIndexedPrimitiveUPR29Hook = {};
            R30DrawPrimitiveUPR29Hook = {};
            R30DrawIndexedPrimitiveR29Hook = {};
            R30DrawPrimitiveR29Hook = {};
        }

        bool R30EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R30DrawPrimitiveR29Hook,
                &R30DrawIndexedPrimitiveR29Hook,
                &R30DrawPrimitiveUPR29Hook,
                &R30DrawIndexedPrimitiveUPR29Hook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R30InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R30InstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r29 = R29StereoInstallState.load(
                    std::memory_order_acquire);
                if (r29 == State::Failed)
                {
                    R30InstallState.store(State::Failed,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR30HUD", false);
                    spdlog::error(
                        "VR R30 HUD: R29 prerequisite failed; R29 remains active without screen-space FOV correction");
                    return 0;
                }

                if (r29 == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R30DrawPrimitiveR29Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR29),
                        DrawPrimitiveDestR30, disabled);
                    R30DrawIndexedPrimitiveR29Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR29),
                        DrawIndexedPrimitiveDestR30, disabled);
                    R30DrawPrimitiveUPR29Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR29),
                        DrawPrimitiveUPDestR30, disabled);
                    R30DrawIndexedPrimitiveUPR29Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR29),
                        DrawIndexedPrimitiveUPDestR30, disabled);

                    if (!R30EnableHooks())
                    {
                        R30RollbackHooks();
                        R30InstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult(
                            "OpenXRVRStereoR30HUD", false);
                        spdlog::error(
                            "VR R30 HUD: disabled-first hook transaction failed; R29 remains active");
                        return 0;
                    }

                    R30InstallState.store(State::Ready,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR30HUD", true);
                    spdlog::info(
                        "VR R30 HUD: ScreenSpace2D asymmetric-FOV correction overlay READY");
                    return 0;
                }
                Sleep(25);
            }

            R30InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRStereoR30HUD", false);
            spdlog::error(
                "VR R30 HUD: timed out waiting for R29; R29 remains active");
            return 0;
        }

        class VRStereoR30HudHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR30HUD";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R30InstallState.store(State::Pending,
                    std::memory_order_release);
                HANDLE thread = CreateThread(nullptr, 0,
                    R30InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R30InstallState.store(State::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR30HudHook instance;
        };

        VRStereoR30HudHook VRStereoR30HudHook::instance;
    }
}
