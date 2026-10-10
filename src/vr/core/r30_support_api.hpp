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

    // Stable R30-owned render routing, not the anonymous R30 private enum.
    enum class R30SupportScreenSpaceKind : std::uint8_t
    {
        None, Hud2D, FlatPerspectiveEffect
    };
    R30SupportScreenSpaceKind R30SupportClassifyScreenSpacePass(
        IDirect3DDevice9* device) noexcept;
    bool R30SupportBuildScreenSpaceEyeConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        R30SupportScreenSpaceKind kind,
        float original[16], float eyeConstants[2][16],
        float eyeScale[2], float eyeOffset[2]) noexcept;
    void R30SupportNoteScreenSpaceFovDraw() noexcept;

    // R30 owns the four XYZRHW paths and four R29 lower replay families.
    HRESULT R30SupportTryXyzrhwPrimitiveVB(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept;
    HRESULT R30SupportTryXyzrhwIndexedPrimitiveVB(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        INT b, UINT m, UINT n, UINT s, UINT p) noexcept;
    HRESULT R30SupportTryXyzrhwPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept;
    HRESULT R30SupportTryXyzrhwIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        UINT m, UINT n, UINT p, const void* idx,
        D3DFORMAT f, const void* v, UINT st) noexcept;
    HRESULT R30SupportCallLowerDrawPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept;
    HRESULT R30SupportCallLowerDrawIndexedPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        INT b, UINT m, UINT n, UINT s, UINT p) noexcept;
    HRESULT R30SupportCallLowerDrawPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept;
    HRESULT R30SupportCallLowerDrawIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT m, UINT n, UINT p,
        const void* idx, D3DFORMAT f, const void* v, UINT st) noexcept;

    // Preserve lower R22 raster guard lifetime and exact callback ordering.
    using R30SupportVoidCallback = void (*)(void*) noexcept;
    using R30SupportHResultCallback = HRESULT (*)(void*) noexcept;
    HRESULT R30SupportRunRasterReplayGuardCallback(
        IDirect3DDevice9* device, const char* site,
        R30SupportVoidCallback active, void* activeContext,
        R30SupportHResultCallback draw, void* drawContext) noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R30SupportLowerPrerequisiteStatus() noexcept;
    void* R30SupportDrawPrimitiveTarget() noexcept;
    void* R30SupportDrawIndexedPrimitiveTarget() noexcept;
    void* R30SupportDrawPrimitiveUPTarget() noexcept;
    void* R30SupportDrawIndexedPrimitiveUPTarget() noexcept;

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
    // Preserve independent lower R9 depth/stencil write eligibility policy.
    bool R30SupportLeftDrawMayWriteDepth(IDirect3DDevice9* device) noexcept;
    bool R30SupportLeftDrawMayWriteStencil(IDirect3DDevice9* device) noexcept;
    // Exact lower R9 depth-content write notification, without a new epoch.
    void R30SupportNoteMainDepthContentWrite() noexcept;
    // Preserve original R9 mono-backup invalidation and frame poisoning.
    // Raw D3D9 trampolines preserve original draw/present dispatch and
    // HRESULT without using higher R30 replay hooks or altering device state.
    HRESULT R30SupportCallRawDrawPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept;
    HRESULT R30SupportCallRawDrawIndexedPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, INT b,
        UINT m, UINT n, UINT s, UINT p) noexcept;
    HRESULT R30SupportCallRawDrawPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept;
    HRESULT R30SupportCallRawDrawIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        UINT m, UINT n, UINT p, const void* idx,
        D3DFORMAT f, const void* v, UINT st) noexcept;
    HRESULT R30SupportCallRawPresent(
        IDirect3DDevice9* d, const RECT* s, const RECT* dst,
        HWND w, const RGNDATA* r) noexcept;
    void R30SupportNoteStereoDrawWithoutMonoBackup() noexcept;
    void R30SupportReportStereoFailure(
        OutRunVR::StereoFailureReason reason,
        const char* site, HRESULT hr) noexcept;
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
    // The R9/R22 resource owner and depth-stencil safety predicates keep
    // their original failure and D3D9 state handling; no eager allocation.
    bool R30SupportEnsureStereoResources(IDirect3DDevice9* device) noexcept;
    bool R30SupportTryBootstrapRightDepth(IDirect3DDevice9* device) noexcept;
    bool R30SupportDepthTestActive(IDirect3DDevice9* device) noexcept;
    bool R30SupportStencilTestActive(IDirect3DDevice9* device) noexcept;
    // Raw lower-hook dispatch for R32 stereo target switches. The original
    // depth-hook absence fallback remains a direct D3D9 device call.
    HRESULT R30SupportCallOriginalSetRenderTarget(
        IDirect3DDevice9* device, DWORD index,
        IDirect3DSurface9* surface) noexcept;
    HRESULT R30SupportCallOriginalSetDepthStencilSurface(
        IDirect3DDevice9* device,
        IDirect3DSurface9* surface) noexcept;
    // Preserve the exact original R9 frame accounting, ordering and the
    // first-pose-sequence metadata latch. No new frame state or stereo policy.
    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept;
    void R30SupportRecordHudStereoDuplicate() noexcept;
    void R30SupportMarkFrameRightDrawFailed() noexcept;
    // Borrowed original lower hook target addresses. Do not change resolver
    // identity, hook ownership, device pointer or acquire-load semantics.
    void* R30SupportResetTarget() noexcept;
    void* R30SupportPresentTarget() noexcept;
    void* R30SupportDirectTransportTarget() noexcept;
    void* R30SupportSetRenderStateTarget() noexcept;
    IDirect3DDevice9* R30SupportInstalledDevice() noexcept;
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
    // R31 reads the shader epoch through R30 ABI, not textual .cpp inclusion.
    bool R30SupportCurrentShaderEpoch(
        std::uintptr_t& identity, std::uint64_t& serial) noexcept;
    void R30SupportResynchronizeShaderEpoch(
        IDirect3DDevice9* device) noexcept;
    void R30SupportInvalidateRendererStateAfterExternalRestore() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R30SupportRendererInstallStatus() noexcept;
    bool R30SupportPrimeTrackedRasterShadow(
        IDirect3DDevice9* device) noexcept;
}