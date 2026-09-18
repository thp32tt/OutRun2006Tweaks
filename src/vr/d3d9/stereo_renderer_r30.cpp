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
#include <vector>

namespace Settings
{
    extern Setting<float> VRHudScale;
}

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

        std::uint64_t R30XyzrhwHudDraws = 0;
        std::uint64_t R30XyzrhwWorldEffectDraws = 0;
        std::uint64_t R30XyzrhwRhwWorldPromotions = 0;
        std::uint64_t R30XyzrhwFallbacks = 0;
        bool R30FirstXyzrhwHudLogged = false;
        bool R30FirstXyzrhwWorldLogged = false;
        bool R30FirstXyzrhwRhwPromotionLogged = false;

        // User-adjustable projection-space HUD scale. The per-eye FOV affine
        // remains automatic; this value is only a common-centre size trim after
        // the headset-specific mapping.
        float R30HudScaleValue() noexcept
        {
            return std::clamp(Settings::VRHudScale.get(), 0.30f, 1.20f);
        }

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


        bool R30BuildEyeAffine(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            float eyeScale[2], float eyeOffset[2]) noexcept
        {
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

            const float commonLeft = 0.5f * (tanLeft[0] + tanLeft[1]);
            const float commonRight = 0.5f * (tanRight[0] + tanRight[1]);
            const float commonWidth = commonRight - commonLeft;
            const float commonSum = commonRight + commonLeft;
            if (!std::isfinite(commonWidth) || commonWidth <= 0.05f)
                return false;

            for (int eye = 0; eye < 2; ++eye)
            {
                const float eyeSum = tanRight[eye] + tanLeft[eye];
                const float scale = commonWidth / width[eye];
                const float offset = (commonSum - eyeSum) / width[eye];
                if (!std::isfinite(scale) || !std::isfinite(offset) ||
                    scale < 0.50f || scale > 1.50f ||
                    std::fabs(offset) > 0.50f)
                    return false;
                eyeScale[eye] = scale;
                eyeOffset[eye] = offset;
            }
            return true;
        }

        struct R30XyzrhwState
        {
            OutRunVRRenderer::LatchedStereoFrame stereo{};
            D3DVIEWPORT9 viewport{};
            float eyeScale[2]{};
            float eyeOffset[2]{};
            float worldScaleX[2]{};
            float worldOffsetX[2]{};
            float worldScaleY[2]{};
            float worldOffsetY[2]{};
            float parallaxPerRhwX[2]{};
            float parallaxPerRhwY[2]{};
            D3DMATRIX inverseBaseProjection{};
            D3DMATRIX eyeProjection[2]{};
            float eyeLocalTranslation[2][3]{};
            bool fullWorldReprojection = false;
            bool depthTestEnabled = false;
            bool rhwDepthEvidence = false;
            bool worldEffect = false;
        };

        bool R30PrepareXyzrhwState(
            IDirect3DDevice9* device, R30XyzrhwState& state) noexcept
        {
            if (!R29StableStereoBase(device) ||
                CurrentVertexShaderIdentity.load(std::memory_order_acquire) != 0)
                return false;

            IDirect3DVertexShader9* shader = nullptr;
            if (FAILED(device->GetVertexShader(&shader)))
                return false;
            if (shader)
            {
                shader->Release();
                return false;
            }

            DWORD fvf = 0;
            if (FAILED(device->GetFVF(&fvf)) ||
                (fvf & D3DFVF_POSITION_MASK) != D3DFVF_XYZRHW)
                return false;

            if (!EnsureStereoResources(device) ||
                FAILED(device->GetViewport(&state.viewport)) ||
                state.viewport.Width == 0)
                return false;

            DWORD zEnable = D3DZB_FALSE;
            if (FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable)))
                return false;
            state.depthTestEnabled = zEnable != D3DZB_FALSE;

            if (!OutRunVRRenderer::GetLatchedStereoFrame(state.stereo) ||
                state.stereo.poseSequence == 0 ||
                (FrameStereoPoseSequence != 0 &&
                 FrameStereoPoseSequence != state.stereo.poseSequence) ||
                !R30BuildEyeAffine(state.stereo,
                    state.eyeScale, state.eyeOffset))
                return false;

            return true;
        }

        bool R30XyzrhwHasProjectedDepthSignature(
            const void* source, UINT vertexCount, UINT stride) noexcept
        {
            if (!source || vertexCount == 0 || stride < sizeof(float) * 4)
                return false;

            // UI quads in OutRun normally carry RHW=1. CPU-projected world
            // particles/decals carry 1/clip-W, often even when Z testing is
            // disabled for blending or to avoid decal z-fighting. Use that
            // pre-transformed depth evidence as an additional world-space
            // signal rather than relying on D3DRS_ZENABLE alone.
            const UINT sampleCount = std::min<UINT>(vertexCount, 512u);
            UINT valid = 0;
            UINT projected = 0;
            for (UINT i = 0; i < sampleCount; ++i)
            {
                const float* p = reinterpret_cast<const float*>(
                    static_cast<const std::uint8_t*>(source) +
                    static_cast<std::size_t>(i) * stride);
                const float z = p[2];
                const float rhw = p[3];
                if (!std::isfinite(z) || !std::isfinite(rhw) ||
                    rhw <= 0.0f || rhw >= 1000.0f)
                    continue;

                ++valid;
                if (z >= -0.10f && z <= 1.10f &&
                    std::fabs(rhw - 1.0f) > 0.02f)
                    ++projected;
            }

            return valid != 0 && projected * 4u >= valid * 3u;
        }

        bool R30ConfigureXyzrhwWorldEffect(
            IDirect3DDevice9* device, const void* source,
            UINT vertexCount, UINT stride, R30XyzrhwState& state) noexcept
        {
            state.rhwDepthEvidence =
                R30XyzrhwHasProjectedDepthSignature(
                    source, vertexCount, stride);

            // Preserve the validated R30.1 depth-tested path, but also promote
            // depth-disabled CPU-projected particles/decals when RHW proves
            // that the vertices came from a 3D projection.
            state.worldEffect =
                state.depthTestEnabled || state.rhwDepthEvidence;
            if (!state.worldEffect)
                return true;

            if (TrackedDepthStencil &&
                (!RightDepthSynchronized || !RightStencilSynchronized))
                TryBootstrapRightDepthFromRecentClear(device);
            if (TrackedDepthStencil &&
                !RightDepthSynchronized && DepthTestActive(device))
                return false;
            if (TrackedDepthStencil &&
                !RightStencilSynchronized && StencilTestActive(device))
                return false;

            float projectionRaw[16]{};
            if (!OutRunVRRenderer::GetRendererBaseProjection(projectionRaw))
                return false;
            D3DMATRIX baseProjection{};
            std::memcpy(&baseProjection, projectionRaw, sizeof(baseProjection));
            if (!MatrixFinite(baseProjection) ||
                std::fabs(baseProjection._11) < 0.01f ||
                std::fabs(baseProjection._22) < 0.01f ||
                std::fabs(baseProjection._34) < 0.25f ||
                !InvertMatrix(baseProjection, state.inverseBaseProjection) ||
                !MatrixFinite(state.inverseBaseProjection))
                return false;
            state.fullWorldReprojection = true;

            const float center[3]{
                0.5f * (state.stereo.eyeOffset[0][0] + state.stereo.eyeOffset[1][0]),
                0.5f * (state.stereo.eyeOffset[0][1] + state.stereo.eyeOffset[1][1]),
                0.5f * (state.stereo.eyeOffset[0][2] + state.stereo.eyeOffset[1][2])
            };
            const float zero[3]{};
            for (int eye = 0; eye < 2; ++eye)
            {
                const float rel[3]{
                    state.stereo.eyeOffset[eye][0] - center[0],
                    state.stereo.eyeOffset[eye][1] - center[1],
                    state.stereo.eyeOffset[eye][2] - center[2]
                };
                const D3DMATRIX eyeRotation =
                    MatrixFromQuaternionTranslation(
                        state.stereo.eyeOrientation[eye], zero, 1.0f);
                const D3DMATRIX inverseEyeRotation =
                    InverseRigid(eyeRotation);
                const float localX =
                    rel[0] * inverseEyeRotation._11 +
                    rel[1] * inverseEyeRotation._21 +
                    rel[2] * inverseEyeRotation._31;
                const float localY =
                    rel[0] * inverseEyeRotation._12 +
                    rel[1] * inverseEyeRotation._22 +
                    rel[2] * inverseEyeRotation._32;
                const float localZ =
                    rel[0] * inverseEyeRotation._13 +
                    rel[1] * inverseEyeRotation._23 +
                    rel[2] * inverseEyeRotation._33;
                const D3DMATRIX eyeProjection =
                    ProjectionFromFov(baseProjection,
                        state.stereo.eyeFov[eye]);
                state.eyeProjection[eye] = eyeProjection;
                state.eyeLocalTranslation[eye][0] =
                    localX * Settings::VRWorldScale;
                state.eyeLocalTranslation[eye][1] =
                    localY * Settings::VRWorldScale;
                state.eyeLocalTranslation[eye][2] =
                    localZ * Settings::VRWorldScale;

                // XYZRHW world effects were projected by the game's original
                // camera/FOV before reaching D3D9. Mapping only the OpenXR
                // left/right asymmetry (R30.2) leaves smoke, skid decals and
                // world rank billboards in the wrong ray whenever the game FOV
                // differs from the HMD FOV. Reconstruct the projected ray from
                // the game's projection coefficients, then map that ray into
                // the real per-eye OpenXR projection. RHW supplies 1/clip-W for
                // the remaining eye-translation parallax term.
                state.worldScaleX[eye] =
                    eyeProjection._11 / baseProjection._11;
                state.worldOffsetX[eye] =
                    (eyeProjection._31 -
                     baseProjection._31 * state.worldScaleX[eye]) /
                    baseProjection._34;
                state.worldScaleY[eye] =
                    eyeProjection._22 / baseProjection._22;
                state.worldOffsetY[eye] =
                    (eyeProjection._32 -
                     baseProjection._32 * state.worldScaleY[eye]) /
                    baseProjection._34;
                state.parallaxPerRhwX[eye] =
                    -localX * Settings::VRWorldScale *
                    eyeProjection._11;
                state.parallaxPerRhwY[eye] =
                    -localY * Settings::VRWorldScale *
                    eyeProjection._22;

                if (!std::isfinite(state.worldScaleX[eye]) ||
                    !std::isfinite(state.worldOffsetX[eye]) ||
                    !std::isfinite(state.worldScaleY[eye]) ||
                    !std::isfinite(state.worldOffsetY[eye]) ||
                    !std::isfinite(state.parallaxPerRhwX[eye]) ||
                    !std::isfinite(state.parallaxPerRhwY[eye]) ||
                    !MatrixFinite(state.eyeProjection[eye]) ||
                    !std::isfinite(state.eyeLocalTranslation[eye][0]) ||
                    !std::isfinite(state.eyeLocalTranslation[eye][1]) ||
                    !std::isfinite(state.eyeLocalTranslation[eye][2]) ||
                    state.worldScaleX[eye] < 0.20f ||
                    state.worldScaleX[eye] > 5.0f ||
                    state.worldScaleY[eye] < 0.20f ||
                    state.worldScaleY[eye] > 5.0f)
                    return false;
            }

            if (state.rhwDepthEvidence && !state.depthTestEnabled)
            {
                ++R30XyzrhwRhwWorldPromotions;
                if (!R30FirstXyzrhwRhwPromotionLogged)
                {
                    R30FirstXyzrhwRhwPromotionLogged = true;
                    spdlog::info(
                        "VR R30.3 XYZRHW WORLD: RHW depth signature promoted a depth-disabled pre-transformed particle/decal to game-FOV -> OpenXR-FOV spatial stereo");
                }
            }
            return true;
        }

        UINT R30PrimitiveElementCount(
            D3DPRIMITIVETYPE type, UINT primitiveCount) noexcept
        {
            switch (type)
            {
            case D3DPT_POINTLIST: return primitiveCount;
            case D3DPT_LINELIST: return primitiveCount * 2u;
            case D3DPT_LINESTRIP: return primitiveCount + 1u;
            case D3DPT_TRIANGLELIST: return primitiveCount * 3u;
            case D3DPT_TRIANGLESTRIP:
            case D3DPT_TRIANGLEFAN: return primitiveCount + 2u;
            default: return 0;
            }
        }

        bool R30TransformXyzrhwVertices(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state, int eye,
            std::vector<std::uint8_t>& out) noexcept
        {
            if (!source || vertexCount == 0 || stride < sizeof(float) * 4 ||
                eye < 0 || eye > 1)
                return false;
            const std::size_t bytes =
                static_cast<std::size_t>(vertexCount) * stride;
            if (bytes == 0 || bytes > 4u * 1024u * 1024u)
                return false;

            try
            {
                out.resize(bytes);
            }
            catch (...)
            {
                return false;
            }
            std::memcpy(out.data(), source, bytes);

            const float x0 = static_cast<float>(state.viewport.X);
            const float y0 = static_cast<float>(state.viewport.Y);
            const float width = static_cast<float>(state.viewport.Width);
            const float height = static_cast<float>(state.viewport.Height);
            if (height <= 0.0f)
                return false;

            for (UINT i = 0; i < vertexCount; ++i)
            {
                float* p = reinterpret_cast<float*>(
                    out.data() + static_cast<std::size_t>(i) * stride);
                const float x = p[0];
                const float y = p[1];
                const float z = p[2];
                const float rhw = p[3];
                if (!std::isfinite(x) || !std::isfinite(y) ||
                    !std::isfinite(z) || !std::isfinite(rhw))
                    return false;

                const float ndcX = ((x - x0) / width) * 2.0f - 1.0f;
                const float ndcY =
                    1.0f - ((y - y0) / height) * 2.0f;

                float correctedX = 0.0f;
                float correctedY = 0.0f;
                if (state.worldEffect)
                {
                    bool fullyReprojected = false;

                    // Reconstruct the original clip position from D3D9 XYZRHW,
                    // unproject it through the game's perspective matrix, apply
                    // only the eye-relative translation (the common HMD camera
                    // can already be reflected by VRCullingCameraSync), and
                    // project through the real OpenXR eye FOV. This updates
                    // X/Y/Z/RHW together instead of treating RHW as an
                    // approximate 2D parallax scalar.
                    if (state.fullWorldReprojection &&
                        rhw > 1.0e-6f && rhw < 1000.0f)
                    {
                        const float invRhw = 1.0f / rhw;
                        const float clip[4]{
                            ndcX * invRhw,
                            ndcY * invRhw,
                            z * invRhw,
                            invRhw
                        };
                        float view[4]{};
                        for (int col = 0; col < 4; ++col)
                            for (int row = 0; row < 4; ++row)
                                view[col] += clip[row] *
                                    state.inverseBaseProjection.m[row][col];

                        if (std::isfinite(view[0]) &&
                            std::isfinite(view[1]) &&
                            std::isfinite(view[2]) &&
                            std::isfinite(view[3]) &&
                            std::fabs(view[3]) > 1.0e-6f)
                        {
                            const float invViewW = 1.0f / view[3];
                            float eyeView[4]{
                                view[0] * invViewW -
                                    state.eyeLocalTranslation[eye][0],
                                view[1] * invViewW -
                                    state.eyeLocalTranslation[eye][1],
                                view[2] * invViewW -
                                    state.eyeLocalTranslation[eye][2],
                                1.0f
                            };

                            float clipEye[4]{};
                            for (int col = 0; col < 4; ++col)
                                for (int row = 0; row < 4; ++row)
                                    clipEye[col] += eyeView[row] *
                                        state.eyeProjection[eye].m[row][col];

                            if (std::isfinite(clipEye[0]) &&
                                std::isfinite(clipEye[1]) &&
                                std::isfinite(clipEye[2]) &&
                                std::isfinite(clipEye[3]) &&
                                std::fabs(clipEye[3]) > 1.0e-6f)
                            {
                                const float invEyeW = 1.0f / clipEye[3];
                                const float fullX = clipEye[0] * invEyeW;
                                const float fullY = clipEye[1] * invEyeW;
                                const float fullZ = clipEye[2] * invEyeW;
                                if (std::isfinite(fullX) &&
                                    std::isfinite(fullY) &&
                                    std::isfinite(fullZ) &&
                                    fullZ >= -0.25f && fullZ <= 1.25f)
                                {
                                    correctedX = fullX;
                                    correctedY = fullY;
                                    p[2] = fullZ;
                                    p[3] = invEyeW;
                                    fullyReprojected = true;
                                }
                            }
                        }
                    }

                    if (!fullyReprojected)
                    {
                        // Conservative compatibility fallback for unusual
                        // pre-transformed formats that cannot be safely
                        // unprojected.
                        correctedX =
                            state.worldScaleX[eye] * ndcX +
                            state.worldOffsetX[eye];
                        correctedY =
                            state.worldScaleY[eye] * ndcY +
                            state.worldOffsetY[eye];
                        if (rhw > 0.0f && rhw < 1000.0f)
                        {
                            correctedX +=
                                state.parallaxPerRhwX[eye] * rhw;
                            correctedY +=
                                state.parallaxPerRhwY[eye] * rhw;
                        }
                    }
                }
                else
                {
                    // HUD is head-relative. Keep the asymmetric-FOV correction,
                    // then shrink the complete HUD toward the optical centre so
                    // speed/time/position remain inside the Quest 3 view.
                    // Scale the common HUD coordinate first, then apply the
                    // eye-specific asymmetric-FOV offset. Scaling the offset
                    // itself makes convergence drift as HUD size changes.
                    correctedX =
                        state.eyeScale[eye] * (R30HudScaleValue() * ndcX) +
                        state.eyeOffset[eye];
                    correctedY = R30HudScaleValue() * ndcY;
                }

                const float transformedX =
                    x0 + (correctedX + 1.0f) * 0.5f * width;
                const float transformedY =
                    y0 + (1.0f - correctedY) * 0.5f * height;
                if (!std::isfinite(transformedX) ||
                    !std::isfinite(transformedY))
                    return false;
                p[0] = transformedX;
                p[1] = transformedY;
            }
            return true;
        }

        template <typename LeftDraw, typename RightDraw>
        HRESULT R30ExecuteXyzrhwStereo(
            IDirect3DDevice9* device, const R30XyzrhwState& state,
            LeftDraw&& leftDraw, RightDraw&& rightDraw,
            const char* site)
        {
            ++R9DrawCalls;
            R9MonoBackupGap = true;
            if (LeftDrawMayWriteDepth(device) ||
                LeftDrawMayWriteStencil(device))
                ++R9MainDepthContentSerial;

            const HRESULT leftHr = leftDraw();
            if (FAILED(leftHr))
            {
                R9Poison(OutRunVR::StereoFailureLeftDrawFailed,
                    site, leftHr);
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
                    rightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(
                        device, TrackedDepthStencil ? RightEyeDepth : nullptr);
                if (SUCCEEDED(rightHr))
                    rightHr = device->SetViewport(&state.viewport);
                if (SUCCEEDED(rightHr))
                {
                    rightFailure =
                        OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = rightDraw();
                }
                restoreOk = RestoreRightPassState(device,
                    savedRt, savedDepth, state.viewport, nullptr, false);
            }

            FrameHadDuplicatedDraw = true;
            ++DuplicatedDraws;
            ++R29StableTwoEyeDraws;
            if (state.worldEffect)
            {
                ++R30XyzrhwWorldEffectDraws;
                if (FrameStereoPoseSequence == 0)
                {
                    FrameStereoPoseSequence = state.stereo.poseSequence;
                    FrameStereoMetadata = state.stereo;
                }
                else if (FrameStereoPoseSequence != state.stereo.poseSequence)
                {
                    FrameRightDrawFailed = true;
                    PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);
                }
                FrameHadWorldStereo = true;
                ++WorldStereoDraws;
                if (!R30FirstXyzrhwWorldLogged)
                {
                    R30FirstXyzrhwWorldLogged = true;
                    spdlog::info(
                        "VR R30.4 XYZRHW WORLD: pre-transformed particle/billboard/decal draws reconstruct clip X/Y/Z/RHW, unproject through the game projection, then reproject into each OpenXR eye; affine RHW fallback retained for unsafe vertices");
                }
            }
            else
            {
                ++NonWorldDuplicatedDraws;
                ++R30XyzrhwHudDraws;
                if (!R30FirstXyzrhwHudLogged)
                {
                    R30FirstXyzrhwHudLogged = true;
                    spdlog::info(
                        "VR R30.3 XYZRHW HUD: pre-transformed fixed-function UP draws receive asymmetric-FOV correction plus centered HUD scale");
                }
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
                NoteRestoreFailure("R30.2 XYZRHW right-eye draw");
                R29ArmMonoSafety();
            }
            return leftHr;
        }

        HRESULT R30TryXyzrhwPrimitiveUP(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT primitiveCount, const void* data, UINT stride)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;
            const UINT vertexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!R30ConfigureXyzrhwWorldEffect(
                    device, data, vertexCount, stride, state))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }
            std::vector<std::uint8_t> left;
            std::vector<std::uint8_t> right;
            if (!R30TransformXyzrhwVertices(
                    data, vertexCount, stride, state, 0, left) ||
                !R30TransformXyzrhwVertices(
                    data, vertexCount, stride, state, 1, right))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, left.data(), stride);
            };
            auto rightDraw = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, right.data(), stride);
            };
            return R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.2/DrawPrimitiveUP-XYZRHW");
        }

        HRESULT R30TryXyzrhwIndexedPrimitiveUP(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;

            const UINT indexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!indexData || indexCount == 0 ||
                (indexFormat != D3DFMT_INDEX16 &&
                 indexFormat != D3DFMT_INDEX32))
                return E_NOTIMPL;

            UINT maxIndex = 0;
            if (indexFormat == D3DFMT_INDEX16)
            {
                const auto* indices =
                    static_cast<const std::uint16_t*>(indexData);
                for (UINT i = 0; i < indexCount; ++i)
                    maxIndex = std::max<UINT>(maxIndex, indices[i]);
            }
            else
            {
                const auto* indices =
                    static_cast<const std::uint32_t*>(indexData);
                for (UINT i = 0; i < indexCount; ++i)
                    maxIndex = std::max(maxIndex, indices[i]);
            }

            const UINT vertexCount =
                std::max<UINT>(minVertexIndex + numVertices,
                    maxIndex + 1u);
            if (vertexCount == 0 || vertexCount > 262144u)
                return E_NOTIMPL;

            if (!R30ConfigureXyzrhwWorldEffect(
                    device, vertexData, vertexCount, stride, state))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            std::vector<std::uint8_t> left;
            std::vector<std::uint8_t> right;
            if (!R30TransformXyzrhwVertices(
                    vertexData, vertexCount, stride, state, 0, left) ||
                !R30TransformXyzrhwVertices(
                    vertexData, vertexCount, stride, state, 1, right))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, minVertexIndex, numVertices,
                    primitiveCount, indexData, indexFormat,
                    left.data(), stride);
            };
            auto rightDraw = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, minVertexIndex, numVertices,
                    primitiveCount, indexData, indexFormat,
                    right.data(), stride);
            };
            return R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.2/DrawIndexedPrimitiveUP-XYZRHW");
        }


        HRESULT R30TryXyzrhwPrimitiveVB(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT startVertex, UINT primitiveCount)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;

            const UINT vertexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!vertexCount || vertexCount > 262144u)
                return E_NOTIMPL;

            IDirect3DVertexBuffer9* vb = nullptr;
            UINT streamOffset = 0;
            UINT stride = 0;
            if (FAILED(device->GetStreamSource(
                    0, &vb, &streamOffset, &stride)) ||
                !vb || stride < sizeof(float) * 4)
            {
                if (vb) vb->Release();
                return E_NOTIMPL;
            }

            D3DVERTEXBUFFER_DESC desc{};
            const std::uint64_t firstByte =
                static_cast<std::uint64_t>(streamOffset) +
                static_cast<std::uint64_t>(startVertex) * stride;
            const std::uint64_t byteCount =
                static_cast<std::uint64_t>(vertexCount) * stride;
            if (FAILED(vb->GetDesc(&desc)) || firstByte > desc.Size ||
                byteCount > desc.Size - firstByte ||
                firstByte > UINT_MAX || byteCount > UINT_MAX)
            {
                vb->Release();
                return E_NOTIMPL;
            }

            void* source = nullptr;
            if (FAILED(vb->Lock(static_cast<UINT>(firstByte),
                    static_cast<UINT>(byteCount), &source, D3DLOCK_READONLY)) ||
                !source)
            {
                vb->Release();
                return E_NOTIMPL;
            }

            const bool configured = R30ConfigureXyzrhwWorldEffect(
                device, source, vertexCount, stride, state);
            std::vector<std::uint8_t> left;
            std::vector<std::uint8_t> right;
            const bool transformed = configured &&
                R30TransformXyzrhwVertices(
                    source, vertexCount, stride, state, 0, left) &&
                R30TransformXyzrhwVertices(
                    source, vertexCount, stride, state, 1, right);
            vb->Unlock();

            if (!transformed)
            {
                vb->Release();
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, left.data(), stride);
            };
            auto rightDraw = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, right.data(), stride);
            };
            const HRESULT hr = R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.4/DrawPrimitiveVB-XYZRHW");

            // DrawPrimitiveUP clears stream 0. Restore the game's VB binding so
            // the next draw sees exactly the state that preceded this conversion.
            {
                InternalPassScope guard;
                if (FAILED(device->SetStreamSource(
                        0, vb, streamOffset, stride)))
                {
                    NoteRestoreFailure("R30.4 VB stream restore");
                    R29ArmMonoSafety();
                }
            }
            vb->Release();
            return hr;
        }

        HRESULT R30TryXyzrhwIndexedPrimitiveVB(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;

            const UINT indexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!indexCount || !numVertices || indexCount > 524288u)
                return E_NOTIMPL;

            IDirect3DVertexBuffer9* vb = nullptr;
            IDirect3DIndexBuffer9* ib = nullptr;
            UINT streamOffset = 0;
            UINT stride = 0;
            if (FAILED(device->GetStreamSource(
                    0, &vb, &streamOffset, &stride)) ||
                !vb || stride < sizeof(float) * 4 ||
                FAILED(device->GetIndices(&ib)) || !ib)
            {
                if (ib) ib->Release();
                if (vb) vb->Release();
                return E_NOTIMPL;
            }

            D3DINDEXBUFFER_DESC ibDesc{};
            if (FAILED(ib->GetDesc(&ibDesc)) ||
                (ibDesc.Format != D3DFMT_INDEX16 &&
                 ibDesc.Format != D3DFMT_INDEX32))
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }
            const UINT indexSize =
                ibDesc.Format == D3DFMT_INDEX16 ? 2u : 4u;
            const std::uint64_t firstIndexByte =
                static_cast<std::uint64_t>(startIndex) * indexSize;
            const std::uint64_t indexBytes =
                static_cast<std::uint64_t>(indexCount) * indexSize;
            if (firstIndexByte > ibDesc.Size ||
                indexBytes > ibDesc.Size - firstIndexByte ||
                firstIndexByte > UINT_MAX || indexBytes > UINT_MAX)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            void* rawIndices = nullptr;
            if (FAILED(ib->Lock(static_cast<UINT>(firstIndexByte),
                    static_cast<UINT>(indexBytes), &rawIndices,
                    D3DLOCK_READONLY)) || !rawIndices)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            std::vector<std::uint32_t> physical(indexCount);
            std::int64_t minPhysical = INT64_MAX;
            std::int64_t maxPhysical = INT64_MIN;
            for (UINT i = 0; i < indexCount; ++i)
            {
                const std::uint32_t raw =
                    ibDesc.Format == D3DFMT_INDEX16
                    ? static_cast<const std::uint16_t*>(rawIndices)[i]
                    : static_cast<const std::uint32_t*>(rawIndices)[i];
                const std::int64_t p =
                    static_cast<std::int64_t>(baseVertexIndex) + raw;
                if (p < 0 || p > UINT_MAX)
                {
                    ib->Unlock();
                    ib->Release();
                    vb->Release();
                    return E_NOTIMPL;
                }
                physical[i] = static_cast<std::uint32_t>(p);
                minPhysical = std::min(minPhysical, p);
                maxPhysical = std::max(maxPhysical, p);
            }
            ib->Unlock();

            if (minPhysical == INT64_MAX || maxPhysical < minPhysical)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }
            const std::uint64_t vertexCount64 =
                static_cast<std::uint64_t>(maxPhysical - minPhysical) + 1u;
            if (!vertexCount64 || vertexCount64 > 262144u)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }
            const UINT vertexCount = static_cast<UINT>(vertexCount64);

            D3DVERTEXBUFFER_DESC vbDesc{};
            const std::uint64_t firstVertexByte =
                static_cast<std::uint64_t>(streamOffset) +
                static_cast<std::uint64_t>(minPhysical) * stride;
            const std::uint64_t vertexBytes =
                static_cast<std::uint64_t>(vertexCount) * stride;
            if (FAILED(vb->GetDesc(&vbDesc)) ||
                firstVertexByte > vbDesc.Size ||
                vertexBytes > vbDesc.Size - firstVertexByte ||
                firstVertexByte > UINT_MAX || vertexBytes > UINT_MAX)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            void* source = nullptr;
            if (FAILED(vb->Lock(static_cast<UINT>(firstVertexByte),
                    static_cast<UINT>(vertexBytes), &source,
                    D3DLOCK_READONLY)) || !source)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            const bool configured = R30ConfigureXyzrhwWorldEffect(
                device, source, vertexCount, stride, state);
            std::vector<std::uint8_t> left;
            std::vector<std::uint8_t> right;
            const bool transformed = configured &&
                R30TransformXyzrhwVertices(
                    source, vertexCount, stride, state, 0, left) &&
                R30TransformXyzrhwVertices(
                    source, vertexCount, stride, state, 1, right);
            vb->Unlock();
            if (!transformed)
            {
                ib->Release();
                vb->Release();
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            std::vector<std::uint16_t> indices16;
            std::vector<std::uint32_t> indices32;
            const void* rebased = nullptr;
            if (ibDesc.Format == D3DFMT_INDEX16)
            {
                indices16.resize(indexCount);
                for (UINT i = 0; i < indexCount; ++i)
                {
                    const std::uint64_t v =
                        physical[i] - static_cast<std::uint64_t>(minPhysical);
                    if (v > 0xFFFFu)
                    {
                        ib->Release();
                        vb->Release();
                        return E_NOTIMPL;
                    }
                    indices16[i] = static_cast<std::uint16_t>(v);
                }
                rebased = indices16.data();
            }
            else
            {
                indices32.resize(indexCount);
                for (UINT i = 0; i < indexCount; ++i)
                    indices32[i] = physical[i] -
                        static_cast<std::uint32_t>(minPhysical);
                rebased = indices32.data();
            }

            auto leftDraw = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, 0u, vertexCount, primitiveCount,
                    rebased, ibDesc.Format, left.data(), stride);
            };
            auto rightDraw = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, 0u, vertexCount, primitiveCount,
                    rebased, ibDesc.Format, right.data(), stride);
            };
            const HRESULT hr = R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.4/DrawIndexedPrimitiveVB-XYZRHW");

            // DrawIndexedPrimitiveUP clears stream 0 and the index buffer.
            {
                InternalPassScope guard;
                bool restoreOk = SUCCEEDED(device->SetStreamSource(
                    0, vb, streamOffset, stride));
                restoreOk = SUCCEEDED(device->SetIndices(ib)) && restoreOk;
                if (!restoreOk)
                {
                    NoteRestoreFailure("R30.4 VB/IB restore");
                    R29ArmMonoSafety();
                }
            }
            ib->Release();
            vb->Release();
            return hr;
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

            if (!R30BuildEyeAffine(stereo, eyeScale, eyeOffset))
                return false;

            D3DMATRIX uploadedT{};
            std::memcpy(&uploadedT, original, sizeof(uploadedT));
            const D3DMATRIX stockWvp = TransposeMatrix(uploadedT);
            if (!MatrixFinite(stockWvp))
                return false;

            for (int eye = 0; eye < 2; ++eye)
            {
                D3DMATRIX clipCorrection{};
                clipCorrection._11 =
                    eyeScale[eye] * R30HudScaleValue();
                clipCorrection._22 = R30HudScaleValue();
                clipCorrection._33 = 1.0f;
                clipCorrection._44 = 1.0f;
                // Row-vector clip transform. Scale both axes around clip-space
                // centre and preserve the eye-specific asymmetric-FOV offset.
                clipCorrection._41 = eyeOffset[eye];

                const D3DMATRIX corrected =
                    MultiplyMatrix(stockWvp, clipCorrection);
                if (!MatrixFinite(corrected))
                    return false;

                const D3DMATRIX correctedT = TransposeMatrix(corrected);
                std::memcpy(eyeConstants[eye], &correctedT,
                    sizeof(correctedT));
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
                    "VR R30 HUD: orthographic ScreenSpace2D asymmetric-FOV correction ACTIVE eyeScale[L/R]={:.4f}/{:.4f} offset[L/R]={:.4f}/{:.4f} hudScale={:.2f}; headset FOV auto-map + user scale active; world/effect passes unchanged",
                    eyeScale[0], eyeScale[1], eyeOffset[0], eyeOffset[1],
                    R30HudScaleValue());
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
            const HRESULT xyzrhw = R30TryXyzrhwPrimitiveVB(
                device, type, startVertex, primitiveCount);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

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
            const HRESULT xyzrhw = R30TryXyzrhwIndexedPrimitiveVB(
                device, type, baseVertexIndex, minVertexIndex, numVertices,
                startIndex, primitiveCount);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

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
            const HRESULT xyzrhw = R30TryXyzrhwPrimitiveUP(
                device, type, primitiveCount, data, stride);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

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
            const HRESULT xyzrhw = R30TryXyzrhwIndexedPrimitiveUP(
                device, type, minVertexIndex, numVertices, primitiveCount,
                indexData, indexFormat, vertexData, stride);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

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
                        "VR R30 HUD: ScreenSpace2D correction READY with configurable common-center HUD scale default/current={:.2f}; R30.4 XYZRHW full game-projection -> OpenXR-eye reprojection READY",
                        R30HudScaleValue());
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
