#pragma once

#include <d3d9.h>
#include <cstdint>

namespace OutRunVRRenderer
{
    struct LatchedStereoFrame;
}

namespace OutRunVRStereo
{
    class InternalStereoPassScope final
    {
    public:
        InternalStereoPassScope() noexcept;
        ~InternalStereoPassScope();
        InternalStereoPassScope(const InternalStereoPassScope&) = delete;
        InternalStereoPassScope& operator=(const InternalStereoPassScope&) = delete;
    private:
        bool previous_ = false;
    };

    bool EnsureStereoResourcesForDispatch(IDirect3DDevice9* device) noexcept;
    bool TryBootstrapRightDepthForDispatch(IDirect3DDevice9* device) noexcept;
    bool DepthTestActiveForDispatch(IDirect3DDevice9* device) noexcept;
    bool StencilTestActiveForDispatch(IDirect3DDevice9* device) noexcept;

    IDirect3DSurface9* TrackedRenderTargetSnapshot() noexcept;
    IDirect3DSurface9* RightEyeSurfaceSnapshot() noexcept;
    IDirect3DSurface9* RightEyeDepthSnapshot() noexcept;

    HRESULT SetRawRenderTarget0(
        IDirect3DDevice9* device, IDirect3DSurface9* surface) noexcept;
    HRESULT SetRawDepthStencil(
        IDirect3DDevice9* device, IDirect3DSurface9* surface) noexcept;

    std::uintptr_t CurrentVertexShaderIdentitySnapshot() noexcept;
    std::uintptr_t MaskCurrentVertexShaderIdentity() noexcept;
    void RestoreCurrentVertexShaderIdentityIfEmpty(
        std::uintptr_t savedIdentity) noexcept;
    std::uint32_t CurrentFrameStereoPoseSequence() noexcept;
    std::uint64_t CurrentPresentEpochSnapshot() noexcept;
    HRESULT SetRawStereoWvpBatch(
        IDirect3DDevice9* device, const float* constants) noexcept;
    void LatchFrameStereoMetadataIfUnset(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept;

    void RecordWorldStereoDuplicate() noexcept;
    void RecordHudStereoDuplicate() noexcept;
    void MarkFrameRightDrawFailed() noexcept;
    void RecordRestoreFailure(const char* what) noexcept;
}
