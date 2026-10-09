#pragma once
// Behavior-neutral R30/lower-owner services consumed by R31.
//
// R31 is being prepared for independent translation-unit compilation. These
// calls preserve the current lower-chain behavior while preventing R31 from
// reaching private R30/R29/R23/R22/R9 state through a textual .cpp include.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <Windows.h>
#include <d3d9.h>
#include <cstdint>

#include "../runtime_eligibility.hpp"
#include "../ipc/protocol.hpp"

namespace OutRunVRStereo
{
    OutRunVR::RuntimeEligibility::InstallState R30InstallStatus() noexcept;

    bool R30SupportTelemetryEnabled() noexcept;
    bool R30SupportIsGameDevice(IDirect3DDevice9* device) noexcept;
    bool R30SupportInternalStereoPassActive() noexcept;
    bool R30SupportExchangeInternalStereoPass(bool active) noexcept;
    std::uint64_t R30SupportPresentEpoch() noexcept;
    bool R30SupportStereoWanted() noexcept;
    bool R30SupportStereoBaselineSeeded() noexcept;
    // R9 depth-generation/stencil metadata remains lower-owned and read-only.
    std::uint64_t R30SupportMainDepthGeneration() noexcept;
    bool R30SupportMainDepthHasStencil() noexcept;
    // Exact lower R9 depth-content write notification, without a new epoch.
    void R30SupportNoteMainDepthContentWrite() noexcept;
    // Exact lower R9 right-eye depth/stencil sync query and invalidation owner.
    void R30SupportInvalidateRightDepthStencilSync(
        bool invalidateDepth, bool invalidateStencil) noexcept;
    bool R30SupportRightDepthInSync() noexcept;
    bool R30SupportRightStencilInSync() noexcept;
    bool R30SupportTargetIsBackBuffer() noexcept;
    bool R30SupportAnyAuxRenderTargetActive() noexcept;
    bool R30SupportTryGetTrackedViewport(D3DVIEWPORT9& viewport) noexcept;

    struct R30SupportEffectTelemetrySnapshot
    {
        DWORD alphaBlend = FALSE;
        DWORD alphaTest = FALSE;
        DWORD zWrite = TRUE;
    };
    bool R30SupportTryGetEffectTelemetrySnapshot(
        R30SupportEffectTelemetrySnapshot& out) noexcept;
    // Preserve the lower R29 effect and stereo readiness policy verbatim.
    bool R30SupportStableStereoBase(IDirect3DDevice9* device) noexcept;
    bool R30SupportFragileEffectCached(IDirect3DDevice9* device,
        bool& fragile) noexcept;
    void R30SupportNoteStableTwoEyeDraw() noexcept;

    struct R30SupportDirectTransportIdentity
    {
        std::uint32_t hostPid = 0;
        std::uint32_t hostAdapterLuidLow = 0;
        std::uint32_t hostAdapterLuidHigh = 0;
    };
    bool R30SupportOverlayReadyForTransport() noexcept;
    void R30SupportNoteSafeAckBackpressure() noexcept;
    void R30SupportNoteDirectTransportRingBackpressure() noexcept;
    std::uint64_t R30SupportDirectTransportRingBackpressureCount() noexcept;
    void R30SupportSetActiveDirectTransportSlot(std::uint32_t slot) noexcept;
    void R30SupportMarkDirectTransportSlotPending(
        std::uint32_t slot, std::uint32_t frameId) noexcept;
    HRESULT R30SupportPollDirectTransportSlotProducer(
        std::uint32_t slot) noexcept;
    void R30SupportRetireDirectTransportSlotPublication(
        std::uint32_t slot) noexcept;
    struct R30SupportGpuCompletionSnapshot
    {
        std::uint32_t completedFrameId[OutRunVR::RenderFrameRingSize]{};
    };
    bool R30SupportTryGetGpuCompletionSnapshot(
        R30SupportGpuCompletionSnapshot& out) noexcept;
    bool R30SupportDirectTransportResourcesReady() noexcept;
    bool R30SupportEnsureDirectTransportResources(
        IDirect3DDevice9* device) noexcept;
    struct R30SupportDirectTransportSourceSurfaces
    {
        IDirect3DSurface9* left = nullptr;
        IDirect3DSurface9* right = nullptr;
    };
    bool R30SupportTryGetDirectTransportSourceSurfaces(
        R30SupportDirectTransportSourceSurfaces& out) noexcept;
    // Borrowed, no AddRef: preserve the former R32 direct right-eye lookup.
    // Borrowed tracked game RT/depth pointers: no ownership transfer or AddRef.
    IDirect3DSurface9* R30SupportBorrowedTrackedRenderTarget() noexcept;
    IDirect3DSurface9* R30SupportBorrowedTrackedDepthStencil() noexcept;
    IDirect3DSurface9* R30SupportBorrowedRightEyeSurface() noexcept;
    // Borrowed R9 right-eye depth surface; identity and lifetime stay lower-owned.
    IDirect3DSurface9* R30SupportBorrowedRightEyeDepth() noexcept;
    std::uint32_t R30SupportFrameStereoPoseSequence() noexcept;
    void R30SupportReleaseDirectAckState() noexcept;
    void R30SupportReleaseDirectTransportInterop() noexcept;
    bool R30SupportTryGetDirectTransportIdentity(
        R30SupportDirectTransportIdentity& out) noexcept;

    void R30SupportInvalidateEffectStateCache() noexcept;
    void R30SupportInvalidateTrackedRasterShadow() noexcept;
    void R30SupportInvalidateLiveStateSample() noexcept;
    std::uintptr_t R30SupportCurrentVertexShaderIdentity() noexcept;
    std::uintptr_t R30SupportExchangeVertexShaderIdentity(
        std::uintptr_t identity) noexcept;
    void R30SupportRestoreVertexShaderIdentityIfEmpty(
        std::uintptr_t identity) noexcept;
    float R30SupportWorldScale() noexcept;

    D3DMATRIX R30SupportMatrixFromQuaternionTranslation(
        const float orientation[4], const float position[3],
        float positionScale) noexcept;
    D3DMATRIX R30SupportInverseRigid(const D3DMATRIX& matrix) noexcept;
    D3DMATRIX R30SupportProjectionFromFov(
        const D3DMATRIX& base, const OutRunVR::SharedFov& fov) noexcept;
    D3DMATRIX R30SupportMultiplyMatrix(
        const D3DMATRIX& a, const D3DMATRIX& b) noexcept;
    D3DMATRIX R30SupportTransposeMatrix(const D3DMATRIX& matrix) noexcept;
    bool R30SupportMatrixFinite(const D3DMATRIX& matrix) noexcept;
    bool R30SupportGetInverseProjection(
        const D3DMATRIX& projection, D3DMATRIX& inverse) noexcept;

    bool R30SupportValidateVerifiedWvp(
        IDirect3DDevice9* device, const float verified[16],
        float live[16]) noexcept;
    bool R30SupportGetVerifiedProjection(
        float outProjection[16], std::uint32_t& generation,
        std::uint32_t& poseSequence) noexcept;
    void R30SupportResynchronizeShaderEpoch(
        IDirect3DDevice9* device) noexcept;
    void R30SupportInvalidateRendererStateAfterExternalRestore() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R30SupportRendererInstallStatus() noexcept;
    bool R30SupportPrimeTrackedRasterShadow(
        IDirect3DDevice9* device) noexcept;
}