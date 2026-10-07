#pragma once
// Explicit R32 functional-owner boundary consumed by the R33 final dispatcher.
//
// This interface is intentionally behavior-neutral. R32 still owns the same
// implementation and R33 still owns the same physical hooks; the boundary only
// prevents R33 from depending on R32 anonymous/private helper names so the
// textual implementation include can be retired in a later bounded seam.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <cstdint>
#include <d3d9.h>
#include <type_traits>
#include <utility>
#include "../ipc/protocol.hpp"
#include "../runtime_eligibility.hpp"

#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

namespace OutRunVRStereo
{
    using R32HResultCallback = HRESULT (*)(void*) noexcept;
    using R32BoolCallback = bool (*)(void*) noexcept;

    bool R32ReviewEffectIsFragileLive(
        IDirect3DDevice9* device, bool& fragile) noexcept;
    bool R32ReviewGetSavedViewport(
        IDirect3DDevice9* device, D3DVIEWPORT9& viewport) noexcept;
    bool R32ReviewSetWvpBatch(
        IDirect3DDevice9* device, const float* constants) noexcept;
    bool R32ReviewRestoreRightPassState(
        IDirect3DDevice9* device,
        IDirect3DSurface9* savedRt,
        IDirect3DSurface9* savedDepth,
        const D3DVIEWPORT9& savedViewport,
        const float* originalConstants,
        bool restoreWvp) noexcept;
    void R32ReviewObserveFrameWorkload(
        IDirect3DDevice9* device,
        D3DPRIMITIVETYPE type,
        UINT primitiveCount,
        bool indexed,
        bool up) noexcept;

    HRESULT R32ReviewRunLowerFailClosedCallback(
        IDirect3DDevice9* device,
        R32HResultCallback callback,
        void* context) noexcept;
    bool R32ReviewResolveDirectTransportCallback(
        IDirect3DDevice9* device,
        std::uint32_t frameId,
        R32BoolCallback callback,
        void* context) noexcept;
    HRESULT R32ReviewRunResetLifecycleCallback(
        IDirect3DDevice9* device,
        R32HResultCallback callback,
        void* context) noexcept;
    HRESULT R32ReviewRunPresentTelemetryCallback(
        IDirect3DDevice9* device,
        R32HResultCallback callback,
        void* context) noexcept;

    using R32VoidCallback = void (*)(void*) noexcept;

    struct R32ReviewOwnedResult
    {
        bool handled = false;
        HRESULT hr = D3D_OK;
    };

    struct R32ReviewFastWorldConstants
    {
        float originalConstants[16]{};
        float eyeConstants[2][16]{};
        std::uint32_t poseSequence = 0;
        OutRunVRRenderer::LatchedStereoFrame stereoFrame{};
    };

    enum class R32ReviewScreenSpaceKind : std::uint8_t
    {
        None,
        Hud2D,
        FlatPerspectiveEffect
    };

    class R32ReviewInternalStereoPassScope final
    {
    public:
        R32ReviewInternalStereoPassScope() noexcept;
        ~R32ReviewInternalStereoPassScope();
        R32ReviewInternalStereoPassScope(
            const R32ReviewInternalStereoPassScope&) = delete;
        R32ReviewInternalStereoPassScope& operator=(
            const R32ReviewInternalStereoPassScope&) = delete;
    private:
        bool previous_ = false;
    };

    bool R32ReviewTelemetryEnabled() noexcept;
    bool R32ReviewIsGameDevice(IDirect3DDevice9* device) noexcept;
    bool R32ReviewInternalStereoPass() noexcept;
    bool R32ReviewStereoWanted() noexcept;
    bool R32ReviewTargetIsBackBuffer() noexcept;
    void R32ReviewFailClosedResetBaselineState() noexcept;
    void R32ReviewArmStereoRecoverySafety(
        std::uint64_t extraPresents = 2) noexcept;

    HRESULT R32ReviewRunRasterReplayGuardCallback(
        IDirect3DDevice9* device,
        const char* site,
        R32VoidCallback activeCallback,
        void* activeContext,
        R32HResultCallback drawCallback,
        void* drawContext) noexcept;

