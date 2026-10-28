// Frozen CPU transform reference from cffec078b50debec5b8a95e5b0fb4a6653cec272.
bool R30TransformXyzrhwVertices(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state, int eye,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& out,
            const std::vector<std::uint8_t>* usedMask,
            bool allowFullReprojection, bool& usedFullReprojection) noexcept
        {
            usedFullReprojection = false;
            if (!source || vertexCount == 0 || stride < sizeof(float) * 4 ||
                eye < 0 || eye > 1)
                return false;
            const std::size_t bytes =
                static_cast<std::size_t>(vertexCount) * stride;
            if (bytes == 0 || bytes > 4u * 1024u * 1024u)
                return false;
            if (usedMask && usedMask->size() < vertexCount)
                return false;

            const float x0 = static_cast<float>(state.viewport.X);
            const float y0 = static_cast<float>(state.viewport.Y);
            const float width = static_cast<float>(state.viewport.Width);
            const float height = static_cast<float>(state.viewport.Height);
            const float minZ = state.viewport.MinZ;
            const float maxZ = state.viewport.MaxZ;
            const float depthSpan = maxZ - minZ;
            if (width <= 0.0f || height <= 0.0f ||
                !std::isfinite(depthSpan) || depthSpan <= 1.0e-6f)
                return false;

            // Fail before the expensive clone for invalid viewport state.
            // Fully overwrite the logical payload (including attributes and
            // unused indexed vertices) before changing either eye's XYZRHW.
            // A rejected full projection may re-copy original bytes below.
            try
            {
                out.resize(bytes);
            }
            catch (...)
            {
                return false;
            }
            std::memcpy(out.data(), source, bytes);

            auto selected = [&](UINT i) noexcept
            {
                return !usedMask || (*usedMask)[i] != 0;
            };
            auto sourceVertex = [&](UINT i) noexcept -> const float*
            {
                return reinterpret_cast<const float*>(
                    static_cast<const std::uint8_t*>(source) +
                    static_cast<std::size_t>(i) * stride);
            };
            auto outputVertex = [&](UINT i) noexcept -> float*
            {
                return reinterpret_cast<float*>(
                    out.data() + static_cast<std::size_t>(i) * stride);
            };

            // M5 evidence only. A game-presented XYZRHW pixel must not be
            // assumed to share the backbuffer/eye viewport coordinate space.
            // Preserve all existing projection math until actual producer
            // source extent is proven from captures on the same physical draw.
            if (Settings::VRTelemetry && !state.worldEffect)
            {
                const auto command =
                    OutRunVR::GameSemantic::CapturePhysicalDrawCommand();
                if (OutRunVR::GameSemantic::ExternalOverlaySemanticDepth == 0 &&
                    command.IsExactFiniteResultHud() &&
                    (!command.queued ||
                     (command.queueNode && command.queueEpoch != 0)))
                {
                    static std::atomic<std::uint64_t> resultPixelProbes{ 0 };
                    const auto n = resultPixelProbes.fetch_add(
                        1, std::memory_order_relaxed) + 1;
                    if (n <= 16 || (n & (n - 1)) == 0)
                    {
                        UINT firstUsed = 0;
                        while (usedMask && firstUsed < vertexCount &&
                               !(*usedMask)[firstUsed])
                            ++firstUsed;
                        if (firstUsed < vertexCount)
                        {
                            const float* v = sourceVertex(firstUsed);
                            spdlog::info(
                                "VR R26 RESULT_XYZRHW_PIXEL_PROBE: stage=TRANSFORM_CANDIDATE producer={} queued={} node={} epoch={} eye={} firstUsed={} xy={},{} vertices={} backbuffer={}x{} viewport={},{},{},{} sourceExtent=UNPROVEN hits={}",
                                OutRunVR::GameSemantic::Name(command.producer),
                                command.queued, command.queueNode,
                                command.queueEpoch, eye, firstUsed,
                                v[0], v[1], vertexCount,
                                BackBufferDesc.Width, BackBufferDesc.Height,
                                state.viewport.X, state.viewport.Y,
                                state.viewport.Width, state.viewport.Height, n);
                        }
                    }
                }
            }

            if (state.worldEffect && state.fullWorldReprojection &&
                allowFullReprojection)
            {
                bool fullDrawOk = true;
                UINT selectedVertices = 0;
                for (UINT i = 0; i < vertexCount; ++i)
                {
                    if (!selected(i))
                        continue;
                    ++selectedVertices;

                    const float* src = sourceVertex(i);
                    float* dst = outputVertex(i);
                    const float x = src[0];
                    const float y = src[1];
                    const float screenZ = src[2];
                    const float rhw = src[3];
                    if (!std::isfinite(x) || !std::isfinite(y) ||
                        !std::isfinite(screenZ) || !std::isfinite(rhw) ||
                        rhw <= 1.0e-6f || rhw >= 1000.0f)
                    {
                        fullDrawOk = false;
                        break;
                    }

                    const float ndcX = ((x - x0) / width) * 2.0f - 1.0f;
                    const float ndcY =
                        1.0f - ((y - y0) / height) * 2.0f;
                    const float clipW = 1.0f / rhw;
                    const float clipX = ndcX * clipW;
                    const float clipY = ndcY * clipW;

                    float restoredView[4]{};
                    bool restored = false;

                    // Pre-transformed D3D9 particles carry RHW = 1/clipW.
                    // For the normal OutRun perspective matrix, clipW gives
                    // view-Z directly and X/Y can then be solved from clip X/Y.
                    // This avoids depending on the particle's biased/clamped
                    // screen Z, which is exactly what caused smoke/decal draws
                    // to fall back to the approximate affine path.
                    const D3DMATRIX& bp = state.baseProjection;
                    if (std::fabs(bp._14) <= 1.0e-5f &&
                        std::fabs(bp._24) <= 1.0e-5f &&
                        std::fabs(bp._34) > 1.0e-5f)
                    {
                        const float viewZ =
                            (clipW - bp._44) / bp._34;
                        const float rhsX =
                            clipX - viewZ * bp._31 - bp._41;
                        const float rhsY =
                            clipY - viewZ * bp._32 - bp._42;
                        const float det =
                            bp._11 * bp._22 - bp._21 * bp._12;
                        if (std::isfinite(viewZ) &&
                            std::isfinite(rhsX) &&
                            std::isfinite(rhsY) &&
                            std::isfinite(det) &&
                            std::fabs(det) > 1.0e-6f)
                        {
                            const float viewX =
                                (rhsX * bp._22 -
                                 bp._21 * rhsY) / det;
                            const float viewY =
                                (bp._11 * rhsY -
                                 rhsX * bp._12) / det;
                            if (std::isfinite(viewX) &&
                                std::isfinite(viewY))
                            {
                                restoredView[0] = viewX;
                                restoredView[1] = viewY;
                                restoredView[2] = viewZ;
                                restoredView[3] = 1.0f;
                                restored = true;
                            }
                        }
                    }

                    // Compatibility fallback for an unusual projection shape:
                    // retain the previous inverse-projection reconstruction.
                    if (!restored)
                    {
                        const float ndcZ =
                            (screenZ - minZ) / depthSpan;
                        if (!std::isfinite(ndcZ) ||
                            ndcZ < -0.25f || ndcZ > 1.25f)
                        {
                            fullDrawOk = false;
                            break;
                        }
                        const float clip[4]{
                            clipX, clipY, ndcZ * clipW, clipW
                        };
                        float restoredViewH[4]{};
                        for (int col = 0; col < 4; ++col)
                            for (int row = 0; row < 4; ++row)
                                restoredViewH[col] += clip[row] *
                                    state.inverseBaseProjection.m[row][col];

                        if (!std::isfinite(restoredViewH[0]) ||
                            !std::isfinite(restoredViewH[1]) ||
                            !std::isfinite(restoredViewH[2]) ||
                            !std::isfinite(restoredViewH[3]) ||
                            std::fabs(restoredViewH[3]) <= 1.0e-6f)
                        {
                            fullDrawOk = false;
                            break;
                        }

                        const float invRestoredW =
                            1.0f / restoredViewH[3];
                        restoredView[0] =
                            restoredViewH[0] * invRestoredW;
                        restoredView[1] =
                            restoredViewH[1] * invRestoredW;
                        restoredView[2] =
                            restoredViewH[2] * invRestoredW;
                        restoredView[3] = 1.0f;
                    }

                    // Match the normal world path exactly: the reconstructed
                    // game-view point receives the same rigid eyeInverse that
                    // BuildEyeConstants/fixed-function world draws use.
                    float eyeView[4]{};
                    for (int col = 0; col < 4; ++col)
                        for (int row = 0; row < 4; ++row)
                            eyeView[col] += restoredView[row] *
                                state.eyeInverse[eye].m[row][col];

                    float clipEye[4]{};
                    for (int col = 0; col < 4; ++col)
                        for (int row = 0; row < 4; ++row)
                            clipEye[col] += eyeView[row] *
                                state.eyeProjection[eye].m[row][col];

                    // D3D9 perspective clip-W must stay in front of the eye.
                    // abs(W) would accept a point behind the camera and mirror
                    // it back into the visible image.
                    if (!std::isfinite(clipEye[0]) ||
                        !std::isfinite(clipEye[1]) ||
                        !std::isfinite(clipEye[2]) ||
                        !std::isfinite(clipEye[3]) ||
                        clipEye[3] <= 1.0e-6f)
                    {
                        fullDrawOk = false;
                        break;
                    }

                    const float invEyeW = 1.0f / clipEye[3];
                    const float fullX = clipEye[0] * invEyeW;
                    const float fullY = clipEye[1] * invEyeW;
                    const float fullZ = clipEye[2] * invEyeW;
                    if (!std::isfinite(fullX) ||
                        !std::isfinite(fullY) ||
                        !std::isfinite(fullZ))
                    {
                        fullDrawOk = false;
                        break;
                    }

                    const float transformedX =
                        x0 + (fullX + 1.0f) * 0.5f * width;
                    const float transformedY =
                        y0 + (1.0f - fullY) * 0.5f * height;

                    // Decals/particles can intentionally bias screen Z beyond
                    // the strict viewport interval. Preserve the game's Z in
                    // that case, while still using the accurately reprojected
                    // eye X/Y and RHW. Falling the whole quad back to an affine
                    // shift was the visible left/right smoke/skid offset.
                    float transformedZ = screenZ;
                    if (fullZ >= 0.0f && fullZ <= 1.0f)
                    {
                        transformedZ = minZ + fullZ * depthSpan;
                    }
                    else
                    {
                        ++R30XyzrhwDepthPreserveFallbacks;
                    }
                    if (!std::isfinite(transformedX) ||
                        !std::isfinite(transformedY) ||
                        !std::isfinite(transformedZ))
                    {
                        fullDrawOk = false;
                        break;
                    }

                    dst[0] = transformedX;
                    dst[1] = transformedY;
                    dst[2] = transformedZ;
                    dst[3] = invEyeW;
                }

                if (fullDrawOk && selectedVertices != 0)
                {
                    usedFullReprojection = true;
                    return true;
                }

                ++R30XyzrhwAtomicFallbacks;
                if (!R30FirstXyzrhwAtomicFallbackLogged)
                {
                    R30FirstXyzrhwAtomicFallbackLogged = true;
                    spdlog::info(
                        "VR R30.6 XYZRHW WORLD: full reprojection rejected for a referenced vertex; this eye candidate is discarded before bilateral fallback selection");
                }
                std::memcpy(out.data(), source, bytes);
            }

            for (UINT i = 0; i < vertexCount; ++i)
            {
                if (!selected(i))
                    continue;

                float* p = outputVertex(i);
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
                if (state.projectedWorldMarker)
                {
                    // Match the shader/c64 ProjectedWorldMarker2D route:
                    // scale around the recovered stock anchor, then apply the
                    // per-eye reprojection delta. This preserves rank digit/
                    // rival sprite offsets while keeping them attached to the
                    // same vehicle during head motion.
                    const float markerScale = R30HudScaleValue();
                    correctedX =
                        markerScale * ndcX +
                        state.projectedDeltaX[eye] +
                        (1.0f - markerScale) * state.projectedBaseX;
                    correctedY =
                        markerScale * ndcY +
                        state.projectedDeltaY[eye] +
                        (1.0f - markerScale) * state.projectedBaseY;
                }
                else if (state.worldEffect)
                {
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
                    // Fallback keeps the game's original Z/RHW pair intact.
                }
                else
                {
                    // R51: both exact SCREEN_HUD and generic canonical
                    // SCREEN_OVERLAY_2D are queue-owned 2D. Put them on the
                    // finite recentered world-fixed plane so they no longer
                    // rotate with the HMD. WORLD_BILLBOARD never enters here.
                    if (!state.hudWorldLockValid)
                        return false;

                    const float clipX =
                        state.hudClipX[eye][0] * ndcX +
                        state.hudClipX[eye][1] * ndcY +
                        state.hudClipX[eye][2];
                    const float clipY =
                        state.hudClipY[eye][0] * ndcX +
                        state.hudClipY[eye][1] * ndcY +
                        state.hudClipY[eye][2];
                    const float clipW =
                        state.hudClipW[eye][0] * ndcX +
                        state.hudClipW[eye][1] * ndcY +
                        state.hudClipW[eye][2];
                    if (!std::isfinite(clipX) ||
                        !std::isfinite(clipY) ||
                        !std::isfinite(clipW) ||
                        clipW <= 1.0e-6f)
                        return false;
                    correctedX = clipX / clipW;
                    correctedY = clipY / clipW;
                    if (!std::isfinite(correctedX) ||
                        !std::isfinite(correctedY))
                        return false;
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
bool R30TransformXyzrhwStereo(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& left,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& right,
            const std::vector<std::uint8_t>* usedMask = nullptr) noexcept
        {
            bool leftFull = false;
            bool rightFull = false;
            if (!R30TransformXyzrhwVertices(source, vertexCount, stride,
                    state, 0, left, usedMask, true, leftFull) ||
                !R30TransformXyzrhwVertices(source, vertexCount, stride,
                    state, 1, right, usedMask, true, rightFull))
                return false;

            if (leftFull != rightFull)
            {
                ++R30XyzrhwBilateralFallbacks;
                if (!R30FirstXyzrhwBilateralFallbackLogged)
                {
                    R30FirstXyzrhwBilateralFallbackLogged = true;
                    spdlog::info(
                        "VR R30.6 XYZRHW WORLD: one eye rejected full reprojection; both eyes are forced onto the same affine fallback policy");
                }
                bool ignored = false;
                if (!R30TransformXyzrhwVertices(source, vertexCount, stride,
                        state, 0, left, usedMask, false, ignored) ||
                    !R30TransformXyzrhwVertices(source, vertexCount, stride,
                        state, 1, right, usedMask, false, ignored))
                    return false;
            }
            return true;
        }
