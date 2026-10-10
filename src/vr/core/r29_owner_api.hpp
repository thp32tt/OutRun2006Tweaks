#pragma once
// R29 functional-owner ABI consumed by the independently compiled R30 TU.
// Preserve the original R29 classification, install epoch, stereo recovery,
// and two-eye accounting. This API does not install or relocate physical hooks.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <cstdint>
#include <d3d9.h>
#include "../runtime_eligibility.hpp"
#include "../ipc/protocol.hpp"

namespace OutRunVRStereo
{
    bool R29OwnerStableStereoBase(IDirect3DDevice9* device) noexcept;
    bool R29OwnerFragileEffectCached(
        IDirect3DDevice9* device, bool& fragile) noexcept;
    void R29OwnerArmMonoSafety(std::uint64_t extraPresents = 2) noexcept;
    void R29OwnerNoteStableTwoEyeDraw() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerInstallStatus() noexcept;
    // Snapshot of the *existing* R29/lower draw and resource state. Borrowed
    // surfaces must not be released or retained by the consumer. This is a
    // value-only transfer; the R29 TU remains sole owner of those resources.
    struct R29OwnerFrameSnapshot
    {
        UINT width = 0;
        UINT height = 0;
        IDirect3DSurface9* backBuffer = nullptr;
        IDirect3DSurface9* rightEyeSurface = nullptr;
        IDirect3DSurface9* rightEyeDepth = nullptr;
        IDirect3DSurface9* trackedDepthStencil = nullptr;
        std::uint64_t presentEpoch = 0;
        std::uint32_t poseSequence = 0;
        bool hadWorldStereo = false;
        bool hadDuplicatedDraw = false;
        bool rightDrawFailed = false;
        bool stereoIncomplete = false;
        bool rightDepthSynchronized = false;
        bool rightStencilSynchronized = false;
    };
    R29OwnerFrameSnapshot R29OwnerCaptureFrameSnapshot() noexcept;
    // Only R29 accesses lower-chain IPC and adapter lifetime state.
    // Consumers receive copied dimensions/identity, never the shared pointer.
    bool R29OwnerRecommendedEyeExtent(std::uint32_t eye,
        std::uint32_t& width, std::uint32_t& height) noexcept;
    struct R29OwnerTransportIdentity
    {
        std::uint32_t hostPid = 0;
        std::uint32_t hostAdapterLuidLow = 0;
        std::uint32_t hostAdapterLuidHigh = 0;
    };
    bool R29OwnerTryGetDirectTransportIdentity(
        R29OwnerTransportIdentity& out) noexcept;
    // Consolidated lower draw/depth/restore services. These forward existing
    // R9/R23 behavior without creating a second owner or hook instance.
    bool R29OwnerEnsureStereoResources(IDirect3DDevice9* device) noexcept;
    bool R29OwnerTryBootstrapRightDepth(IDirect3DDevice9* device) noexcept;
    bool R29OwnerDepthTestActive(IDirect3DDevice9* device) noexcept;
    bool R29OwnerStencilTestActive(IDirect3DDevice9* device) noexcept;
    bool R29OwnerLeftDrawMayWriteDepth(IDirect3DDevice9* device) noexcept;
    bool R29OwnerLeftDrawMayWriteStencil(IDirect3DDevice9* device) noexcept;
    void R29OwnerNoteMainDepthContentWrite() noexcept;
    void R29OwnerNoteStereoDrawWithoutMonoBackup() noexcept;
    void R29OwnerUndoStereoDrawCount() noexcept;
    IDirect3DSurface9* R29OwnerBorrowTrackedRenderTarget() noexcept;
    void R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(IDirect3DDevice9* device) noexcept;
    void R29OwnerNoteRestoreFailure(const char* site) noexcept;
    // Lower-owned original-hook and frame-failure services.
    void R29OwnerReportStereoFailure(
        OutRunVR::StereoFailureReason reason,
        const char* site, HRESULT hr) noexcept;
    void R29OwnerMarkRightDrawFailed() noexcept;
    HRESULT R29OwnerCallOriginalSetRenderTarget(
        IDirect3DDevice9* device, DWORD index,
        IDirect3DSurface9* surface) noexcept;
    HRESULT R29OwnerCallOriginalSetDepthStencilSurface(
        IDirect3DDevice9* device, IDirect3DSurface9* surface) noexcept;
    bool R29OwnerRestoreRightPassState(
        IDirect3DDevice9* device, IDirect3DSurface9* target,
        IDirect3DSurface9* depth, const D3DVIEWPORT9& viewport,
        const float* originalWvp, bool restoreWvp) noexcept;
    bool R29OwnerStereoWanted() noexcept;
    bool R29OwnerTargetIsBackBuffer() noexcept;
    bool R29OwnerExchangeInternalStereoPass(bool active) noexcept;

