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
}