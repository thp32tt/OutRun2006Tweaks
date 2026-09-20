#pragma once

// ABI-compatible declaration of the public VR extension exported by
// Detegr/dxvk-openRBRVR.  The upstream implementation is zlib-licensed.
// This project does not depend on Vulkan headers here; dispatchable Vulkan
// handles are represented as opaque pointers because only the D3D9-facing
// methods below are used by OutRun.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <Unknwn.h>
#include <d3d9.h>
#include <cstdint>

namespace OutRunVR::OpenRbrDxvk
{
    struct TextureVrDesc
    {
        std::uint64_t image{};
        void* device{};
        void* physicalDevice{};
        void* instance{};
        void* queue{};
        std::uint32_t queueFamilyIndex{};
        std::uint32_t width{};
        std::uint32_t height{};
        std::uint32_t format{};
        std::uint32_t sampleCount{};
    };

    struct OxrVkDeviceDesc
    {
        void* device{};
        void* physicalDevice{};
        void* instance{};
        std::uint32_t queueIndex{};
        std::uint32_t queueFamilyIndex{};
    };

    inline constexpr std::uint32_t AllLayers = 0xffffffffu;

    using ChangeSpirvMultiViewFn = int (*)(
        std::uint32_t* data,
        std::uint32_t size,
        std::uint32_t* dataOut,
        std::uint32_t* sizeOut,
        std::uint32_t floatRegisterIndex,
        std::uint32_t offset,
        std::int8_t optimize);

    using OptimizeSpirvFn = int (*)(
        std::uint32_t* data,
        std::uint32_t size,
        std::uint32_t* dataOut,
        std::uint32_t* sizeOut);
}

// Public ABI from dxvk-openRBRVR/src/d3d9/d3d9_vr.h.
// Keep new methods appended to preserve the upstream vtable order.
// {7E272B32-A49C-46C7-B1A4-EF52936BEC87}
MIDL_INTERFACE("7e272b32-a49c-46c7-b1a4-ef52936bec87")
IDirect3DVR9OutRun : public IUnknown
{
public:
    virtual HRESULT STDMETHODCALLTYPE GetVRDesc(
        IDirect3DSurface9* surface,
        OutRunVR::OpenRbrDxvk::TextureVrDesc* desc) = 0;
    virtual HRESULT STDMETHODCALLTYPE TransferSurfaceForVR(
        IDirect3DSurface9* surface) = 0;
    virtual HRESULT STDMETHODCALLTYPE BeginVRSubmit() = 0;
    virtual HRESULT STDMETHODCALLTYPE EndVRSubmit() = 0;
    virtual HRESULT STDMETHODCALLTYPE LockDevice() = 0;
    virtual HRESULT STDMETHODCALLTYPE UnlockDevice() = 0;
    virtual HRESULT STDMETHODCALLTYPE WaitDeviceIdle(BOOL flush) = 0;
    virtual HRESULT STDMETHODCALLTYPE WaitGraphicsQueueIdle(BOOL flush) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetOXRVkDeviceDesc(
        OutRunVR::OpenRbrDxvk::OxrVkDeviceDesc* desc) = 0;
    virtual HRESULT STDMETHODCALLTYPE Flush() = 0;
    virtual HRESULT STDMETHODCALLTYPE LockSubmissionQueue() = 0;
    virtual HRESULT STDMETHODCALLTYPE UnlockSubmissionQueue() = 0;
    virtual HRESULT STDMETHODCALLTYPE ImportFence(
        HANDLE handle, std::uint64_t value) = 0;
    virtual HRESULT STDMETHODCALLTYPE SignalFence(
        std::uint64_t value) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetShaderHash(
        IDirect3DVertexShader9* shader, char** out) = 0;
    virtual HRESULT STDMETHODCALLTYPE PatchSPIRVToVertexShader(
        IDirect3DVertexShader9* shader,
        const std::uint32_t* data,
        std::uint32_t size) = 0;
    virtual HRESULT STDMETHODCALLTYPE CreateMultiViewRenderTarget(
        UINT width,
        UINT height,
        D3DFORMAT format,
        D3DMULTISAMPLE_TYPE multiSample,
        DWORD multiSampleQuality,
        BOOL lockable,
        IDirect3DSurface9** surface,
        HANDLE* sharedHandle,
        UINT views) = 0;
    virtual HRESULT STDMETHODCALLTYPE CreateMultiViewDepthStencilSurface(
        UINT width,
        UINT height,
        D3DFORMAT format,
        D3DMULTISAMPLE_TYPE multiSample,
        DWORD multiSampleQuality,
        BOOL discard,
        IDirect3DSurface9** surface,
        HANDLE* sharedHandle,
        UINT views) = 0;
    virtual HRESULT STDMETHODCALLTYPE CopySurfaceLayers(
        IDirect3DSurface9* source,
        IDirect3DSurface9** destinations,
        UINT layerCount) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetSPIRVShaderCode(
        IDirect3DVertexShader9* shader,
        std::uint32_t* out,
        std::uint32_t* size) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetShaderConstantCount(
        IDirect3DVertexShader9* shader,
        std::uint32_t* out) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetShaderConstantCount(
        IDirect3DVertexShader9* shader,
        std::uint32_t count) = 0;
    virtual HRESULT STDMETHODCALLTYPE EnableMultiView(bool enable) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetMultiviewSurfaceLayer(
        IDirect3DSurface9* surface,
        std::uint32_t layer) = 0;
};

namespace OutRunVR::OpenRbrDxvk
{
    using Direct3DCreateVrFn = HRESULT (WINAPI*)(
        IDirect3DDevice9* device,
        IDirect3DVR9OutRun** interfaceOut);
}