    // R84: R29 is the sole owner of frame counters, latched pose metadata,
    // lower shader epoch and matrix helpers. All pointers remain borrowed.
    void R29OwnerRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept;
    void R29OwnerRecordXyzrhwWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept;
    void R29OwnerRecordHudStereoDuplicate() noexcept;
    std::uintptr_t R29OwnerCurrentVertexShaderIdentity() noexcept;
    std::uintptr_t R29OwnerExchangeVertexShaderIdentity(
        std::uintptr_t identity) noexcept;
    void R29OwnerRestoreVertexShaderIdentityIfEmpty(
        std::uintptr_t identity) noexcept;
    bool R29OwnerCurrentShaderEpoch(
        std::uintptr_t& identity, std::uint64_t& serial) noexcept;
    void R29OwnerResynchronizeShaderEpoch(
        IDirect3DDevice9* device) noexcept;
    D3DMATRIX R29OwnerIdentityMatrix() noexcept;
    D3DMATRIX R29OwnerMatrixFromQuaternionTranslation(
        const float orientation[4], const float position[3],
        float positionScale) noexcept;
    D3DMATRIX R29OwnerInverseRigid(const D3DMATRIX& matrix) noexcept;
    D3DMATRIX R29OwnerProjectionFromFov(
        const D3DMATRIX& base, const OutRunVR::SharedFov& fov) noexcept;
    D3DMATRIX R29OwnerMultiplyMatrix(
        const D3DMATRIX& a, const D3DMATRIX& b) noexcept;
    D3DMATRIX R29OwnerTransposeMatrix(const D3DMATRIX& matrix) noexcept;
    bool R29OwnerMatrixFinite(const D3DMATRIX& matrix) noexcept;
    bool R29OwnerInvertMatrix(
        const D3DMATRIX& matrix, D3DMATRIX& inverse) noexcept;
    bool R29OwnerGetInverseProjection(
        const D3DMATRIX& matrix, D3DMATRIX& inverse) noexcept;