    std::uint64_t R32ReviewMainDepthGeneration() noexcept;
    bool R32ReviewMainDepthHasStencil() noexcept;
    bool R32ReviewLeftDrawMayWriteDepth(IDirect3DDevice9* device) noexcept;
    bool R32ReviewLeftDrawMayWriteStencil(IDirect3DDevice9* device) noexcept;
    void R32ReviewInvalidateRightDepthStencilSync(
        bool invalidateDepth, bool invalidateStencil) noexcept;
    bool R32ReviewRightDepthInSync() noexcept;
    bool R32ReviewRightStencilInSync() noexcept;
    void R32ReviewNoteStereoDrawWithoutMonoBackup() noexcept;
    void R32ReviewNoteMainDepthContentWrite() noexcept;
    void R32ReviewReportStereoFailure(
        OutRunVR::StereoFailureReason reason,
        const char* site, HRESULT hr = E_FAIL) noexcept;
    void R32ReviewNoteRestoreFailure(const char* what) noexcept;

    IDirect3DSurface9* R32ReviewTrackedRenderTarget() noexcept;
    IDirect3DSurface9* R32ReviewTrackedDepthStencil() noexcept;
    IDirect3DSurface9* R32ReviewRightEyeSurface() noexcept;
    IDirect3DSurface9* R32ReviewRightEyeDepth() noexcept;
    bool R32ReviewEnsureStereoResources(IDirect3DDevice9* device) noexcept;
    bool R32ReviewTryBootstrapRightDepth(IDirect3DDevice9* device) noexcept;
    bool R32ReviewDepthTestActive(IDirect3DDevice9* device) noexcept;
    bool R32ReviewStencilTestActive(IDirect3DDevice9* device) noexcept;
    HRESULT R32ReviewSetRenderTarget(
        IDirect3DDevice9* device, DWORD index,
        IDirect3DSurface9* surface) noexcept;
    HRESULT R32ReviewSetDepthStencilSurface(
        IDirect3DDevice9* device, IDirect3DSurface9* surface) noexcept;

    std::uintptr_t R32ReviewCurrentVertexShaderIdentity() noexcept;
    bool R32ReviewLiveVertexShaderMatches(
        IDirect3DDevice9* device, std::uintptr_t expected) noexcept;
    std::uint32_t R32ReviewFrameStereoPoseSequence() noexcept;
    void R32ReviewRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept;
    void R32ReviewRecordHudStereoDuplicate() noexcept;
    void R32ReviewMarkFrameRightDrawFailed() noexcept;

    bool R32ReviewStableStereoBase(IDirect3DDevice9* device) noexcept;
    bool R32ReviewFragileEffectCached(
        IDirect3DDevice9* device, bool& fragile) noexcept;
    void R32ReviewNoteStableTwoEyeDraw() noexcept;

