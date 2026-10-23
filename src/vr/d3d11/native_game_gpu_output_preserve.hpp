#pragma once
#include <d3d11.h>
#include "native_game_om_slots.hpp"

namespace outrun::vr::dx11::live_game_frame {
// Preserve the entire *game-owned* D3D11 OM/compute output state while
// transferring a real menu/car/race GPU source to the shared D3D9Ex desktop.
// A source may still be bound as MRT or a compute/pixel UAV at Present.
// D3D11 GPU Copy/Resolve must not read a live writable output. The original
// native Draw pipeline, as well as D3D9 input/FFB fallback, resumes with
// exactly the same bound render targets and UAV counter values (-1 = keep).
class ScopedNativeGameGpuTransferOutputs final {
public:
    explicit ScopedNativeGameGpuTransferOutputs(
        ID3D11DeviceContext* context) noexcept : context_(context) {
        if (!context_) return;
        context_->OMGetRenderTargets(
            D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT, targets_, &depth_);
        std::uint32_t occupied = 0u;
        for (UINT i = 0; i < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++i)
            if (targets_[i]) occupied |= 1u << i;
        slots_ = NativeGameOmSlots::from_rtv_mask(occupied);
        // Pixel UAVs share the RTV namespace. Query only the unoccupied
        // tail, including when the game uses a sparse eight-target MRT.
        if (slots_.uavCount)
            context_->OMGetRenderTargetsAndUnorderedAccessViews(
                0u, nullptr, nullptr, slots_.uavStart, slots_.uavCount,
                pixelUavs_ + slots_.uavStart);
        context_->CSGetUnorderedAccessViews(
            0u, D3D11_PS_CS_UAV_REGISTER_COUNT, computeUavs_);
        ID3D11UnorderedAccessView* detached[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
        context_->CSSetUnorderedAccessViews(
            0u, D3D11_PS_CS_UAV_REGISTER_COUNT, detached, nullptr);
        context_->OMSetRenderTargetsAndUnorderedAccessViews(
            0u, nullptr, nullptr, 0u,
            D3D11_PS_CS_UAV_REGISTER_COUNT, detached, nullptr);
    }
    ~ScopedNativeGameGpuTransferOutputs() noexcept {
        if (!context_) return;
        UINT keepCounters[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
        for (auto& counter : keepCounters) counter = UINT(-1);
        if (slots_.uavCount) {
            context_->OMSetRenderTargetsAndUnorderedAccessViews(
                slots_.rtvCount, slots_.rtvCount ? targets_ : nullptr, depth_,
                slots_.uavStart, slots_.uavCount,
                pixelUavs_ + slots_.uavStart,
                keepCounters + slots_.uavStart);
        } else {
            // RTV7 occupies the final pixel output register; UAVStart=8 is
            // invalid even with a zero count. Restore the MRT-only variant.
            context_->OMSetRenderTargets(slots_.rtvCount, targets_, depth_);
        }
        context_->CSSetUnorderedAccessViews(
            0u, D3D11_PS_CS_UAV_REGISTER_COUNT, computeUavs_,
            keepCounters);
        for (auto* target : targets_) if (target) target->Release();
        if (depth_) depth_->Release();
        for (auto* uav : pixelUavs_) if (uav) uav->Release();
        for (auto* uav : computeUavs_) if (uav) uav->Release();
    }
    ScopedNativeGameGpuTransferOutputs(
        const ScopedNativeGameGpuTransferOutputs&) = delete;
    ScopedNativeGameGpuTransferOutputs& operator=(
        const ScopedNativeGameGpuTransferOutputs&) = delete;
private:
    ID3D11DeviceContext* context_{};
    ID3D11RenderTargetView* targets_[
        D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
    ID3D11DepthStencilView* depth_{};
    ID3D11UnorderedAccessView* pixelUavs_[
        D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    ID3D11UnorderedAccessView* computeUavs_[
        D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    NativeGameOmSlots slots_{};
};

// Preserve real-game native shader inputs while a game-authored surface copy
// writes the native full-frame texture. D3D11 would otherwise permit a
// write/read alias to persist into later menu/car/race Draws. Only views of
// the destination are detached; unrelated game SRVs remain untouched.
class ScopedNativeGameGpuTransferInputs final {
public:
    explicit ScopedNativeGameGpuTransferInputs(
        ID3D11DeviceContext* context, ID3D11Resource* destination) noexcept
        : context_(context), destination_(destination) {
        if (context_ && destination_)
            for (UINT stage = 0u; stage != 6u; ++stage) capture(stage);
    }
    ~ScopedNativeGameGpuTransferInputs() noexcept {
        if (!context_) return;
        for (UINT i = count_; i; --i) {
            const auto& entry = saved_[i - 1u];
            set(entry.stage, entry.slot, &entry.view);
            entry.view->Release();
        }
    }
    ScopedNativeGameGpuTransferInputs(
        const ScopedNativeGameGpuTransferInputs&) = delete;
    ScopedNativeGameGpuTransferInputs& operator=(
        const ScopedNativeGameGpuTransferInputs&) = delete;
private:
    struct Entry { ID3D11ShaderResourceView* view{}; UINT stage{}, slot{}; };
    void get(UINT stage, ID3D11ShaderResourceView** views) noexcept {
        constexpr UINT n = D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT;
        switch (stage) {
        case 0u: context_->VSGetShaderResources(0u, n, views); break;
        case 1u: context_->PSGetShaderResources(0u, n, views); break;
        case 2u: context_->GSGetShaderResources(0u, n, views); break;
        case 3u: context_->HSGetShaderResources(0u, n, views); break;
        case 4u: context_->DSGetShaderResources(0u, n, views); break;
        case 5u: context_->CSGetShaderResources(0u, n, views); break;
        }
    }
    void set(UINT stage, UINT slot,
             ID3D11ShaderResourceView* const* views) noexcept {
        switch (stage) {
        case 0u: context_->VSSetShaderResources(slot, 1u, views); break;
        case 1u: context_->PSSetShaderResources(slot, 1u, views); break;
        case 2u: context_->GSSetShaderResources(slot, 1u, views); break;
        case 3u: context_->HSSetShaderResources(slot, 1u, views); break;
        case 4u: context_->DSSetShaderResources(slot, 1u, views); break;
        case 5u: context_->CSSetShaderResources(slot, 1u, views); break;
        }
    }
    void capture(UINT stage) noexcept {
        constexpr UINT n = D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT;
        ID3D11ShaderResourceView* views[n]{};
        get(stage, views); // Get* adds one reference for every bound SRV.
        for (UINT slot = 0u; slot != n; ++slot) {
            auto* view = views[slot];
            if (!view) continue;
            ID3D11Resource* resource = nullptr;
            view->GetResource(&resource);
            const bool alias = resource == destination_;
            if (resource) resource->Release();
            if (!alias) { view->Release(); continue; }
            saved_[count_++] = {view, stage, slot};
            ID3D11ShaderResourceView* empty = nullptr;
            set(stage, slot, &empty);
        }
    }
    ID3D11DeviceContext* context_{};
    ID3D11Resource* destination_{};
    Entry saved_[6u * D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    UINT count_{};
};
} // namespace outrun::vr::dx11::live_game_frame