    // Exact original lower R9 dispatch: same physical trampoline, arguments,
    // HRESULT and hook lifetime; no new hooks or higher-R30 recursion.
    HRESULT R29OwnerCallRawDrawPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept;
    HRESULT R29OwnerCallRawDrawIndexedPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, INT b,
        UINT m, UINT n, UINT s, UINT p) noexcept;
    HRESULT R29OwnerCallRawDrawPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        UINT p, const void* data, UINT st) noexcept;
    HRESULT R29OwnerCallRawDrawIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT m,
        UINT n, UINT p, const void* idx, D3DFORMAT f,
        const void* v, UINT st) noexcept;
    HRESULT R29OwnerCallRawPresent(
        IDirect3DDevice9* d, const RECT* s, const RECT* dst,
        HWND w, const RGNDATA* r) noexcept;

    // R84 Windows split preflight: expose original hook install targets and
    // game-device pointer; these do not allocate or install hooks.
    IDirect3DDevice9* R29OwnerGameDevice() noexcept;
    void* R29OwnerPresentTarget() noexcept;
    void* R29OwnerResetTarget() noexcept;
    void* R29OwnerDrawPrimitiveTarget() noexcept;
    void* R29OwnerDrawIndexedPrimitiveTarget() noexcept;
    void* R29OwnerDrawPrimitiveUPTarget() noexcept;
    void* R29OwnerDrawIndexedPrimitiveUPTarget() noexcept;
    bool R29OwnerSetWvpOneRegisterAtATime(
        IDirect3DDevice9* device, const float* constants) noexcept;

    // Additional R84 lower-state boundary for independently linked R30 support.
    bool R29OwnerIsGameDevice(IDirect3DDevice9* device) noexcept;
    bool R29OwnerInternalStereoPassActive() noexcept;
    bool R29OwnerStereoBaselineSeeded() noexcept;
    std::uint64_t R29OwnerMainDepthGeneration() noexcept;
    bool R29OwnerMainDepthHasStencil() noexcept;
    void R29OwnerInvalidateRightDepthStencilSync(bool invalidateDepth, bool invalidateStencil) noexcept;
    bool R29OwnerRightDepthInSync() noexcept;
    bool R29OwnerRightStencilInSync() noexcept;
    bool R29OwnerAnyAuxRenderTargetActive() noexcept;
    bool R29OwnerTryGetTrackedViewport(D3DVIEWPORT9& viewport) noexcept;
    bool R29OwnerOverlayReadyForTransport() noexcept;
    void R29OwnerNoteSafeAckBackpressure() noexcept;
    bool R29OwnerDirectTransportResourcesReady() noexcept;
    bool R29OwnerEnsureDirectTransportResources(IDirect3DDevice9* device) noexcept;
    void R29OwnerReleaseDirectAckState() noexcept;
    void R29OwnerReleaseDirectTransportInterop() noexcept;
    void R29OwnerInvalidateEffectStateCache() noexcept;
    void R29OwnerInvalidateTrackedRasterShadow() noexcept;
    void R29OwnerInvalidateLiveStateSample() noexcept;
    bool R29OwnerPrimeTrackedRasterShadow(IDirect3DDevice9* device) noexcept;
    void R29OwnerSetStereoRecoverySafetyThroughEpoch(std::uint64_t throughEpoch) noexcept;
    bool R29OwnerFrameIdAtOrAfter(std::uint32_t candidate, std::uint32_t reference) noexcept;
    void R29OwnerFailClosedResetBaselineState() noexcept;
    void R29OwnerArmStereoRecoverySafety(std::uint64_t extraPresents) noexcept;
    IDirect3DDevice9* R29OwnerInstalledDevice() noexcept;

    using R29OwnerVoidCallback = void (*)(void*) noexcept;
    using R29OwnerHResultCallback = HRESULT (*)(void*) noexcept;
    HRESULT R29OwnerRunRasterReplayGuardCallback(
        IDirect3DDevice9* device, const char* site,
        R29OwnerVoidCallback active, void* activeContext,
        R29OwnerHResultCallback draw, void* drawContext) noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerLowerPrerequisiteStatus() noexcept;

    // R29 physical owner of R13 DirectGPU ring, fence and publication state.
    void R29OwnerNoteDirectTransportRingBackpressure() noexcept;
    std::uint64_t R29OwnerDirectTransportRingBackpressureCount() noexcept;
    void R29OwnerSetActiveDirectTransportSlot(std::uint32_t slot) noexcept;
    void R29OwnerMarkDirectTransportSlotPending(
        std::uint32_t slot, std::uint32_t frameId) noexcept;
    struct R29OwnerDirectTransportPublication
    {
        bool published = false;
        std::uint32_t frameId = 0;
    };
    R29OwnerDirectTransportPublication
    R29OwnerGetDirectTransportSlotPublication(
        std::uint32_t slot) noexcept;
    HRESULT R29OwnerPollDirectTransportSlotProducer(
        std::uint32_t slot) noexcept;
    void R29OwnerRetireDirectTransportSlotPublication(
        std::uint32_t slot) noexcept;
    bool R29OwnerTryGetGpuCompletionSnapshot(
        std::uint32_t completed[OutRunVR::RenderFrameRingSize]) noexcept;
    struct R29OwnerDirectTransportCopyResult
    {
        HRESULT hr = D3D_OK;
        bool copyFailed = false;
    };
    R29OwnerDirectTransportCopyResult
    R29OwnerCopyDirectTransportEyesAndIssueFence(
        IDirect3DDevice9* device, std::uint32_t index,
        IDirect3DSurface9* left, IDirect3DSurface9* right) noexcept;
    struct R29OwnerEffectTelemetrySnapshot
    {
        DWORD alphaBlend = FALSE;
        DWORD alphaTest = FALSE;
        DWORD zWrite = TRUE;
    };
    bool R29OwnerTryGetEffectTelemetrySnapshot(
        R29OwnerEffectTelemetrySnapshot& out) noexcept;
    bool R29OwnerValidateVerifiedWvp(
        IDirect3DDevice9* device,
        const float* verified, float* live) noexcept;

    // R28/R29 renderer semantic queries are lower-TU only. R30 receives
    // explicit responses instead of relying on lower .cpp forward declarations.
    bool R29OwnerGetR28VerifiedProjection(float outProjection[16],
        std::uint32_t& generation, std::uint32_t& poseSequence) noexcept;
    void R29OwnerInvalidateRendererStateAfterExternalRestore() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R29OwnerRendererInstallStatus() noexcept;

    // Borrow lower hook entry addresses; the R30 TU never resolves them.
    void* R29OwnerResetR22Target() noexcept;
    void* R29OwnerPresentR13Target() noexcept;
    void* R29OwnerDirectTransportR13Target() noexcept;
    void* R29OwnerSetRenderStateR29Target() noexcept;
}