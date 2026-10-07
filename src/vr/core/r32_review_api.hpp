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
