#pragma once
#include <Windows.h>
#include <d3d9.h>
#include <d3d11.h>
#include <dxgi.h>
#include <wrl/client.h>
#include <cstdint>
#include "native_game_shared_desktop_admission.hpp"

namespace outrun::vr::dx11::live_game_frame {
// One process-local, opt-in, GPU-only game-frame presentation route.
// Opens the D3D11 BGRA shared allocation on the *original* D3D9Ex
// device. A failed import, GPU fence or StretchRect never replaces
// the game's Draw/Present/controls or its existing CPU fallback.
class NativeSharedDesktopBridge final {
public:
    NativeSharedDesktopBridge() = default;
    NativeSharedDesktopBridge(const NativeSharedDesktopBridge&) = delete;
    NativeSharedDesktopBridge& operator=(const NativeSharedDesktopBridge&) = delete;

    void reset() noexcept {
        source_.Reset();
        fence_.Reset();
        shared9_.Reset();
        game9Ex_.Reset();
        device11_.Reset();
        width_ = height_ = 0;
        generation_ = 0;
        pending_ = false;
        faulted_ = false;
    }

    [[nodiscard]] bool try_present(
        IDirect3DDevice9* game, IDirect3DSurface9* backbuffer,
        ID3D11Device* device, ID3D11DeviceContext* context,
        ID3D11Texture2D* source, std::uint32_t width,
        std::uint32_t height, std::uint64_t generation) noexcept {
        if (!game || !backbuffer || !device || !context || !source ||
            !width || !height || !generation)
            return false;

        D3D11_TEXTURE2D_DESC desc{};
        source->GetDesc(&desc);
        if (desc.Width != width || desc.Height != height ||
            desc.Format != DXGI_FORMAT_B8G8R8A8_UNORM ||
            desc.SampleDesc.Count != 1 || desc.SampleDesc.Quality != 0 ||
            desc.MipLevels != 1 || desc.ArraySize != 1 ||
            desc.Usage != D3D11_USAGE_DEFAULT || desc.CPUAccessFlags != 0 ||
            context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE)
            return false;
        Microsoft::WRL::ComPtr<ID3D11Device> actualDevice;
        context->GetDevice(actualDevice.GetAddressOf());
        if (!actualDevice || actualDevice.Get() != device)
            return false;
        // D3D11 CopyResource silently fails validation for a texture created
        // on another device. Never signal/publish uninitialized shared pixels
        // as a successful menu/car/race frame.
        Microsoft::WRL::ComPtr<ID3D11Device> sourceOwner;
        source->GetDevice(sourceOwner.GetAddressOf());
        if (!sourceOwner || sourceOwner.Get() != device)
            return false;

        // Confirm the real game destination independently of the Present
        // caller's admission proof. The shared D3D9Ex import is A8R8G8B8,
        // while an X8R8G8B8 backbuffer discards alpha on StretchRect. If a
        // driver refuses this conversion, the original D3D9 image remains
        // the fallback because only SUCCEEDED(StretchRect) returns true.
        D3DSURFACE_DESC destination{};
        if (FAILED(backbuffer->GetDesc(&destination)) ||
            destination.Width != width || destination.Height != height ||
            destination.MultiSampleType != D3DMULTISAMPLE_NONE ||
            !NativeSharedDesktopAdmission::destination_compatible(
                static_cast<std::uint32_t>(destination.Format),
                static_cast<std::uint32_t>(D3DFMT_A8R8G8B8),
                static_cast<std::uint32_t>(D3DFMT_X8R8G8B8)))
            return false;

        // A change in the producer, destination device, extent or
        // backbuffer generation retires both API views together.
        Microsoft::WRL::ComPtr<IDirect3DDevice9Ex> ex;
        if (FAILED(game->QueryInterface(
                __uuidof(IDirect3DDevice9Ex),
                reinterpret_cast<void**>(ex.GetAddressOf()))) || !ex)
            return false;
        if (!shared9_ || device11_.Get() != device ||
            game9Ex_.Get() != ex.Get() ||
            width_ != width || height_ != height ||
            generation_ != generation) {
            reset();
            D3D11_TEXTURE2D_DESC shared{};
            shared.Width = width;
            shared.Height = height;
            shared.MipLevels = 1;
            shared.ArraySize = 1;
            shared.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
            shared.SampleDesc.Count = 1;
            shared.Usage = D3D11_USAGE_DEFAULT;
            shared.BindFlags = D3D11_BIND_RENDER_TARGET |
                               D3D11_BIND_SHADER_RESOURCE;
            shared.MiscFlags = D3D11_RESOURCE_MISC_SHARED;
            if (FAILED(device->CreateTexture2D(
                    &shared, nullptr, source_.GetAddressOf())) || !source_) {
                reset();
                return false;
            }
            Microsoft::WRL::ComPtr<IDXGIResource> dxgi;
            HANDLE handle = nullptr;
            if (FAILED(source_.As(&dxgi)) || !dxgi ||
                FAILED(dxgi->GetSharedHandle(&handle)) || !handle) {
                reset();
                return false;
            }
            // A8R8G8B8 on D3D9Ex corresponds to B8G8R8A8 on D3D11.
            if (FAILED(ex->CreateTexture(
                    width, height, 1, D3DUSAGE_RENDERTARGET,
                    D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT,
                    shared9_.GetAddressOf(), &handle)) || !shared9_) {
                reset();
                return false;
            }
            D3D11_QUERY_DESC query{};
            query.Query = D3D11_QUERY_EVENT;
            if (FAILED(device->CreateQuery(
                    &query, fence_.GetAddressOf())) || !fence_) {
                reset();
                return false;
            }
            device11_ = device;
            game9Ex_ = ex;
            width_ = width;
            height_ = height;
            generation_ = generation;
        }
        if (faulted_ || !source_ || !fence_) return false;

        // Never overwrite an allocation while an earlier asynchronous
        // D3D11 CopyResource is still in flight. Old frames are discarded,
        // never presented late after a newer game Present.
        if (pending_) {
            const HRESULT result = context->GetData(
                fence_.Get(), nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
            if (result == S_FALSE) return false;
            if (result != S_OK) {
                faulted_ = true;
                return false;
            }
            pending_ = false;
        }
        context->CopyResource(source_.Get(), source);
        context->End(fence_.Get());
        context->Flush();
        pending_ = true;

        // Bounded same-Present completion check: no unbounded stall in the
        // gamepad/FFB loop. If the GPU is busy, the original D3D9 path wins.
        HRESULT status = context->GetData(
            fence_.Get(), nullptr, 0, D3D11_ASYNC_GETDATA_DONOTFLUSH);
        if (status == S_FALSE) {
            LARGE_INTEGER freq{}, started{}, now{};
            if (QueryPerformanceFrequency(&freq) && freq.QuadPart > 0 &&
                QueryPerformanceCounter(&started)) {
                for (std::uint32_t retry = 0; retry < 512 && status == S_FALSE;
                     ++retry) {
                    if (!QueryPerformanceCounter(&now) ||
                        now.QuadPart < started.QuadPart ||
                        (static_cast<std::uint64_t>(
                            now.QuadPart - started.QuadPart) * 2000u >=
                         static_cast<std::uint64_t>(freq.QuadPart)))
                        break;
                    status = context->GetData(
                        fence_.Get(), nullptr, 0,
                        D3D11_ASYNC_GETDATA_DONOTFLUSH);
                }
            }
        }
        if (status == S_FALSE) return false;
        if (status != S_OK) {
            faulted_ = true;
            return false;
        }
        pending_ = false;
        Microsoft::WRL::ComPtr<IDirect3DSurface9> sharedSurface;
        if (FAILED(shared9_->GetSurfaceLevel(
                0, sharedSurface.GetAddressOf())) || !sharedSurface)
            return false;
        // The caller suppresses its own StretchRect surface-mutation hook
        // while the source State mutex is held.
        return SUCCEEDED(game->StretchRect(
            sharedSurface.Get(), nullptr, backbuffer, nullptr, D3DTEXF_NONE));
    }
private:
    Microsoft::WRL::ComPtr<ID3D11Texture2D> source_;
    Microsoft::WRL::ComPtr<IDirect3DTexture9> shared9_;
    Microsoft::WRL::ComPtr<ID3D11Query> fence_;
    Microsoft::WRL::ComPtr<IDirect3DDevice9Ex> game9Ex_;
    Microsoft::WRL::ComPtr<ID3D11Device> device11_;
    std::uint32_t width_ = 0, height_ = 0;
    std::uint64_t generation_ = 0;
    bool pending_ = false;
    bool faulted_ = false;
};
} // namespace outrun::vr::dx11::live_game_frame