    void R32ReviewObserveDispatchDraw(IDirect3DDevice9* device) noexcept;
    void R32ReviewDiscardUnreliableDrawCaches() noexcept;
    void R32ReviewNoteDispatchFallback() noexcept;
    void R32ReviewNoteDispatchFastWorld() noexcept;
    void R32ReviewNoteDispatchFragile() noexcept;
    void R32ReviewNoteDispatchHud() noexcept;
    void R32ReviewNoteDispatchUnstable() noexcept;
    bool R32ReviewBuildFastWorldConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        R32ReviewFastWorldConstants& out) noexcept;

    R32ReviewScreenSpaceKind
    R32ReviewClassifyScreenSpacePass(IDirect3DDevice9* device) noexcept;
    bool R32ReviewBuildScreenSpaceEyeConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        R32ReviewScreenSpaceKind kind,
        float original[16], float eyeConstants[2][16],
        float eyeScale[2], float eyeOffset[2]) noexcept;
    void R32ReviewNoteScreenSpaceFovDraw() noexcept;

    HRESULT R32ReviewTryXyzrhwPrimitiveVB(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount) noexcept;
    HRESULT R32ReviewTryXyzrhwIndexedPrimitiveVB(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount) noexcept;
    HRESULT R32ReviewTryXyzrhwPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride) noexcept;
    HRESULT R32ReviewTryXyzrhwIndexedPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride) noexcept;

    HRESULT R32ReviewCallRawDrawPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount) noexcept;
    HRESULT R32ReviewCallRawDrawIndexedPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount) noexcept;
    HRESULT R32ReviewCallRawDrawPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride) noexcept;
    HRESULT R32ReviewCallRawDrawIndexedPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride) noexcept;
    HRESULT R32ReviewCallRawPresent(
        IDirect3DDevice9* device,
        const RECT* sourceRect, const RECT* destRect,
        HWND destWindowOverride, const RGNDATA* dirtyRegion) noexcept;

    HRESULT R32ReviewCallLowerDrawPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount) noexcept;
    HRESULT R32ReviewCallLowerDrawIndexedPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount) noexcept;
    HRESULT R32ReviewCallLowerDrawPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride) noexcept;
    HRESULT R32ReviewCallLowerDrawIndexedPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride) noexcept;

    OutRunVR::RuntimeEligibility::InstallState
    R32ReviewPrerequisiteStatus() noexcept;
    void* R32ReviewResetTarget() noexcept;
    void* R32ReviewPresentTarget() noexcept;
    void* R32ReviewDirectTransportTarget() noexcept;
    void* R32ReviewSetRenderStateTarget() noexcept;
    void* R32ReviewDrawPrimitiveTarget() noexcept;
    void* R32ReviewDrawIndexedPrimitiveTarget() noexcept;
    void* R32ReviewDrawPrimitiveUPTarget() noexcept;
    void* R32ReviewDrawIndexedPrimitiveUPTarget() noexcept;
    IDirect3DDevice9* R32ReviewInstalledDevice() noexcept;

    template <typename DrawCallback, typename ActiveCallback>
    HRESULT R32ReviewRunRasterReplayGuard(
        IDirect3DDevice9* device,
        const char* site,
        DrawCallback&& drawCallback,
        ActiveCallback&& activeCallback) noexcept
    {
        using DrawFn = std::remove_reference_t<DrawCallback>;
        using ActiveFn = std::remove_reference_t<ActiveCallback>;
        auto drawTrampoline = [](void* context) noexcept -> HRESULT {
            return (*static_cast<DrawFn*>(context))();
        };
        auto activeTrampoline = [](void* context) noexcept {
            (*static_cast<ActiveFn*>(context))();
        };
        return R32ReviewRunRasterReplayGuardCallback(
            device, site, activeTrampoline, &activeCallback,
            drawTrampoline, &drawCallback);
    }

    template <typename Callback>
    HRESULT R32ReviewRunLowerFailClosed(
        IDirect3DDevice9* device, Callback&& callback) noexcept
    {
        using Fn = std::remove_reference_t<Callback>;
        auto trampoline = [](void* context) noexcept -> HRESULT {
            return (*static_cast<Fn*>(context))();
        };
        return R32ReviewRunLowerFailClosedCallback(
            device, trampoline, &callback);
    }

    template <typename Callback>
    bool R32ReviewResolveDirectTransport(
        IDirect3DDevice9* device,
        std::uint32_t frameId,
        Callback&& callback) noexcept
    {
        using Fn = std::remove_reference_t<Callback>;
        auto trampoline = [](void* context) noexcept -> bool {
            return (*static_cast<Fn*>(context))();
        };
        return R32ReviewResolveDirectTransportCallback(
            device, frameId, trampoline, &callback);
    }

    template <typename Callback>
    HRESULT R32ReviewRunResetLifecycle(
        IDirect3DDevice9* device, Callback&& callback) noexcept
    {
        using Fn = std::remove_reference_t<Callback>;
        auto trampoline = [](void* context) noexcept -> HRESULT {
            return (*static_cast<Fn*>(context))();
        };
        return R32ReviewRunResetLifecycleCallback(
            device, trampoline, &callback);
    }

    template <typename Callback>
    HRESULT R32ReviewRunPresentTelemetry(
        IDirect3DDevice9* device, Callback&& callback) noexcept
    {
        using Fn = std::remove_reference_t<Callback>;
        auto trampoline = [](void* context) noexcept -> HRESULT {
            return (*static_cast<Fn*>(context))();
        };
        return R32ReviewRunPresentTelemetryCallback(
            device, trampoline, &callback);
    }
}
