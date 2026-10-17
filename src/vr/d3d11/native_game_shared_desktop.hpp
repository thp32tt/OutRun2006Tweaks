#pragma once
#include <Windows.h>
#include <d3d9.h>
#include <d3d11.h>
#include <dxgi.h>
#include <wrl/client.h>
#include <cstdint>
#include "native_game_shared_desktop_admission.hpp"
#include "native_game_shared_desktop_rollback.hpp"
#include "native_game_shared_desktop_backup.hpp"
#include "native_game_shared_desktop_source.hpp"

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
        // D3D9 DEFAULT-pool backups cannot survive Reset/owner/transport changes.
        for (auto& backup : backups_) backup.Reset();
        for (auto& key : backupKeys_) key = {};
        source_.Reset();
        resolvedSource_.Reset();
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
        std::uint32_t height, std::uint64_t generation,
        const RECT& visibleRegion) noexcept {
        return try_present_regions(game, backbuffer, device, context, source,
                                   width, height, generation, &visibleRegion, 1u);
    }

    // Multi-dirty menu/car/race Presents copy the exact GPU-rendered tiles
    // rather than CPU readback or their bounding box (which contains original
    // D3D9-authored pixels). The D3D9 writes are rolled back if any blit fails.
    [[nodiscard]] bool try_present_regions(
        IDirect3DDevice9* game, IDirect3DSurface9* backbuffer,
        ID3D11Device* device, ID3D11DeviceContext* context,
        ID3D11Texture2D* source, std::uint32_t width,
        std::uint32_t height, std::uint64_t generation,
        const RECT* visibleRegions, std::uint32_t regionCount) noexcept {
        if (!game || !backbuffer || !device || !context || !source ||
            !width || !height || !generation || !visibleRegions ||
            !regionCount ||
            regionCount > GameNativeDirtyRegionCoverage::kMaxPartitionRects ||
            width > 0x7fffffffu || height > 0x7fffffffu)
            return false;
        // Derive the full list before any GPU command. Multi-dirty copies
        // take exact tile backups, not the area spanning untouched game HUD.
        std::array<GameNativePresentRegion,
                   GameNativeDirtyRegionCoverage::kMaxPartitionRects> regions{};
        for (std::uint32_t i = 0; i < regionCount; ++i) {
            const RECT& rect = visibleRegions[i];
            if (rect.left < 0 || rect.top < 0 ||
                rect.right <= rect.left || rect.bottom <= rect.top ||
                static_cast<std::uint32_t>(rect.right) > width ||
                static_cast<std::uint32_t>(rect.bottom) > height)
                return false;
            regions[i] = {rect.left, rect.top, rect.right, rect.bottom};
        }
        const auto rollbackPlan = NativeSharedDesktopRollbackPlan::select(
            width, height, regions.data(), regionCount);
        if (!rollbackPlan.valid) return false;

        D3D11_TEXTURE2D_DESC desc{};
        source->GetDesc(&desc);
        if (desc.Width != width || desc.Height != height ||
            desc.Format != DXGI_FORMAT_B8G8R8A8_UNORM ||
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
        // The source may be a real multisampled game color target. CopyResource
        // cannot transfer MSAA into a one-sample D3D9Ex shared texture:
        // preflight a full GPU ResolveSubresource before any D3D9 pixel write.
        // Never treat an unsupported depth, copy-only MSAA or array source as
        // a complete menu/car/race frame.
        UINT sourceFormatSupport = 0u;
        const bool canResolve = desc.SampleDesc.Count > 1u &&
            SUCCEEDED(device->CheckFormatSupport(desc.Format, &sourceFormatSupport)) &&
            (sourceFormatSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) != 0u;
        const auto transfer = native_shared_desktop_source_transfer(
            desc.MipLevels, desc.ArraySize, desc.SampleDesc.Count,
            desc.SampleDesc.Quality,
            (desc.BindFlags & D3D11_BIND_RENDER_TARGET) != 0u, canResolve);
        if (transfer == NativeSharedDesktopSourceTransfer::Reject)
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
        // Transfer only the pixels that this native menu/car/race Present
        // will actually reveal. A cropped or single-dirty source otherwise
        // incurred a full 3440x1440 GPU CopyResource on every frame.
        // Source/destination are identically sized BGRA textures; source_
        // pixels outside this region are never exposed by StretchRect.
        ID3D11Texture2D* readySource = source;
        if (transfer == NativeSharedDesktopSourceTransfer::Resolve) {
            // Cache one non-MSAA GPU intermediate per output generation. The
            // existing EVENT fence protects it and the shared D3D9 allocation
            // from premature reuse; no CPU Map or readback is introduced.
            if (!resolvedSource_) {
                D3D11_TEXTURE2D_DESC resolved = desc;
                resolved.MipLevels = 1u;
                resolved.ArraySize = 1u;
                resolved.SampleDesc.Count = 1u;
                resolved.SampleDesc.Quality = 0u;
                resolved.BindFlags = 0u; // copy-only GPU intermediate
                resolved.MiscFlags = 0u;
                if (FAILED(device->CreateTexture2D(
                        &resolved, nullptr, resolvedSource_.GetAddressOf())) ||
                    !resolvedSource_)
                    return false;
            }
            // Resolve is whole-subresource even for a cropped/dirty Present;
            // copy only the admitted visible tiles from that resolved image.
            context->ResolveSubresource(
                resolvedSource_.Get(), 0u, source, 0u, desc.Format);
            readySource = resolvedSource_.Get();
        }
        const bool entire = regionCount == 1u &&
            visibleRegions[0].left == 0 && visibleRegions[0].top == 0 &&
            static_cast<std::uint32_t>(visibleRegions[0].right) == width &&
            static_cast<std::uint32_t>(visibleRegions[0].bottom) == height;
        if (entire) {
            context->CopyResource(source_.Get(), readySource);
        } else {
            for (std::uint32_t i = 0; i < regionCount; ++i) {
                const RECT& tile = visibleRegions[i];
                const D3D11_BOX region{
                    static_cast<UINT>(tile.left),
                    static_cast<UINT>(tile.top), 0u,
                    static_cast<UINT>(tile.right),
                    static_cast<UINT>(tile.bottom), 1u};
                context->CopySubresourceRegion(
                    source_.Get(), 0u, region.left, region.top, 0u,
                    readySource, 0u, &region);
            }
        }
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
        // while the source State mutex is held. Copy only pixels the game
        // will show from this Present crop / one proven dirty rectangle.
        // All other D3D9 backbuffer pixels remain the game's own output.
        // StretchRect is not atomic even for ONE full/cropped game rectangle.
        // Preserve original D3D9 pixels for every region before any writes,
        // otherwise a failed first/single blit could corrupt the fallback.
        // Never back up the union between distant original-game HUD tiles.
        // Keep bounded original-game rollback render targets across steady
        // Presents instead of allocating up to 32 DEFAULT-pool surfaces per
        // frame. Their contents are NEVER reused: snapshot all visible tiles
        // again before any GPU/native StretchRect changes the backbuffer.
        // Generation, owning D3D9Ex device, format and exact tile size fence
        // reuse across Reset, car/menu resolution changes and new sources.
        const auto ownerToken =
            reinterpret_cast<std::uintptr_t>(game9Ex_.Get());
        for (std::uint32_t i = 0u; i < rollbackPlan.count; ++i) {
            const NativeSharedDesktopBackupKey required{
                rollbackPlan.tiles[i].width,
                rollbackPlan.tiles[i].height,
                static_cast<std::uint32_t>(destination.Format),
                generation_, ownerToken};
            auto& backup = backups_[i];
            if (!backup || !backupKeys_[i].reusable_for(required)) {
                backup.Reset();
                backupKeys_[i] = {};
                if (FAILED(game->CreateRenderTarget(
                        required.width, required.height,
                        destination.Format, D3DMULTISAMPLE_NONE, 0u, FALSE,
                        backup.GetAddressOf(), nullptr)) || !backup)
                    return false;
                backupKeys_[i] = required;
            }
            if (FAILED(game->StretchRect(
                    backbuffer, &visibleRegions[i], backup.Get(),
                    nullptr, D3DTEXF_NONE)))
                return false;
        }
        for (std::uint32_t i = 0; i < regionCount; ++i) {
            const RECT* rect = entire ? nullptr : &visibleRegions[i];
            if (FAILED(game->StretchRect(
                    sharedSurface.Get(), rect, backbuffer, rect, D3DTEXF_NONE))) {
                // A failing StretchRect can have partially written its own tile.
                // Restore the failed tile AND all earlier writes from original
                // pre-blit snapshots. Never rewrite untouched gaps in the union.
                bool restored = true;
                for (std::uint32_t j = 0u; j <= i; ++j) {
                    if (FAILED(game->StretchRect(
                            backups_[j].Get(), nullptr, backbuffer,
                            &visibleRegions[j], D3DTEXF_NONE)))
                        restored = false;
                }
                if (!restored) faulted_ = true;
                return false;
            }
        }
        return true;
    }
private:
    // Bounded by the same admitted dirty-region tile count as the rollback
    // plan. Snapshots are rewritten every frame; only GPU allocations persist.
    std::array<Microsoft::WRL::ComPtr<IDirect3DSurface9>,
               GameNativeDirtyRegionCoverage::kMaxPartitionRects> backups_{};
    std::array<NativeSharedDesktopBackupKey,
               GameNativeDirtyRegionCoverage::kMaxPartitionRects> backupKeys_{};
    Microsoft::WRL::ComPtr<ID3D11Texture2D> source_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> resolvedSource_;
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
