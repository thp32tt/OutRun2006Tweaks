#include "native_game_stereo_submission.hpp"
#include "native_game_offscreen_color_provenance.hpp"
#include "native_game_eye_pair_sources.hpp"
#include "native_game_postpass_replay.hpp"
#include "native_game_camera_view.hpp"
#include "native_game_partial_color_format.hpp"
#include "native_game_stretch_source.hpp"
#include "native_game_stereo_draw_evidence.hpp"
#include "native_game_raster_topology.hpp"
#include <limits>
#include <cmath>
#include <algorithm>
#include <d3d11_1.h>
#include <d3dcompiler.h>
#include <mutex>
#include <utility>

namespace outrun::vr::dx11 {
namespace {
[[nodiscard]] bool raster_partial_eye_depth_clear(
    ID3D11DeviceContext*, ID3D11DepthStencilView*,
    std::uint32_t, std::uint32_t, const D3D11_RECT&,
    float, std::uint8_t, bool, bool) noexcept;
[[nodiscard]] bool raster_partial_eye_color_clear(
    ID3D11DeviceContext*, ID3D11RenderTargetView*,
    std::uint32_t, std::uint32_t, const D3D11_RECT&,
    const float (&)[4]) noexcept;

// Capture the full RTV/DSV state before querying the legal pixel UAV tail.
// OM RTV and pixel UAV registers overlap; querying all eight RTV slots AND
// UAV slots 0..7 as a single range is not legal with live sparse MRTs.
// The highest occupied RTV (not the number of non-null RTVs) sets the start.
// Preserve gaps such as RT0/RT2 + UAV3 across real camera Copy/Stretch and
// eye replay, including the last-RT7 case with NO available pixel UAV slots.
void capture_native_om_outputs(
    ID3D11DeviceContext* ctx,
    ID3D11RenderTargetView** targets,
    ID3D11DepthStencilView** depth,
    ID3D11UnorderedAccessView** unordered) noexcept {
    ctx->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
                            targets, depth);
    UINT occupiedPrefix = 0u;
    for (UINT i = 0u; i < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++i)
        if (targets[i]) occupiedPrefix = i + 1u;
    if (occupiedPrefix < D3D11_PS_CS_UAV_REGISTER_COUNT)
        ctx->OMGetRenderTargetsAndUnorderedAccessViews(
            0u, nullptr, nullptr,
            occupiedPrefix, D3D11_PS_CS_UAV_REGISTER_COUNT - occupiedPrefix,
            unordered + occupiedPrefix);
}

// D3D11 OM UAVs share the output merger with MRT/DSV. A game/host
// postpass can leave a pixel-stage UAV bound while the native camera
// copies or replays its eye. Restore the occupied RTV prefix and every
// remaining UAV slot together: OMSetRenderTargets alone loses the UAVs.
// -1 retains append/consume counters for structured game GPU outputs.
void restore_native_om_outputs(
    ID3D11DeviceContext* ctx,
    ID3D11RenderTargetView* const* targets,
    ID3D11DepthStencilView* depth,
    ID3D11UnorderedAccessView* const* unordered) noexcept {
    UINT rtCount = 0u;
    for (UINT i = 0u; i < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++i)
        if (targets[i]) rtCount = i + 1u;
    UINT keep[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    for (auto& value : keep) value = UINT(-1);
    const UINT remaining = D3D11_PS_CS_UAV_REGISTER_COUNT - rtCount;
    if (!remaining) {
        // RTV7 occupied: UAVStartSlot=8 is not a D3D11 pixel UAV slot.
        ctx->OMSetRenderTargets(rtCount, targets, depth);
    } else {
        ctx->OMSetRenderTargetsAndUnorderedAccessViews(
            rtCount, rtCount ? targets : nullptr, depth,
            rtCount, remaining, unordered + rtCount, keep + rtCount);
    }
}

// Native GPU game postpasses may sample compute-produced camera textures.
// Detach every bound CS UAV and OM target before copying/sampling, then
// restore unrelated MRT/depth/UAV outputs without resetting UAV counters.
struct ScopedNativePostpassOutputs final {
    ID3D11DeviceContext* ctx{};
    ID3D11RenderTargetView* targets[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
    ID3D11DepthStencilView* depth{};
    ID3D11UnorderedAccessView* om[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    ID3D11UnorderedAccessView* compute[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    explicit ScopedNativePostpassOutputs(ID3D11DeviceContext* c) noexcept : ctx(c) {
        capture_native_om_outputs(ctx, targets, &depth, om);
        ctx->CSGetUnorderedAccessViews(0u, D3D11_PS_CS_UAV_REGISTER_COUNT, compute);
        ID3D11UnorderedAccessView* empty[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
        ctx->CSSetUnorderedAccessViews(0u, D3D11_PS_CS_UAV_REGISTER_COUNT, empty, nullptr);
        // Detach both PS/OM and CS writable aliases before sampling or Copy.
        ctx->OMSetRenderTargetsAndUnorderedAccessViews(
            0u, nullptr, nullptr, 0u, D3D11_PS_CS_UAV_REGISTER_COUNT,
            empty, nullptr);
    }
    ~ScopedNativePostpassOutputs() noexcept {
        restore_native_om_outputs(ctx, targets, depth, om);
        UINT keep[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
        for (auto& v : keep) v = UINT(-1);
        ctx->CSSetUnorderedAccessViews(0u, D3D11_PS_CS_UAV_REGISTER_COUNT, compute, keep);
        for (auto* v : targets) if (v) v->Release();
        if (depth) depth->Release();
        for (auto* v : om) if (v) v->Release();
        for (auto* v : compute) if (v) v->Release();
    }
    ScopedNativePostpassOutputs(const ScopedNativePostpassOutputs&) = delete;
    ScopedNativePostpassOutputs& operator=(const ScopedNativePostpassOutputs&) = delete;
};

// A source Clear/Copy/Stretch scheduled immediately before an offscreen
// Draw writes the XR eye, not the callback's currently selected camera.
// Temporarily install the eye's original RS clip and restore ALL viewport,
// scissor and rasterizer bindings before drawing the offscreen game geometry.
// No GPU commands are created by the snapshot itself.
class ScopedNativeEyeRasterForSourceReplay final {
public:
    ScopedNativeEyeRasterForSourceReplay(
        ID3D11DeviceContext* context, const D3D11_VIEWPORT& eyeViewport,
        const D3D11_RECT& eyeScissor, ID3D11RasterizerState* eyeRaster) noexcept
        : context_(context) {
        if (!context_) return;
        viewportCount_ = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
        scissorCount_ = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
        context_->RSGetViewports(&viewportCount_, viewports_);
        context_->RSGetScissorRects(&scissorCount_, scissors_);
        context_->RSGetState(savedRaster_.GetAddressOf());
        if (viewportCount_ == 0u ||
            viewportCount_ > D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE ||
            scissorCount_ > D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE)
            return;
        context_->RSSetState(eyeRaster);
        context_->RSSetViewports(1u, &eyeViewport);
        context_->RSSetScissorRects(1u, &eyeScissor);
        active_ = true;
    }
    ~ScopedNativeEyeRasterForSourceReplay() noexcept {
        if (!active_) return;
        context_->RSSetState(savedRaster_.Get());
        context_->RSSetViewports(viewportCount_, viewports_);
        context_->RSSetScissorRects(
            scissorCount_, scissorCount_ ? scissors_ : nullptr);
    }
    [[nodiscard]] bool valid() const noexcept { return active_; }
    ScopedNativeEyeRasterForSourceReplay(
        const ScopedNativeEyeRasterForSourceReplay&) = delete;
    ScopedNativeEyeRasterForSourceReplay& operator=(
        const ScopedNativeEyeRasterForSourceReplay&) = delete;
private:
    ID3D11DeviceContext* context_{};
    D3D11_VIEWPORT viewports_[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE]{};
    D3D11_RECT scissors_[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE]{};
    UINT viewportCount_{}, scissorCount_{};
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> savedRaster_;
    bool active_{};
};

// A native D3D9 TARGET rectangle Clear on a D3D11.0 device must rasterize
// into the *typed RTV*, not infer its format from the backing texture. Real
// menu/vehicle intermediates may use TYPELESS allocations with UNORM/float
// camera views, and 10-bit/half-float targets also need the same bounded GPU
// Clear. Integer/typeless/depth views cannot consume our float4 pixel shader.
// The device must actually advertise RTV writes for the selected typed format.
[[nodiscard]] bool native_game_partial_color_shader_rtv(
    ID3D11DeviceContext* context, ID3D11RenderTargetView* target) noexcept {
    if (!context || !target) return false;
    D3D11_RENDER_TARGET_VIEW_DESC view{};
    target->GetDesc(&view);
    // Retain the original audited typed-RTV admission in the native GPU
    // activation boundary. Additional valid typed cameras (luminance,
    // two-channel, float and sRGB) use the same float4 Clear shader only
    // after the shared extended classifier explicitly accepts the format.
    // Integer, typeless and depth views still fail closed.
    switch (view.Format) {
    case DXGI_FORMAT_R8G8B8A8_UNORM:
    case DXGI_FORMAT_B8G8R8A8_UNORM:
    case DXGI_FORMAT_B8G8R8X8_UNORM:
    case DXGI_FORMAT_R10G10B10A2_UNORM:
    case DXGI_FORMAT_R16G16B16A16_UNORM:
    case DXGI_FORMAT_R16G16B16A16_FLOAT:
    case DXGI_FORMAT_R11G11B10_FLOAT:
    case DXGI_FORMAT_B5G6R5_UNORM:
    case DXGI_FORMAT_B5G5R5A1_UNORM:
        break;
    default:
        if (!native_game_partial_color_shader_format(view.Format))
            return false;
        break;
    }
    Microsoft::WRL::ComPtr<ID3D11Device> device;
    context->GetDevice(device.GetAddressOf());
    UINT support = 0u;
    return device &&
        SUCCEEDED(device->CheckFormatSupport(view.Format, &support)) &&
        (support & D3D11_FORMAT_SUPPORT_RENDER_TARGET) != 0u;
}

// The Clear command uses real D3D9 viewport/scissor coverage, not the
// D3D11.0/11.1 full-RTV semantics. Query RS before a shader-backed Clear
// temporarily swaps the draw pipeline, and preserve fail-closed fallback.
[[nodiscard]] NativeGameCameraClearRegion camera_clear_coverage(
    ID3D11DeviceContext* ctx, UINT width, UINT height,
    const D3D11_RECT* region) noexcept {
    if (!ctx) return {};
    D3D11_VIEWPORT viewport{};
    UINT viewportCount = 1u;
    ctx->RSGetViewports(&viewportCount, &viewport);
    if (viewportCount != 1u) return {};
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> raster;
    ctx->RSGetState(raster.GetAddressOf());
    bool enabled = false;
    if (raster) {
        D3D11_RASTERIZER_DESC desc{};
        raster->GetDesc(&desc);
        enabled = desc.ScissorEnable != FALSE;
    }
    D3D11_RECT scissor{};
    if (enabled) {
        UINT count = 1u;
        ctx->RSGetScissorRects(&count, &scissor);
        if (count != 1u) return {};
    }
    return native_game_camera_clear_region(
        width, height, viewport, enabled, enabled ? &scissor : nullptr,
        region);
}
}

// Real Draws have to overlap the selected camera's physical pixel area.
// Clear and copy chronology use their own coverage rules, so a clipped
// no-op game Clear remains successful without fabricating a geometry Draw.
[[nodiscard]] bool camera_draw_coverage(
    ID3D11DeviceContext* ctx, UINT width, UINT height) noexcept {
    if (!ctx) return false;
    D3D11_VIEWPORT viewport{};
    UINT viewportCount = 1u;
    ctx->RSGetViewports(&viewportCount, &viewport);
    if (viewportCount != 1u) return false;
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> rasterizer;
    ctx->RSGetState(rasterizer.GetAddressOf());
    bool scissorEnabled = false;
    if (rasterizer) {
        D3D11_RASTERIZER_DESC desc{};
        rasterizer->GetDesc(&desc);
        scissorEnabled = desc.ScissorEnable != FALSE;
    }
    D3D11_RECT scissor{};
    if (scissorEnabled) {
        UINT count = 1u;
        ctx->RSGetScissorRects(&count, &scissor);
        if (count != 1u) return false;
    }
    return native_game_camera_draw_coverage(
        width, height, viewport, scissorEnabled,
        scissorEnabled ? &scissor : nullptr);
}

// Only game Draws addressed to THIS eye's real RTV+DSV are source evidence.
// A callback may unbind OM to render a menu texture; counting that Draw
// would publish an unchanged/stale XR eye although the GPU issued commands.
bool NativeGameEyeDrawEncoder::eye_targets_bound() const noexcept {
    if (!context_ || !eyeTarget_ || !eyeDepth_) return false;
    ID3D11RenderTargetView* actualTarget = nullptr;
    ID3D11DepthStencilView* actualDepth = nullptr;
    context_->OMGetRenderTargets(1u, &actualTarget, &actualDepth);
    const bool matches = actualTarget == eyeTarget_ && actualDepth == eyeDepth_;
    if (actualTarget) actualTarget->Release();
    if (actualDepth) actualDepth->Release();
    return matches;
}

// A source game Draw can inherit a menu MRT1 or a PS UAV from an unrelated
// camera/host pass while RT0 still matches our eye. D3D11 would write BOTH
// outputs on Draw/DrawIndexed; those extra pixels bypass XR ownership and
// potentially overwrite the other eye. Postpass Copy/Stretch deliberately
// support MRT/UAV save+restore; this restriction is only for geometry writes.
// Query UAV slots 1..7 only after proving RTV0 is the sole color attachment:
// RTV and PS UAV slots overlap on D3D11 and querying an occupied RTV range
// as UAV would be invalid. Balance all Get* COM references on every path.
bool NativeGameEyeDrawEncoder::geometry_outputs_isolated(
    ID3D11RenderTargetView* target) const noexcept {
    if (!context_ || !target) return false;
    ID3D11RenderTargetView* bound[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
    context_->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
                                  bound, nullptr);
    bool sole = bound[0] == target;
    for (UINT i = 1u; i < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT; ++i)
        if (bound[i]) sole = false;
    for (auto* view : bound) if (view) view->Release();
    if (!sole) return false;
    ID3D11UnorderedAccessView* uavs[D3D11_PS_CS_UAV_REGISTER_COUNT - 1u]{};
    context_->OMGetRenderTargetsAndUnorderedAccessViews(
        0u, nullptr, nullptr, 1u,
        D3D11_PS_CS_UAV_REGISTER_COUNT - 1u, uavs);
    for (auto* view : uavs) {
        if (view) { sole = false; view->Release(); }
    }
    return sole;
}

bool NativeGameEyeDrawEncoder::eye_output_bound() const noexcept {
    if (!eye_targets_bound() || !targetWidth_ || !targetHeight_ ||
        !geometry_outputs_isolated(eyeTarget_)) return false;

    // A successful API Draw with a clipped or empty raster cannot be used
    // as OpenXR eye evidence. Apply the SAME physical viewport/scissor
    // admission as a real auxiliary menu/car/race camera Draw: they must not
    // disagree on whether any GPU color pixels can be produced.
    UINT viewportCount = 1u;
    D3D11_VIEWPORT view{};
    context_->RSGetViewports(&viewportCount, &view);
    if (viewportCount != 1u) return false;
    ID3D11RasterizerState* rasterizer = nullptr;
    context_->RSGetState(&rasterizer);
    bool scissorEnabled = false;
    if (rasterizer) {
        D3D11_RASTERIZER_DESC desc{};
        rasterizer->GetDesc(&desc);
        scissorEnabled = desc.ScissorEnable != FALSE;
        rasterizer->Release();
    }
    D3D11_RECT scissor{};
    if (scissorEnabled) {
        UINT count = 1u;
        context_->RSGetScissorRects(&count, &scissor);
        if (count != 1u) return false;
    }
    return native_game_camera_draw_coverage(
        targetWidth_, targetHeight_, view, scissorEnabled,
        scissorEnabled ? &scissor : nullptr);
}

// An OM-bound eye with valid raster coverage is not a color frame when
// menu/vehicle/race draws update Z only, suppress every sample, or have no
// shader capable of writing target 0. Preserve these GPU draws as depth
// history while requiring at least one color-capable draw per published eye.
bool NativeGameEyeDrawEncoder::eye_color_writable() const noexcept {
    return color_writable_for_samples(1u); // shared native XR eye is single-sample
}

// Real game menu/car/race cameras may be MSAA, unlike the ring eye.
// A queued depth-only, color-masked or shaderless offscreen Draw cannot
// certify that a subsequent GPU Copy/Stretch contains a fresh game frame.
// Preserve the authentic GPU command and source draw ordinal regardless.
bool NativeGameEyeDrawEncoder::source_color_writable(
    ID3D11RenderTargetView* gameTarget) const noexcept {
    if (!context_ || !gameTarget) return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    gameTarget->GetResource(resource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
    if (!resource || FAILED(resource.As(&texture)) || !texture)
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    texture->GetDesc(&desc);
    return color_writable_for_samples(desc.SampleDesc.Count);
}


// An eligible Draw from camera A is NOT evidence that a later GPU Copy from
// camera B contains freshly rendered game pixels. Keep only the exact physical
// resource/mip/slice of live, color-writable menu/car/race Draws.
void NativeGameEyeDrawEncoder::remember_offscreen_color_source(
    ID3D11RenderTargetView* target) noexcept {
    if (!target) return;
    Microsoft::WRL::ComPtr<ID3D11Resource> allocation;
    target->GetResource(allocation.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
    if (!allocation || FAILED(allocation.As(&texture)) || !texture) return;
    D3D11_TEXTURE2D_DESC td{};
    D3D11_RENDER_TARGET_VIEW_DESC vd{};
    texture->GetDesc(&td);
    target->GetDesc(&vd);
    const auto view = native_game_camera_rtv_extent(td, vd);
    if (!view.valid) return;
    D3D11_VIEWPORT viewport{};
    UINT viewportCount = 1u;
    context_->RSGetViewports(&viewportCount, &viewport);
    if (viewportCount != 1u) return;
    Microsoft::WRL::ComPtr<ID3D11RasterizerState> raster;
    context_->RSGetState(raster.GetAddressOf());
    D3D11_RASTERIZER_DESC rasterDesc{};
    if (raster) raster->GetDesc(&rasterDesc);
    D3D11_RECT scissor{};
    if (rasterDesc.ScissorEnable) {
        UINT scissorCount = 1u;
        context_->RSGetScissorRects(&scissorCount, &scissor);
        if (scissorCount != 1u) return;
    }
    const auto region = native_game_offscreen_draw_pixel_region(
        view.width, view.height,
        double(viewport.TopLeftX), double(viewport.TopLeftY),
        double(viewport.TopLeftX) + double(viewport.Width),
        double(viewport.TopLeftY) + double(viewport.Height),
        rasterDesc.ScissorEnable != FALSE,
        scissor.left, scissor.top, scissor.right, scissor.bottom);
    if (!native_game_offscreen_color_region_valid(region)) return;
    const NativeGameOffscreenColorKey key{
        reinterpret_cast<std::uintptr_t>(texture.Get()), view.arraySlice, view.mip};
    for (const auto& record : offscreenColorSources_)
        if (native_game_offscreen_color_key_matches(
                key, {reinterpret_cast<std::uintptr_t>(record.texture.Get()),
                      record.arraySlice, record.mipSlice}) &&
            record.region.left == region.left &&
            record.region.top == region.top &&
            record.region.right == region.right &&
            record.region.bottom == region.bottom) return;
    for (auto& record : offscreenColorSources_) {
        if (!record.texture) {
            record.texture = std::move(texture);
            record.arraySlice = view.arraySlice;
            record.mipSlice = view.mip;
            record.region = region;
            return;
        }
    }
    // Full ledger: keep original GPU commands but do not invent source proof.
}
void NativeGameEyeDrawEncoder::invalidate_offscreen_color_source(
    ID3D11RenderTargetView* target) noexcept {
    if (!target) return;
    Microsoft::WRL::ComPtr<ID3D11Resource> allocation;
    target->GetResource(allocation.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
    if (!allocation || FAILED(allocation.As(&texture)) || !texture) return;
    D3D11_TEXTURE2D_DESC td{};
    D3D11_RENDER_TARGET_VIEW_DESC vd{};
    texture->GetDesc(&td);
    target->GetDesc(&vd);
    const auto view = native_game_camera_rtv_extent(td, vd);
    if (!view.valid) return;
    const NativeGameOffscreenColorKey key{
        reinterpret_cast<std::uintptr_t>(texture.Get()), view.arraySlice, view.mip};
    for (auto& record : offscreenColorSources_)
        if (native_game_offscreen_color_key_matches(
                key, {reinterpret_cast<std::uintptr_t>(record.texture.Get()),
                      record.arraySlice, record.mipSlice})) {
            record.texture.Reset();
            record.arraySlice = record.mipSlice = 0u;
            record.region = {};
        }
}
bool NativeGameEyeDrawEncoder::offscreen_color_source_proven(
    ID3D11Texture2D* source, UINT arraySlice, UINT mipSlice,
    const D3D11_BOX& sourceRegion) const noexcept {
    if (!source || sourceRegion.front != 0u || sourceRegion.back != 1u)
        return false;
    const NativeGameOffscreenColorRegion copied{
        sourceRegion.left, sourceRegion.top,
        sourceRegion.right, sourceRegion.bottom};
    if (!native_game_offscreen_color_region_valid(copied)) return false;
    const NativeGameOffscreenColorKey key{
        reinterpret_cast<std::uintptr_t>(source), arraySlice, mipSlice};
    for (const auto& record : offscreenColorSources_)
        if (native_game_offscreen_color_key_matches(
                key, {reinterpret_cast<std::uintptr_t>(record.texture.Get()),
                      record.arraySlice, record.mipSlice}) &&
            native_game_offscreen_color_regions_intersect(record.region, copied))
            return true;
    return false;
}

bool NativeGameEyeDrawEncoder::color_writable_for_samples(
    UINT sampleCount) const noexcept {
    if (!context_) return false;
    ID3D11BlendState* blend = nullptr;
    FLOAT blendFactors[4]{};
    UINT sampleMask = 0u;
    context_->OMGetBlendState(&blend, blendFactors, &sampleMask);
    // The XR eye uses sample zero, while a real offscreen MSAA camera can
    // write any of its physical samples. High mask bits outside that
    // attachment's sample count never certify new color pixels.
    bool writable = live_game_stereo::render_target_color_sample_write(
        sampleMask, sampleCount);
    if (blend) {
        D3D11_BLEND_DESC desc{};
        blend->GetDesc(&desc);
        const auto& eye = desc.RenderTarget[0];
        writable = writable &&
            (desc.RenderTarget[0].RenderTargetWriteMask &
             D3D11_COLOR_WRITE_ENABLE_ALL) != 0u &&
            live_game_stereo::blended_eye_color_may_change(
                eye.BlendEnable != FALSE, eye.RenderTargetWriteMask,
                static_cast<UINT>(eye.SrcBlend),
                static_cast<UINT>(eye.DestBlend),
                static_cast<UINT>(eye.BlendOp),
                static_cast<UINT>(eye.SrcBlendAlpha),
                static_cast<UINT>(eye.DestBlendAlpha),
                static_cast<UINT>(eye.BlendOpAlpha));
        blend->Release();
    }
    ID3D11VertexShader* vertex = nullptr;
    ID3D11PixelShader* pixel = nullptr;
    context_->VSGetShader(&vertex, nullptr, nullptr);
    context_->PSGetShader(&pixel, nullptr, nullptr);
    const bool hasShaders = vertex != nullptr && pixel != nullptr;
    if (vertex) vertex->Release();
    if (pixel) pixel->Release();

    // Game-authored menu/vehicle occluders often draw with both shaders and
    // writable OM color but a NEVER depth/stencil comparison. D3D11 queues
    // those commands successfully without emitting ANY eye color samples.
    // Preserve their real source ordinals, while requiring subsequent
    // color-capable game geometry/Copy/Stretch before XR publication.
    ID3D11DepthStencilState* depthStencil = nullptr;
    UINT stencilReference = 0u;
    context_->OMGetDepthStencilState(&depthStencil, &stencilReference);
    if (depthStencil) {
        D3D11_DEPTH_STENCIL_DESC desc{};
        depthStencil->GetDesc(&desc);
        writable = writable && live_game_stereo::fragment_can_reach_eye_color(
            desc.DepthEnable != FALSE,
            desc.DepthFunc == D3D11_COMPARISON_NEVER,
            desc.StencilEnable != FALSE,
            desc.FrontFace.StencilFunc == D3D11_COMPARISON_NEVER,
            desc.BackFace.StencilFunc == D3D11_COMPARISON_NEVER);
        depthStencil->Release();
    }
    return writable && hasShaders;
}

// A game postpass can bind an occlusion predicate after the eye scope
// initially detached inherited host predicates. The D3D11 draw API returns
// success even when GPU predication discards all fragments. Its async query
// result is not evidence of a visible XR eye. Issue the authentic command
// for its depth/order history, but never certify color without a known
// unpredicated source draw; the original D3D9 game remains authoritative.
bool NativeGameEyeDrawEncoder::unpredicated_color_evidence() const noexcept {
    if (!context_) return false;
    ID3D11Predicate* predicate = nullptr;
    BOOL comparison = FALSE;
    context_->GetPredication(&predicate, &comparison);
    const bool clear = predicate == nullptr;
    if (predicate) predicate->Release();
    return clear;
}

bool NativeGameEyeDrawEncoder::raster_primitive_possible(
    UINT vertexOrIndexCount) const noexcept {
    if (!context_) return false;
    D3D11_PRIMITIVE_TOPOLOGY topology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context_->IAGetPrimitiveTopology(&topology);
    return live_game_stereo::primitive_can_rasterize(topology, vertexOrIndexCount);
}

bool NativeGameEyeDrawEncoder::bind_eye_output() noexcept {
    if (!context_ || !eyeTarget_ || !eyeDepth_) return false;
    // A game menu/vehicle offscreen camera may leave a 256x144 viewport,
    // scissor and winding state after its last Draw. Rebinding ONLY the
    // full-resolution XR RTV/DSV would rasterize subsequent eye geometry
    // inside that stale camera clip. Preserve the game's intentionally
    // selected eye-space clip when RT0 is already the native eye, but on a
    // real offscreen->eye transition restore this eye's snapshotted camera.
    if (eye_targets_bound()) return eye_output_bound();
    if (!eyeRasterReady_) return false; // no verified eye raster: DX9 fallback
    ID3D11RenderTargetView* target = eyeTarget_;
    context_->OMSetRenderTargets(1u, &target, eyeDepth_);
    context_->RSSetState(eyeRasterizer_.Get());
    context_->RSSetViewports(1u, &eyeViewport_);
    context_->RSSetScissorRects(1u, &eyeScissor_);
    // Verify the physical eye coverage and sole OM ownership after
    // rebinding. A failed native transition never certifies OpenXR color.
    return eye_output_bound();
}

// A menu/vehicle game camera can draw into its private offscreen GPU RT
// before a chronological game StretchRect composites that image into an
// independently rendered XR eye. Admit only an explicitly source-proven
// attached texture. Its geometry MUST NOT count as direct eye color.
bool NativeGameEyeDrawEncoder::game_source_target_bound(
    ID3D11RenderTargetView* gameTarget) const noexcept {
    if (!context_ || !eyeTarget_ || !gameTarget || gameTarget == eyeTarget_)
        return false;
    ID3D11RenderTargetView* actual = nullptr;
    context_->OMGetRenderTargets(1u, &actual, nullptr);
    const bool bound = actual == gameTarget;
    if (actual) actual->Release();
    if (!bound) return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> sourceResource, eyeResource;
    gameTarget->GetResource(sourceResource.GetAddressOf());
    eyeTarget_->GetResource(eyeResource.GetAddressOf());
    if (!sourceResource || !eyeResource ||
        sourceResource.Get() == eyeResource.Get()) return false;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> source;
    if (FAILED(sourceResource.As(&source)) || !source) return false;
    Microsoft::WRL::ComPtr<ID3D11Device> producer, sourceOwner;
    context_->GetDevice(producer.GetAddressOf());
    source->GetDevice(sourceOwner.GetAddressOf());
    if (!producer || producer.Get() != sourceOwner.Get()) return false;
    D3D11_TEXTURE2D_DESC desc{};
    source->GetDesc(&desc);
    D3D11_RENDER_TARGET_VIEW_DESC viewDesc{};
    gameTarget->GetDesc(&viewDesc);
    const auto camera = native_game_camera_rtv_extent(desc, viewDesc);
    constexpr UINT sharedFlags =
        D3D11_RESOURCE_MISC_SHARED |
        D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
        D3D11_RESOURCE_MISC_SHARED_NTHANDLE;
    if (!camera.valid || desc.Usage != D3D11_USAGE_DEFAULT ||
        desc.CPUAccessFlags || (desc.MiscFlags & sharedFlags) ||
        (desc.BindFlags & D3D11_BIND_RENDER_TARGET) == 0u)
        return false;

    // Menu/car/race source cameras may omit depth for color-only HUD draws,
    // but a camera must NEVER borrow this native eye's depth/stencil. The
    // prior RT0-only admission let an authentic offscreen Draw overwrite
    // live XR-eye Z/stencil even though its color went to a game camera.
    // Test backing allocations, not DSV interface addresses: an alternate
    // view of the same eye depth texture is equally unsafe.
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> cameraDepth;
    context_->OMGetRenderTargets(0u, nullptr, cameraDepth.GetAddressOf());
    if (cameraDepth) {
        Microsoft::WRL::ComPtr<ID3D11Resource> cameraDepthResource;
        Microsoft::WRL::ComPtr<ID3D11Resource> nativeEyeDepthResource;
        cameraDepth->GetResource(cameraDepthResource.GetAddressOf());
        if (eyeDepth_)
            eyeDepth_->GetResource(nativeEyeDepthResource.GetAddressOf());
        if (!cameraDepthResource || !nativeEyeDepthResource ||
            cameraDepthResource.Get() == nativeEyeDepthResource.Get() ||
            cameraDepthResource.Get() == eyeResource.Get() ||
            cameraDepthResource.Get() == sourceResource.Get())
            return false;
        Microsoft::WRL::ComPtr<ID3D11Texture2D> cameraDepthTexture;
        Microsoft::WRL::ComPtr<ID3D11Device> depthOwner;
        if (FAILED(cameraDepthResource.As(&cameraDepthTexture)) ||
            !cameraDepthTexture) return false;
        cameraDepthTexture->GetDevice(depthOwner.GetAddressOf());
        D3D11_TEXTURE2D_DESC depthDesc{};
        cameraDepthTexture->GetDesc(&depthDesc);
        D3D11_DEPTH_STENCIL_VIEW_DESC selectedDepthView{};
        cameraDepth->GetDesc(&selectedDepthView);
        const auto physicalDepth =
            native_game_camera_dsv_extent(depthDesc, selectedDepthView);
        // Unlike the existing color-only admission, an actually bound game
        // DSV must address the same selected physical mip and sample layout.
        // Without this, a menu/vehicle source Draw is counted and later
        // copied to an XR eye despite having an incompatible Z/stencil view.
        if (!depthOwner || depthOwner.Get() != producer.Get() ||
            depthDesc.Usage != D3D11_USAGE_DEFAULT ||
            depthDesc.CPUAccessFlags != 0u ||
            (depthDesc.BindFlags & D3D11_BIND_DEPTH_STENCIL) == 0u ||
            (depthDesc.MiscFlags & sharedFlags) != 0u ||
            !native_game_camera_depth_compatible(
                camera, physicalDepth, desc.SampleDesc.Count,
                depthDesc.SampleDesc.Count, desc.SampleDesc.Quality,
                depthDesc.SampleDesc.Quality))
            return false;
    }
    UINT count = 1u;
    D3D11_VIEWPORT view{};
    context_->RSGetViewports(&count, &view);
    return count == 1u &&
        std::isfinite(view.TopLeftX) && std::isfinite(view.TopLeftY) &&
        std::isfinite(view.Width) && std::isfinite(view.Height) &&
        view.Width > 0.f && view.Height > 0.f &&
        view.TopLeftX < static_cast<float>(camera.width) &&
        view.TopLeftY < static_cast<float>(camera.height) &&
        view.TopLeftX + view.Width > 0.f &&
        view.TopLeftY + view.Height > 0.f;
}

bool NativeGameEyeDrawEncoder::prepare_offscreen_game_draw(
    ID3D11RenderTargetView* gameTarget,
    bool requireDrawableRaster) noexcept {
    if (!game_source_target_bound(gameTarget) ||
        !geometry_outputs_isolated(gameTarget) ||
        drawCount_ == (std::numeric_limits<std::uint64_t>::max)())
        return false;
    if (requireDrawableRaster) {
        Microsoft::WRL::ComPtr<ID3D11Resource> resource;
        Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
        gameTarget->GetResource(resource.GetAddressOf());
        if (!resource || FAILED(resource.As(&texture)) || !texture)
            return false;
        D3D11_TEXTURE2D_DESC allocation{};
        D3D11_RENDER_TARGET_VIEW_DESC selected{};
        texture->GetDesc(&allocation);
        gameTarget->GetDesc(&selected);
        const auto camera = native_game_camera_rtv_extent(allocation, selected);
        if (!camera.valid ||
            !camera_draw_coverage(context_, camera.width, camera.height))
            return false;
    }
    // Real game TARGET Clears and Copy/Stretch events scheduled at the
    // preceding ordinal belong to the XR eye, even if its next game Draw
    // switches to an auxiliary camera. Temporarily replay into the ring RTV,
    // preserving original MRTs/DSV/compute and pixel UAV bindings.
    if (sourceClears_ &&
        sourceClearCursor_ < sourceClears_->count[sourceClearEye_] &&
        sourceClears_->entries[sourceClearEye_][sourceClearCursor_]
            .afterDrawOrdinal <= drawCount_) {
        // The callback's current RS viewport/scissor can belong to a smaller
        // offscreen camera. Replay source-authored TARGET rectangles through
        // the independently captured XR-eye raster; otherwise a valid full
        // eye clear becomes cropped and leaves stale car/menu/race pixels.
        // Restore offscreen RS and all its MRT/UAV outputs before the next
        // authentic game Draw/DrawIndexed.
        if (!eyeRasterReady_) return false;
        ScopedNativePostpassOutputs restore(context_);
        ScopedNativeEyeRasterForSourceReplay eyeRaster(
            context_, eyeViewport_, eyeScissor_, eyeRasterizer_.Get());
        if (!eyeRaster.valid()) return false;
        ID3D11RenderTargetView* eye = eyeTarget_;
        context_->OMSetRenderTargets(1u, &eye, eyeDepth_);
        if (!replay_due_source_clears()) return false;
    }
    return game_source_target_bound(gameTarget) &&
        geometry_outputs_isolated(gameTarget);
}

bool NativeGameEyeDrawEncoder::draw_offscreen(
    ID3D11RenderTargetView* gameTarget,
    UINT vertexCount, UINT startVertex) noexcept {
    if (!vertexCount || !prepare_offscreen_game_draw(gameTarget, true))
        return false;
    const bool eligible = unpredicated_color_evidence() &&
        source_color_writable(gameTarget) &&
        raster_primitive_possible(vertexCount);
    context_->Draw(vertexCount, startVertex);
    ++drawCount_; // source ordinal, NEVER direct XR color evidence
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        remember_offscreen_color_source(gameTarget);
    }
    return true;
}

bool NativeGameEyeDrawEncoder::draw_offscreen_indexed(
    ID3D11RenderTargetView* gameTarget,
    UINT indexCount, UINT startIndex, INT baseVertex) noexcept {
    if (!indexCount || !prepare_offscreen_game_draw(gameTarget, true))
        return false;
    const bool eligible = unpredicated_color_evidence() &&
        source_color_writable(gameTarget) &&
        raster_primitive_possible(indexCount);
    context_->DrawIndexed(indexCount, startIndex, baseVertex);
    ++drawCount_;
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        remember_offscreen_color_source(gameTarget);
    }
    return true;
}


 // Instanced menu/vehicle camera draws also belong to the real source stream.
 // They are one game command each regardless of instance count. Only a later
 // game-authored GPU Copy/Stretch may turn their pixels into OpenXR eye color;
 // never certify an offscreen instance as a direct XR-eye color Draw.
bool NativeGameEyeDrawEncoder::draw_offscreen_instanced(
    ID3D11RenderTargetView* gameTarget, UINT verticesPerInstance,
    UINT instanceCount, UINT startVertex, UINT startInstance) noexcept {
    if (!live_game_stereo::may_issue_instanced(
            verticesPerInstance, instanceCount, drawCount_) ||
        !prepare_offscreen_game_draw(gameTarget, true))
        return false;
    const bool eligible = unpredicated_color_evidence() &&
        source_color_writable(gameTarget) &&
        raster_primitive_possible(verticesPerInstance);
    context_->DrawInstanced(
        verticesPerInstance, instanceCount, startVertex, startInstance);
    ++drawCount_;
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        remember_offscreen_color_source(gameTarget);
    }
    return true;
}

bool NativeGameEyeDrawEncoder::draw_offscreen_indexed_instanced(
    ID3D11RenderTargetView* gameTarget, UINT indicesPerInstance,
    UINT instanceCount, UINT startIndex, INT baseVertex,
    UINT startInstance) noexcept {
    if (!live_game_stereo::may_issue_instanced(
            indicesPerInstance, instanceCount, drawCount_) ||
        !prepare_offscreen_game_draw(gameTarget, true))
        return false;
    const bool eligible = unpredicated_color_evidence() &&
        source_color_writable(gameTarget) &&
        raster_primitive_possible(indicesPerInstance);
    context_->DrawIndexedInstanced(
        indicesPerInstance, instanceCount, startIndex,
        baseVertex, startInstance);
    ++drawCount_;
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        remember_offscreen_color_source(gameTarget);
    }
    return true;
}

void NativeGameEyeDrawEncoder::set_source_clear_timeline(
    const NativeGameEyePartialTargetClear* clears, std::uint32_t eye) noexcept {
    sourceClears_ = (clears && eye < 2u) ? clears : nullptr;
    sourceClearEye_ = eye;
    sourceClearCursor_ = 0u;
}

// Real game menu/vehicle auxiliary camera Clears must write the camera's
// own target before source Draw/DrawIndexed and chronological GPU Copy/Stretch.
// Never convert them into direct-eye color evidence.
bool NativeGameEyeDrawEncoder::clear_offscreen_game_color(
    ID3D11RenderTargetView* gameTarget, std::uint32_t argb,
    const D3D11_RECT* region) noexcept {
    if (!prepare_offscreen_game_draw(gameTarget, false)) return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> texture;
    gameTarget->GetResource(resource.GetAddressOf());
    if (!resource || FAILED(resource.As(&texture)) || !texture) return false;
    D3D11_TEXTURE2D_DESC desc{};
    texture->GetDesc(&desc);
    D3D11_RENDER_TARGET_VIEW_DESC viewDesc{};
    gameTarget->GetDesc(&viewDesc);
    const auto camera = native_game_camera_rtv_extent(desc, viewDesc);
    if (!camera.valid) return false;
    const auto covered = camera_clear_coverage(
        context_, camera.width, camera.height, region);
    if (!covered.valid) return false;
    if (covered.empty) return true; // genuine D3D9 clipped no-op, no GPU write
    const D3D11_RECT* actual = covered.full ? nullptr : &covered.rect;
    const bool cropped = actual != nullptr;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext1> rectContext;
    if (cropped)
        (void)context_->QueryInterface(
            IID_PPV_ARGS(rectContext.GetAddressOf()));
    // The source viewport/scissor may crop even a null pRects Clear.
    // D3D11.0 must rasterize the cropped region; never wipe the entire
    // menu/car camera nor silently discard the genuine game Clear.
    const bool shaderSupported = cropped && !rectContext &&
        native_game_partial_color_shader_rtv(context_, gameTarget);
    const auto route = live_game_stereo::color_clear_route(
        cropped, actual ? actual->left : 0,
        actual ? actual->top : 0, actual ? actual->right : 0,
        actual ? actual->bottom : 0, camera.width, camera.height,
        rectContext != nullptr, shaderSupported);
    constexpr float scale = 1.0f / 255.0f;
    const float rgba[4]{
        static_cast<float>((argb >> 16) & 0xffu) * scale,
        static_cast<float>((argb >> 8) & 0xffu) * scale,
        static_cast<float>(argb & 0xffu) * scale,
        static_cast<float>((argb >> 24) & 0xffu) * scale};
    switch (route) {
    case live_game_stereo::NativeColorClearRoute::FullRtv:
        context_->ClearRenderTargetView(gameTarget, rgba);
        invalidate_offscreen_color_source(gameTarget);
        return true;
    case live_game_stereo::NativeColorClearRoute::ClearView:
        rectContext->ClearView(gameTarget, rgba, actual, 1u);
        invalidate_offscreen_color_source(gameTarget);
        return true;
    case live_game_stereo::NativeColorClearRoute::ShaderRaster: {
        // Keep the original audited D3D11.0 shader-raster Clear dispatch.
        // Only a successfully queued camera Clear invalidates old Draw color.
        const bool issued = [&]() noexcept {
            return raster_partial_eye_color_clear(
                context_, gameTarget, camera.width, camera.height,
                *actual, rgba);
        }();
        if (issued) invalidate_offscreen_color_source(gameTarget);
        return issued;
    }
    default:
        return false; // malformed region or unsupported target; DX9Ex owns it
    }
}

// The game's offscreen DSV must be actively bound on the SAME context and
// device, independent of the OpenXR ring depth, and compatible with its
// currently bound color camera. Full Clears ignore viewport and scissor.
bool NativeGameEyeDrawEncoder::clear_offscreen_game_depth_stencil(
    ID3D11RenderTargetView* gameTarget, ID3D11DepthStencilView* gameDepth,
    bool clearDepth, float depth, bool clearStencil,
    std::uint8_t stencil, const D3D11_RECT* region) noexcept {
    if (!gameDepth || gameDepth == eyeDepth_ ||
        (!clearDepth && !clearStencil) ||
        (clearDepth && (!std::isfinite(depth) || depth < 0.f || depth > 1.f)) ||
        !prepare_offscreen_game_draw(gameTarget, false)) return false;
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> boundDepth;
    context_->OMGetRenderTargets(0u, nullptr, boundDepth.GetAddressOf());
    if (boundDepth.Get() != gameDepth) return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> depthResource, colorResource;
    Microsoft::WRL::ComPtr<ID3D11Resource> eyeDepthResource;
    gameDepth->GetResource(depthResource.GetAddressOf());
    gameTarget->GetResource(colorResource.GetAddressOf());
    if (eyeDepth_) eyeDepth_->GetResource(eyeDepthResource.GetAddressOf());
    if (!depthResource || !colorResource ||
        depthResource.Get() == eyeDepthResource.Get() ||
        depthResource.Get() == colorResource.Get()) return false;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> depthTexture, colorTexture;
    if (FAILED(depthResource.As(&depthTexture)) || !depthTexture ||
        FAILED(colorResource.As(&colorTexture)) || !colorTexture) return false;
    Microsoft::WRL::ComPtr<ID3D11Device> owner, depthOwner;
    context_->GetDevice(owner.GetAddressOf());
    depthTexture->GetDevice(depthOwner.GetAddressOf());
    D3D11_TEXTURE2D_DESC dd{}, cd{};
    depthTexture->GetDesc(&dd);
    colorTexture->GetDesc(&cd);
    D3D11_RENDER_TARGET_VIEW_DESC colorViewDesc{};
    D3D11_DEPTH_STENCIL_VIEW_DESC depthViewDesc{};
    gameTarget->GetDesc(&colorViewDesc);
    gameDepth->GetDesc(&depthViewDesc);
    const auto camera = native_game_camera_rtv_extent(cd, colorViewDesc);
    const auto cameraDepth = native_game_camera_dsv_extent(dd, depthViewDesc);
    if (!owner || owner.Get() != depthOwner.Get() ||
        !native_game_camera_depth_compatible(
            camera, cameraDepth, cd.SampleDesc.Count, dd.SampleDesc.Count,
            cd.SampleDesc.Quality, dd.SampleDesc.Quality) ||
        dd.Usage != D3D11_USAGE_DEFAULT || dd.CPUAccessFlags ||
        (dd.BindFlags & D3D11_BIND_DEPTH_STENCIL) == 0u) return false;
    const auto covered = camera_clear_coverage(
        context_, camera.width, camera.height, region);
    if (!covered.valid) return false;
    if (covered.empty) return true; // a real viewport/scissor-clipped Z/S no-op
    const D3D11_RECT* actual = covered.full ? nullptr : &covered.rect;
    const auto route = live_game_stereo::depth_clear_route(
        actual != nullptr, actual ? actual->left : 0,
        actual ? actual->top : 0, actual ? actual->right : 0,
        actual ? actual->bottom : 0, camera.width, camera.height);
    if (route == live_game_stereo::NativeDepthClearRoute::Reject)
        return false;
    if (route == live_game_stereo::NativeDepthClearRoute::PartialRaster)
        return raster_partial_eye_depth_clear(
            context_, gameDepth, camera.width, camera.height, *actual,
            depth, stencil, clearDepth, clearStencil);
    const UINT flags = (clearDepth ? D3D11_CLEAR_DEPTH : 0u) |
                       (clearStencil ? D3D11_CLEAR_STENCIL : 0u);
    context_->ClearDepthStencilView(gameDepth, flags, depth, stencil);
    return true;
}

bool NativeGameEyeDrawEncoder::replay_due_source_clears() noexcept {
    if (!sourceClears_) return true;
    const auto count = sourceClears_->count[sourceClearEye_];
    if (count > NativeGameEyePartialTargetClear::kMaxRectsPerEye) return false;
    while (sourceClearCursor_ < count) {
        const auto& clear = sourceClears_->entries[sourceClearEye_][sourceClearCursor_];
        if (clear.afterDrawOrdinal > drawCount_) return true;
        if (clear.afterDrawOrdinal < drawCount_) return false;
        if (clear.kind == NativeGameEyePartialTargetClear::Kind::TargetRect) {
            if (!clear_target_argb(clear.argb, &clear.rect)) return false;
            // clear_target_argb() updates this source color history itself,
            // identical to a direct game callback Clear. Do not count a
            // queued full Clear twice or retain pre-Clear eye color evidence.
        } else if (clear.kind ==
                   NativeGameEyePartialTargetClear::Kind::FullDepthStencil) {
            const bool partial = clear.rect.left || clear.rect.top ||
                clear.rect.right || clear.rect.bottom;
            if (!clear_depth_stencil(clear.depth, clear.stencil,
                                     clear.clearDepth, clear.clearStencil,
                                     partial ? &clear.rect : nullptr))
                return false;
        } else if (clear.kind ==
                   NativeGameEyePartialTargetClear::Kind::SourceCopy) {
            const bool proven = offscreen_color_source_proven(
                clear.source, clear.sourceArraySlice, clear.sourceMipSlice,
                clear.sourceBox);
            if (!copy_game_surface(clear.source, &clear.sourceBox,
                                   clear.destX, clear.destY,
                                   clear.sourceArraySlice, clear.sourceMipSlice))
                return false;
            // Game-authored offscreen menu/car/race compositing can write
            // real eye color even when its on-eye geometry only updates Z.
            // Count only a postpass of an actually color-written camera
            // subresource; unrelated stale textures never certify this eye.
            if (proven) ++authoredColorPostpassCount_;
        } else if (clear.kind ==
                   NativeGameEyePartialTargetClear::Kind::SourceStretch) {
            const bool proven = offscreen_color_source_proven(
                clear.source, clear.sourceArraySlice, clear.sourceMipSlice);
            if (!stretch_game_surface(clear.source, clear.sourceBox,
                                      clear.destination, clear.linearFilter,
                                      clear.sourceArraySlice, clear.sourceMipSlice))
                return false;
            if (proven) ++authoredColorPostpassCount_;
        } else {
            return false; // Reject unrecognized source commands, never fabricate a Clear.
        }
        ++sourceClearCursor_;
    }
    return true;
}

bool NativeGameEyeDrawEncoder::finish_source_clear_timeline() noexcept {
    return replay_due_source_clears() &&
        (!sourceClears_ ||
         sourceClearCursor_ == sourceClears_->count[sourceClearEye_]);
}

bool NativeGameEyeDrawEncoder::draw(
    UINT vertexCount, UINT startVertex) noexcept {
    if (!vertexCount || !eye_output_bound() ||
        drawCount_ == (std::numeric_limits<std::uint64_t>::max)())
        return false;
    if (!replay_due_source_clears() || !eye_output_bound()) return false;
    const bool unpredicated = unpredicated_color_evidence();
    const bool eligible = unpredicated &&
        raster_primitive_possible(vertexCount);
    const bool colorWritable = live_game_stereo::color_certifiable(
        eye_color_writable(), eligible);
    context_->Draw(vertexCount, startVertex);
    ++drawCount_;
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        ++unpredicatedEyeDrawCount_;
    }
    if (colorWritable) ++colorDrawCount_;
    return true;
}

bool NativeGameEyeDrawEncoder::draw_indexed(
    UINT indexCount, UINT startIndex, INT baseVertex) noexcept {
    if (!indexCount || !eye_output_bound() ||
        drawCount_ == (std::numeric_limits<std::uint64_t>::max)())
        return false;
    if (!replay_due_source_clears() || !eye_output_bound()) return false;
    const bool unpredicated = unpredicated_color_evidence();
    const bool eligible = unpredicated &&
        raster_primitive_possible(indexCount);
    const bool colorWritable = live_game_stereo::color_certifiable(
        eye_color_writable(), eligible);
    context_->DrawIndexed(indexCount, startIndex, baseVertex);
    ++drawCount_;
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        ++unpredicatedEyeDrawCount_;
    }
    if (colorWritable) ++colorDrawCount_;
    return true;
}

// D3D9 game instancing is one authored primitive command, not N separate
// source ordinals. Reuse the same timeline, bound eye verification and
// fail-closed color evidence for both non-indexed and indexed instances.
bool NativeGameEyeDrawEncoder::draw_instanced(
    UINT verticesPerInstance, UINT instanceCount,
    UINT startVertex, UINT startInstance) noexcept {
    if (!live_game_stereo::may_issue_instanced(
            verticesPerInstance, instanceCount, drawCount_) ||
        !eye_output_bound() || !replay_due_source_clears())
        return false;
    // A native GPU SourceCopy/Stretch can temporarily rebind OM. Preserve
    // the audited pre-replay guard AND recheck this actual XR-eye raster
    // after chronological postpasses, before the game GPU Draw is issued.
    if (!eye_output_bound()) return false;
    const bool unpredicated = unpredicated_color_evidence();
    const bool eligible = unpredicated &&
        raster_primitive_possible(verticesPerInstance);
    const bool colorWritable = live_game_stereo::color_certifiable(
        eye_color_writable(), eligible);
    context_->DrawInstanced(
        verticesPerInstance, instanceCount, startVertex, startInstance);
    ++drawCount_;
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        ++unpredicatedEyeDrawCount_;
    }
    if (colorWritable) ++colorDrawCount_;
    return true;
}

bool NativeGameEyeDrawEncoder::draw_indexed_instanced(
    UINT indicesPerInstance, UINT instanceCount, UINT startIndex,
    INT baseVertex, UINT startInstance) noexcept {
    if (!live_game_stereo::may_issue_instanced(
            indicesPerInstance, instanceCount, drawCount_) ||
        !eye_output_bound() || !replay_due_source_clears())
        return false;
    // A native GPU SourceCopy/Stretch can temporarily rebind OM. Preserve
    // the audited pre-replay guard AND recheck this actual XR-eye raster
    // after chronological postpasses, before the game GPU Draw is issued.
    if (!eye_output_bound()) return false;
    const bool unpredicated = unpredicated_color_evidence();
    const bool eligible = unpredicated &&
        raster_primitive_possible(indicesPerInstance);
    const bool colorWritable = live_game_stereo::color_certifiable(
        eye_color_writable(), eligible);
    context_->DrawIndexedInstanced(
        indicesPerInstance, instanceCount, startIndex,
        baseVertex, startInstance);
    ++drawCount_;
    if (eligible) {
        ++unpredicatedGameDrawCount_;
        ++unpredicatedEyeDrawCount_;
    }
    if (colorWritable) ++colorDrawCount_;
    return true;
}

bool NativeGameEyeDrawEncoder::clear_target_argb(
    std::uint32_t argb, const D3D11_RECT* region) noexcept {
    lastTargetClearFull_ = false;
    if (!eye_targets_bound() || !targetWidth_ || !targetHeight_) return false;
    // D3D9 Clear clips even explicit TARGET rectangles to the live viewport
    // and (when enabled) scissor. D3D11 ClearRTV/ClearView ignore RS clips.
    // Do not erase another menu/HUD area of the native L/R eye, and do not
    // reset geometry evidence for a nominal full RECT that is actually cropped.
    const auto covered = camera_clear_coverage(
        context_, targetWidth_, targetHeight_, region);
    if (!covered.valid) return false;
    if (covered.empty) return true; // genuine D3D9 clipped no-op
    const D3D11_RECT* actual = covered.full ? nullptr : &covered.rect;
    const bool cropped = actual != nullptr;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext1> rectContext;
    if (cropped)
        (void)context_->QueryInterface(
            IID_PPV_ARGS(rectContext.GetAddressOf()));
    constexpr float kByte = 1.0f / 255.0f;
    const float rgba[4]{
        static_cast<float>((argb >> 16) & 0xffu) * kByte,
        static_cast<float>((argb >> 8) & 0xffu) * kByte,
        static_cast<float>(argb & 0xffu) * kByte,
        static_cast<float>((argb >> 24) & 0xffu) * kByte};
    const bool shaderSupported = cropped && !rectContext &&
        native_game_partial_color_shader_rtv(context_, eyeTarget_);
    const auto route = live_game_stereo::color_clear_route(
        cropped, actual ? actual->left : 0,
        actual ? actual->top : 0, actual ? actual->right : 0,
        actual ? actual->bottom : 0, targetWidth_, targetHeight_,
        rectContext != nullptr, shaderSupported);
    bool written = false;
    switch (route) {
    case live_game_stereo::NativeColorClearRoute::FullRtv:
        context_->ClearRenderTargetView(eyeTarget_, rgba);
        written = true;
        break;
    case live_game_stereo::NativeColorClearRoute::ClearView:
        rectContext->ClearView(eyeTarget_, rgba, actual, 1u);
        written = true;
        break;
    case live_game_stereo::NativeColorClearRoute::ShaderRaster:
        written = raster_partial_eye_color_clear(
            context_, eyeTarget_, targetWidth_, targetHeight_, *actual, rgba);
        break;
    default:
        return false;
    }
    lastTargetClearFull_ = written && covered.full;
    if (written) {
        // A direct, genuine game TARGET Clear can occur after eye geometry
        // without going through set_source_clear_timeline(). Previously it
        // left old Draw/Copy/Stretch color evidence live, certifying pixels
        // that the GPU had already erased. Keep both Clear entrypoints in
        // one real command chronology; cropped Clears preserve prior color.
        const auto history = live_game_stereo::after_target_clear(
            {colorDrawCount_, authoredColorPostpassCount_,
             authoredFullColorClearCount_, lastFullClearDrawOrdinal_},
            lastTargetClearFull_, drawCount_);
        colorDrawCount_ = history.colorDraws;
        authoredColorPostpassCount_ = history.colorPostpasses;
        authoredFullColorClearCount_ = history.fullTargetClears;
        lastFullClearDrawOrdinal_ = history.lastFullClearDrawOrdinal;
        if (lastTargetClearFull_) {
            unpredicatedAtLastFullClear_ = unpredicatedGameDrawCount_;
            unpredicatedEyeAtLastFullClear_ = unpredicatedEyeDrawCount_;
        }
    }
    return written;
}

bool NativeGameEyeDrawEncoder::clear_depth_stencil(
    float depth, std::uint8_t stencil,
    bool clearDepth, bool clearStencil, const D3D11_RECT* region) noexcept {
    if (!eye_targets_bound() || (!clearDepth && !clearStencil) ||
        (clearDepth && (!std::isfinite(depth) ||
                        depth < 0.0f || depth > 1.0f)))
        return false;
    // The original D3D9 Z/stencil Clear is viewport/scissor clipped just
    // like TARGET, even if its pRects contains the entire eye. A native
    // whole-DSV Clear here would erase untouched HUD/car/race depth pixels.
    const auto covered = camera_clear_coverage(
        context_, targetWidth_, targetHeight_, region);
    if (!covered.valid) return false;
    if (covered.empty) return true;
    const D3D11_RECT* actual = covered.full ? nullptr : &covered.rect;
    const auto route = live_game_stereo::depth_clear_route(
        actual != nullptr, actual ? actual->left : 0,
        actual ? actual->top : 0, actual ? actual->right : 0,
        actual ? actual->bottom : 0, targetWidth_, targetHeight_);
    if (route == live_game_stereo::NativeDepthClearRoute::Reject)
        return false;
    if (route == live_game_stereo::NativeDepthClearRoute::PartialRaster)
        return raster_partial_eye_depth_clear(
            context_, eyeDepth_, targetWidth_, targetHeight_, *actual,
            depth, stencil, clearDepth, clearStencil);
    const UINT flags = (clearDepth ? D3D11_CLEAR_DEPTH : 0u) |
                       (clearStencil ? D3D11_CLEAR_STENCIL : 0u);
    context_->ClearDepthStencilView(eyeDepth_, flags,
                                    clearDepth ? depth : 1.0f, stencil);
    return true;
}

// Copy a genuine GPU-resident game intermediate (not the mono desktop
// backbuffer) after a real Draw without passing it through system memory.
// CopySubresourceRegion replays single-sample game pixels without scaling.
// MSAA offscreen menu/car/race color requires an explicit GPU resolve first;
// partial transfers resolve into a private temporary before copying the box.
// Never touch the original D3D9 StretchRect, game input or independent XR eye
// when source format, dimensions, ownership or resolve support is invalid.
bool NativeGameEyeDrawEncoder::copy_game_surface(
    ID3D11Texture2D* source, const D3D11_BOX* sourceRegion,
    std::int64_t destX, std::int64_t destY,
    UINT sourceArraySlice, UINT sourceMipSlice) noexcept
{
    if (!source || !eye_targets_bound() || !targetWidth_ || !targetHeight_)
        return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> eyeResource;
    eyeTarget_->GetResource(eyeResource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> eyeColor;
    if (!eyeResource || FAILED(eyeResource.As(&eyeColor)) ||
        !eyeColor || eyeColor.Get() == source)
        return false;
    Microsoft::WRL::ComPtr<ID3D11Device> owner, sourceOwner;
    context_->GetDevice(owner.GetAddressOf());
    source->GetDevice(sourceOwner.GetAddressOf());
    if (!owner || owner.Get() != sourceOwner.Get()) return false;
    D3D11_TEXTURE2D_DESC sourceDesc{}, eyeDesc{};
    source->GetDesc(&sourceDesc);
    eyeColor->GetDesc(&eyeDesc);
    const auto sourceMip = native_game_postpass_mip_extent(
        sourceDesc.Width, sourceDesc.Height, sourceDesc.MipLevels,
        sourceMipSlice, sourceDesc.ArraySize, sourceArraySlice,
        sourceDesc.SampleDesc.Count);
    if (!sourceMip.valid) return false;
    const UINT mipWidth = sourceMip.width;
    const UINT mipHeight = sourceMip.height;
    // Clip a game-origin unscaled postpass at the native eye edge, while
    // preserving the original pixel-to-pixel map. This must be done BEFORE
    // choosing Copy, shader format conversion, or MSAA Resolve. All of them
    // must see the same nonempty game source box.
    const D3D11_BOX requested = sourceRegion
        ? *sourceRegion
        : D3D11_BOX{0u, 0u, 0u, mipWidth, mipHeight, 1u};
    if (requested.front != 0u || requested.back != 1u)
        return false;
    const auto clippedCopy = native_game_copy_clipped_region(
        mipWidth, mipHeight,
        requested.left, requested.top, requested.right, requested.bottom,
        targetWidth_, targetHeight_, destX, destY);
    if (!clippedCopy.valid) return false;
    const D3D11_BOX box{
        clippedCopy.sourceLeft, clippedCopy.sourceTop, 0u,
        clippedCopy.sourceRight, clippedCopy.sourceBottom, 1u};
    const UINT eyeDestX = clippedCopy.destX;
    const UINT eyeDestY = clippedCopy.destY;
    // D3D9 StretchRect also performs format conversion for unscaled
    // menu/vehicle postpasses. CopySubresourceRegion cannot do that. Replay
    // the caller's exact mip-zero source rectangle with a native point-sampled
    // GPU shader instead of dropping both genuine game camera color outputs
    // or falling back to a CPU/desktop copy. The existing stretch admission
    // rejects unsupported/foreign resources before GPU mutation. This path
    // must never count its fullscreen shader triangle as game Draw evidence.
    if (sourceDesc.Format != eyeDesc.Format) {
        const UINT width = box.right - box.left;
        const UINT height = box.bottom - box.top;
        const UINT maxLong = static_cast<UINT>(
            (std::numeric_limits<LONG>::max)());
        if (eyeDestX > targetWidth_ || eyeDestY > targetHeight_ ||
            width > targetWidth_ - eyeDestX ||
            height > targetHeight_ - eyeDestY ||
            eyeDestX > maxLong || eyeDestY > maxLong ||
            width > maxLong - eyeDestX || height > maxLong - eyeDestY)
            return false;
        const D3D11_RECT destination{
            static_cast<LONG>(eyeDestX), static_cast<LONG>(eyeDestY),
            static_cast<LONG>(eyeDestX + width),
            static_cast<LONG>(eyeDestY + height)};
        // Unlike CopySubresourceRegion this path temporarily replaces
        // the entire OM/viewport/shader state to draw a conversion triangle.
        // A successful GPU postpass must also restore THIS native eye's
        // render/depth attachments before its next genuine game Draw.
        // If restoration fails, reject the frame (the producer quarantines
        // any already queued GPU writes) instead of publishing stale eyes.
        if (!stretch_game_surface(
                source, box, destination, false, sourceArraySlice,
                sourceMipSlice))
            return false;
        return eye_targets_bound();
    }
    // A game GPU post-pass may copy its RT to a DEFAULT shader-readable
    // intermediate before the eye compositor samples it. D3D11 GPU copy
    // accepts either owned RT or SRV texture as source; do not require a
    // redundant RTV merely for an unscaled, same-format CopySubresourceRegion.
    // GPU-only DEFAULT CopyResource destinations have no RTV/SRV bind flag.
    // They remain real, device-local game postpass sources for an unscaled,
    // identical-format CopySubresourceRegion. Shader conversion still needs
    // an RTV or SRV and multisample sources still need an RTV for resolve.
    // Game compute outputs may be UAV-only but are still GPU copyable.
    const bool gpuSourceBindable = native_game_postpass_gpu_source(
        sourceDesc.BindFlags, sourceDesc.SampleDesc.Count,
        D3D11_BIND_RENDER_TARGET, D3D11_BIND_SHADER_RESOURCE,
        D3D11_BIND_UNORDERED_ACCESS);
    constexpr UINT sharedFlags =
        D3D11_RESOURCE_MISC_SHARED | D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
        D3D11_RESOURCE_MISC_SHARED_NTHANDLE;
    // A menu/vehicle render pass can place its full-size game color in mip 0
    // of a GPU-only texture with a complete mip chain. CopySubresourceRegion
    // selects subresource 0 below; it does NOT copy the smaller mip levels.
    // MSAA sources still require exactly one mip and an explicit GPU resolve.
    const bool needsResolve = sourceDesc.SampleDesc.Count > 1u;
    if (sourceDesc.Format == DXGI_FORMAT_UNKNOWN ||
        sourceDesc.Format != eyeDesc.Format ||
        sourceDesc.MipLevels == 0u ||
        (needsResolve && sourceDesc.MipLevels != 1u) ||
        sourceArraySlice >= sourceDesc.ArraySize ||
        eyeDesc.MipLevels != 1u || eyeDesc.ArraySize != 1u ||
        sourceDesc.SampleDesc.Count == 0u ||
        eyeDesc.SampleDesc.Count != 1u ||
        sourceDesc.Usage != D3D11_USAGE_DEFAULT ||
        sourceDesc.CPUAccessFlags != 0u ||
        !gpuSourceBindable ||
        (sourceDesc.MiscFlags & sharedFlags) != 0u ||
        eyeDesc.Width != targetWidth_ || eyeDesc.Height != targetHeight_)
        return false;
    if (needsResolve) {
        // The only supported multisample source is a GPU color render
        // target. D3D11 cannot resolve a depth surface or an arbitrary
        // unresolvable/typeless color format; retain D3D9 in that case.
        UINT support = 0u;
        if ((sourceDesc.BindFlags & D3D11_BIND_RENDER_TARGET) == 0u ||
            FAILED(owner->CheckFormatSupport(sourceDesc.Format, &support)) ||
            (support & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) == 0u)
            return false;
    }
    if (box.right > mipWidth || box.bottom > mipHeight ||
        eyeDesc.Width != targetWidth_ || eyeDesc.Height != targetHeight_)
        return false;

    // Only mip zero of the caller-proven camera eye slice enters the native
    // shared RTV. Whole-array CopyResource would mismatch a single-eye target.
    const UINT sourceSubresource =
        D3D11CalcSubresource(sourceMipSlice, sourceArraySlice,
                             sourceDesc.MipLevels);
    // Never use CopyResource for a full mip chain into a one-mip XR eye.
    // A full-source MSAA resolve can write directly into the full-size eye.
    // Cropped menu/vehicle postpasses must not overwrite unaffected pixels:
    // resolve the original full source to an owned, GPU-only intermediate,
    // then copy only the genuine source rectangle to its eye destination.
    const bool fullResolve = needsResolve &&
        box.left == 0u && box.top == 0u &&
        box.right == sourceDesc.Width && box.bottom == sourceDesc.Height &&
        eyeDestX == 0u && eyeDestY == 0u &&
        sourceDesc.Width == eyeDesc.Width &&
        sourceDesc.Height == eyeDesc.Height;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> resolved;
    // Menu/vehicle/race MSAA partial copies may occur every eye and every
    // frame. Keep one device-local, single-sample private resolve destination
    // instead of allocating full-resolution GPU memory for every Copy event.
    // Serialize cache selection THROUGH command recording: the immediate
    // context orders Resolve -> Copy before this scratch is reused by eye R.
    static std::mutex resolveScratchMutex;
    static Microsoft::WRL::ComPtr<ID3D11Device> resolveScratchDevice;
    static Microsoft::WRL::ComPtr<ID3D11Texture2D> resolveScratch;
    static NativeGamePostpassScratchKey resolveScratchKey{};
    std::unique_lock<std::mutex> resolveScratchLock;
    if (needsResolve && !fullResolve) {
        resolveScratchLock = std::unique_lock<std::mutex>(resolveScratchMutex);
        D3D11_TEXTURE2D_DESC resolvedDesc = sourceDesc;
        resolvedDesc.SampleDesc.Count = 1u;
        resolvedDesc.SampleDesc.Quality = 0u;
        resolvedDesc.ArraySize = 1u; // selected camera only
        resolvedDesc.BindFlags = 0u; // GPU copy-only, never alias an RTV/SRV
        resolvedDesc.MiscFlags = 0u;
        const NativeGamePostpassScratchKey key{
            resolvedDesc.Width, resolvedDesc.Height,
            static_cast<std::uint32_t>(resolvedDesc.Format), resolvedDesc.BindFlags};
        if (resolveScratchDevice.Get() != owner.Get() ||
            !resolveScratch ||
            !native_game_postpass_scratch_matches(resolveScratchKey, key)) {
            Microsoft::WRL::ComPtr<ID3D11Texture2D> fresh;
            if (FAILED(owner->CreateTexture2D(
                    &resolvedDesc, nullptr, fresh.GetAddressOf())) || !fresh)
                return false;
            resolveScratch = std::move(fresh);
            resolveScratchDevice = owner;
            resolveScratchKey = key;
        }
        resolved = resolveScratch;
    }

    // The game may have additional color MRT attachments (e.g. deferred
    // vehicle/HUD output) beside this eye's RT0. A one-RTV rebind after the
    // copy silently discards RT1..RT7 and breaks the next real game Draw.
    // Preserve the complete OM set, including its exact depth attachment,
    // while temporarily unbinding both copy source and destination.
    {
        ScopedNativePostpassOutputs restore{context_};
        context_->OMSetRenderTargets(0u, nullptr, nullptr);
        if (needsResolve) {
            context_->ResolveSubresource(
                fullResolve ? eyeColor.Get() : resolved.Get(),
                0u, source, sourceSubresource, sourceDesc.Format);
            if (!fullResolve) {
                context_->CopySubresourceRegion(
                    eyeColor.Get(), 0u, eyeDestX, eyeDestY, 0u,
                    resolved.Get(), 0u, &box);
            }
        } else {
            context_->CopySubresourceRegion(
                eyeColor.Get(), 0u, eyeDestX, eyeDestY, 0u,
                source, sourceSubresource, &box);
        }
    }
    return eye_targets_bound();
}


// The D3D9 game and native OpenXR path may share an immediate D3D11 context.
// A game eye pass must rasterize into the ring's actual RTV, not whichever
// desktop/probe target happened to be bound by an earlier native draw. Save
// and restore the existing OM/viewport/scissor bindings even on a partial
// callback failure; the ring separately quarantines all potentially queued
// GPU writes. The callback continues to own its shader/IA/texture state.
namespace {
class ScopedNativeGameEyeOutput final {
public:
    ScopedNativeGameEyeOutput(ID3D11DeviceContext* context,
                              std::uint32_t width,
                              std::uint32_t height) noexcept
        : context_(context), width_(width), height_(height) {
        if (!context_ || !width_ || !height_) return;
        capture_native_om_outputs(
            context_, savedTargets_, &savedDepth_, savedOmOutputs_);
        context_->OMGetBlendState(&savedBlend_, savedBlendFactors_, &savedSampleMask_);
        context_->OMGetDepthStencilState(&savedDepthState_, &savedStencilRef_);
        context_->RSGetState(&savedRasterizer_);
        // A game-authored Draw/DrawIndexed callback may replace IA and VS/PS
        // state for its eye. Restore the original caller bindings before EACH
        // eye as well as on exit: right-eye replay must not inherit left-eye
        // vertex streams, topology or shader class interfaces.
        context_->IAGetInputLayout(&savedInputLayout_);
        context_->IAGetVertexBuffers(
            0u, D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT,
            savedVertexBuffers_, savedStrides_, savedOffsets_);
        context_->IAGetIndexBuffer(&savedIndexBuffer_,
                                   &savedIndexFormat_, &savedIndexOffset_);
        context_->IAGetPrimitiveTopology(&savedTopology_);
        context_->VSGetShader(&savedVS_, savedVSClasses_, &savedVSClassCount_);
        context_->PSGetShader(&savedPS_, savedPSClasses_, &savedPSClassCount_);
        // D3D9 emits VS/PS game geometry, not host GS/tessellation programs.
        // Save these stages so a shared OpenXR context cannot distort either
        // native eye's Draw, while preserving the original caller pipeline.
        context_->GSGetShader(&savedGS_, savedGSClasses_, &savedGSClassCount_);
        context_->HSGetShader(&savedHS_, savedHSClasses_, &savedHSClassCount_);
        context_->DSGetShader(&savedDS_, savedDSClasses_, &savedDSClassCount_);
        // Preserve programmable bindings for VS/PS and inherited GS/HS/DS
        // across left/right game replay and the OpenXR caller's next frame.
        // A game postpass or injected callback can change these resources;
        // restoring shaders alone leaves stale SRVs, samplers and CBs.
        // Preserve shader inputs for both game camera draws. The first eye
        // can swap or unbind resources; the second must start from the same
        // source game state, including vertex texture fetch and constant data.
        context_->VSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedVSResources_);
        context_->PSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedPSResources_);
        context_->VSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedVSSamplers_);
        context_->PSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedPSSamplers_);
        context_->VSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedVSConstants_);
        context_->PSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedPSConstants_);
        context_->GSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedGSResources_);
        context_->GSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedGSSamplers_);
        context_->GSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedGSConstants_);
        context_->HSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedHSResources_);
        context_->HSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedHSSamplers_);
        context_->HSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedHSConstants_);
        context_->DSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedDSResources_);
        context_->DSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedDSSamplers_);
        context_->DSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedDSConstants_);
        // Real menu/race camera postpasses may use CS shader inputs and UAV
        // outputs between the two game eyes. The second eye must start with
        // the same compute pipeline, and the desktop/host caller must retain it.
        context_->CSGetShader(&savedCS_, savedCSClasses_, &savedCSClassCount_);
        context_->CSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedCSResources_);
        context_->CSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedCSSamplers_);
        context_->CSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedCSConstants_);
        context_->CSGetUnorderedAccessViews(0u, D3D11_PS_CS_UAV_REGISTER_COUNT, savedCSOutputs_);
        // The caller may be in a host occlusion-predicated/stream-output
        // postpass. D3D9 game Draw/DrawIndexed never inherited those stages.
        // Borrow the immediate context without suppressing either eye's
        // pixels or writing game vertices into the host's SO buffers.
        context_->GetPredication(&savedPredicate_, &savedPredicateValue_);
        context_->SOGetTargets(D3D11_SO_BUFFER_SLOT_COUNT, savedStreamOut_);
        viewportCount_ = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
        context_->RSGetViewports(&viewportCount_, savedViewports_);
        scissorCount_ = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
        context_->RSGetScissorRects(&scissorCount_, savedScissors_);
        active_ = true;
        isolate_game_draw_outputs();
    }
    ~ScopedNativeGameEyeOutput() noexcept {
        if (!active_) return;
        restore_native_om_outputs(
            context_, savedTargets_, savedDepth_, savedOmOutputs_);
        context_->OMSetBlendState(savedBlend_, savedBlendFactors_, savedSampleMask_);
        context_->OMSetDepthStencilState(savedDepthState_, savedStencilRef_);
        context_->RSSetState(savedRasterizer_);
        restore_draw_pipeline(false);
        // SOGetTargets exposes buffers but not their stream cursors. -1
        // resumes the caller's append position rather than resetting it to
        // zero; release the borrowed refs only after binding restoration.
        UINT append[D3D11_SO_BUFFER_SLOT_COUNT]{};
        for (auto& offset : append) offset = UINT(-1);
        context_->SOSetTargets(D3D11_SO_BUFFER_SLOT_COUNT, savedStreamOut_, append);
        context_->SetPredication(savedPredicate_, savedPredicateValue_);
        context_->RSSetViewports(viewportCount_,
                                 viewportCount_ ? savedViewports_ : nullptr);
        context_->RSSetScissorRects(scissorCount_,
                                   scissorCount_ ? savedScissors_ : nullptr);
        for (auto*& target : savedTargets_) {
            if (target) { target->Release(); target = nullptr; }
        }
        if (savedDepth_) { savedDepth_->Release(); savedDepth_ = nullptr; }
        for (auto*& om : savedOmOutputs_)
            if (om) { om->Release(); om = nullptr; }
        if (savedBlend_) { savedBlend_->Release(); savedBlend_ = nullptr; }
        if (savedDepthState_) { savedDepthState_->Release(); savedDepthState_ = nullptr; }
        if (savedRasterizer_) { savedRasterizer_->Release(); savedRasterizer_ = nullptr; }
        if (savedInputLayout_) savedInputLayout_->Release();
        if (savedIndexBuffer_) savedIndexBuffer_->Release();
        for (auto*& buffer : savedVertexBuffers_)
            if (buffer) { buffer->Release(); buffer = nullptr; }
        if (savedVS_) savedVS_->Release();
        if (savedPS_) savedPS_->Release();
        if (savedGS_) savedGS_->Release();
        if (savedHS_) savedHS_->Release();
        if (savedDS_) savedDS_->Release();
        if (savedCS_) savedCS_->Release();
        if (savedPredicate_) savedPredicate_->Release();
        for (auto*& buffer : savedStreamOut_)
            if (buffer) { buffer->Release(); buffer = nullptr; }
        for (UINT i = 0; i < savedCSClassCount_; ++i)
            if (savedCSClasses_[i]) savedCSClasses_[i]->Release();
        for (UINT i = 0; i < savedVSClassCount_; ++i)
            if (savedVSClasses_[i]) savedVSClasses_[i]->Release();
        for (UINT i = 0; i < savedPSClassCount_; ++i)
            if (savedPSClasses_[i]) savedPSClasses_[i]->Release();
        for (UINT i = 0; i < savedGSClassCount_; ++i)
            if (savedGSClasses_[i]) savedGSClasses_[i]->Release();
        for (UINT i = 0; i < savedHSClassCount_; ++i)
            if (savedHSClasses_[i]) savedHSClasses_[i]->Release();
        for (UINT i = 0; i < savedDSClassCount_; ++i)
            if (savedDSClasses_[i]) savedDSClasses_[i]->Release();
        // D3D11 Get* adds references to every saved slot, including slots
        // released by a callback. Balance all references after restoring.
        for (auto* p : savedVSResources_) if (p) p->Release();
        for (auto* p : savedPSResources_) if (p) p->Release();
        for (auto* p : savedVSSamplers_) if (p) p->Release();
        for (auto* p : savedPSSamplers_) if (p) p->Release();
        for (auto* p : savedVSConstants_) if (p) p->Release();
        for (auto* p : savedGSResources_) if (p) p->Release();
        for (auto* p : savedGSSamplers_) if (p) p->Release();
        for (auto* p : savedGSConstants_) if (p) p->Release();
        for (auto* p : savedHSResources_) if (p) p->Release();
        for (auto* p : savedHSSamplers_) if (p) p->Release();
        for (auto* p : savedHSConstants_) if (p) p->Release();
        for (auto* p : savedDSResources_) if (p) p->Release();
        for (auto* p : savedDSSamplers_) if (p) p->Release();
        for (auto* p : savedDSConstants_) if (p) p->Release();
        for (auto* p : savedPSConstants_) if (p) p->Release();
        for (auto* p : savedCSResources_) if (p) p->Release();
        for (auto* p : savedCSSamplers_) if (p) p->Release();
        for (auto* p : savedCSConstants_) if (p) p->Release();
        for (auto* p : savedCSOutputs_) if (p) p->Release();
    }
    ScopedNativeGameEyeOutput(const ScopedNativeGameEyeOutput&) = delete;
    ScopedNativeGameEyeOutput& operator=(const ScopedNativeGameEyeOutput&) = delete;

    bool bind(ID3D11RenderTargetView* target,
              ID3D11DepthStencilView* depth,
              const NativeGameEyeRasterState* raster,
              std::uint32_t eyeIndex) noexcept {
        if (!active_ || !target || !depth) return false;
        // The previous eye may have rebound IA/VB/IB/VS/PS. Start each
        // replay from exactly the captured caller state, not eye L residue.
        restore_draw_pipeline(true);
        isolate_game_draw_outputs();
        // The previous eye may also have changed blend, depth/stencil and
        // rasterizer state. Restore BEFORE each independent eye's Draw, not
        // only when exiting back to the desktop D3D9 fallback.
        context_->OMSetBlendState(savedBlend_, savedBlendFactors_, savedSampleMask_);
        context_->OMSetDepthStencilState(savedDepthState_, savedStencilRef_);
        context_->RSSetState(savedRasterizer_);
        const D3D11_VIEWPORT viewport = raster
            ? raster->viewport[eyeIndex]
            : D3D11_VIEWPORT{0.0f, 0.0f, static_cast<float>(width_),
                             static_cast<float>(height_), 0.0f, 1.0f};
        const D3D11_RECT scissor = raster
            ? raster->scissor[eyeIndex]
            : D3D11_RECT{0, 0, static_cast<LONG>(width_),
                         static_cast<LONG>(height_)};
        // A live road/car/building Draw must receive the depth/stencil surface
        // belonging to THIS eye. A color-only RT0 silently disables native
        // depth testing and allows the later eye to inherit stale depth.
        context_->OMSetRenderTargets(1u, &target, depth);
        context_->RSSetViewports(1u, &viewport);
        context_->RSSetScissorRects(1u, &scissor);
        return true;
    }
    // A camera callback may leave an OpenXR/host predicate or SO writer
    // active after its final geometry. The producer still owns pending game
    // Clear/Copy/Stretch events at the same last Draw ordinal; those commands
    // must not be conditionally discarded before this eye is sealed.
    void prepare_source_timeline_tail() noexcept {
        if (active_) isolate_game_draw_outputs();
    }
    [[nodiscard]] bool valid() const noexcept { return active_; }
private:
    void isolate_game_draw_outputs() noexcept {
        context_->SetPredication(nullptr, FALSE);
        // SOSetTargets with zero buffers detaches every inherited SO slot.
        // The game callbacks may change them again, so isolate each eye.
        context_->SOSetTargets(0u, nullptr, nullptr);
    }
    void restore_draw_pipeline(bool eyeReplay) noexcept {
        context_->IASetInputLayout(savedInputLayout_);
        context_->IASetVertexBuffers(
            0u, D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT,
            savedVertexBuffers_, savedStrides_, savedOffsets_);
        context_->IASetIndexBuffer(
            savedIndexBuffer_, savedIndexFormat_, savedIndexOffset_);
        context_->IASetPrimitiveTopology(savedTopology_);
        context_->VSSetShader(savedVS_, savedVSClasses_, savedVSClassCount_);
        context_->PSSetShader(savedPS_, savedPSClasses_, savedPSClassCount_);
        // Isolate both independent game cameras from inherited host or
        // previous-eye geometry/tessellation programs. Restore on scope exit.
        context_->GSSetShader(eyeReplay ? nullptr : savedGS_,
                              eyeReplay ? nullptr : savedGSClasses_,
                              eyeReplay ? 0u : savedGSClassCount_);
        context_->HSSetShader(eyeReplay ? nullptr : savedHS_,
                              eyeReplay ? nullptr : savedHSClasses_,
                              eyeReplay ? 0u : savedHSClassCount_);
        context_->DSSetShader(eyeReplay ? nullptr : savedDS_,
                              eyeReplay ? nullptr : savedDSClasses_,
                              eyeReplay ? 0u : savedDSClassCount_);
        context_->VSSetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedVSResources_);
        context_->PSSetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedPSResources_);
        context_->VSSetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedVSSamplers_);
        context_->PSSetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedPSSamplers_);
        context_->VSSetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedVSConstants_);
        context_->PSSetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedPSConstants_);
        context_->DSSetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedDSResources_);
        context_->DSSetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedDSSamplers_);
        context_->DSSetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedDSConstants_);
        context_->HSSetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedHSResources_);
        context_->HSSetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedHSSamplers_);
        context_->HSSetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedHSConstants_);
        context_->GSSetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedGSResources_);
        context_->GSSetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedGSSamplers_);
        context_->GSSetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedGSConstants_);
        // Restore real compute camera programs/inputs as well as all UAV
        // outputs without resetting append/consume counters. A callback may
        // change them for eye L, but eye R must see the source game's state.
        context_->CSSetShader(savedCS_, savedCSClasses_, savedCSClassCount_);
        context_->CSSetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedCSResources_);
        context_->CSSetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedCSSamplers_);
        context_->CSSetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedCSConstants_);
        UINT preserveCounters[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
        for (auto& count : preserveCounters) count = UINT(-1);
        context_->CSSetUnorderedAccessViews(0u, D3D11_PS_CS_UAV_REGISTER_COUNT,
                                            savedCSOutputs_, preserveCounters);
    }
    ID3D11DeviceContext* context_{};
    std::uint32_t width_{}, height_{};
    ID3D11RenderTargetView* savedTargets_[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
    ID3D11DepthStencilView* savedDepth_{};
    ID3D11UnorderedAccessView* savedOmOutputs_[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    ID3D11BlendState* savedBlend_{};
    FLOAT savedBlendFactors_[4]{};
    UINT savedSampleMask_{};
    ID3D11DepthStencilState* savedDepthState_{};
    UINT savedStencilRef_{};
    ID3D11RasterizerState* savedRasterizer_{};
    ID3D11InputLayout* savedInputLayout_{};
    ID3D11Buffer* savedVertexBuffers_[D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT]{};
    UINT savedStrides_[D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT]{};
    UINT savedOffsets_[D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11Buffer* savedIndexBuffer_{};
    DXGI_FORMAT savedIndexFormat_{DXGI_FORMAT_UNKNOWN};
    UINT savedIndexOffset_{};
    D3D11_PRIMITIVE_TOPOLOGY savedTopology_{D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED};
    ID3D11VertexShader* savedVS_{};
    ID3D11PixelShader* savedPS_{};
    ID3D11GeometryShader* savedGS_{};
    ID3D11HullShader* savedHS_{};
    ID3D11DomainShader* savedDS_{};
    ID3D11ComputeShader* savedCS_{};
    ID3D11Predicate* savedPredicate_{};
    BOOL savedPredicateValue_{FALSE};
    ID3D11Buffer* savedStreamOut_[D3D11_SO_BUFFER_SLOT_COUNT]{};
    ID3D11ShaderResourceView* savedCSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11SamplerState* savedCSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11Buffer* savedCSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11UnorderedAccessView* savedCSOutputs_[D3D11_PS_CS_UAV_REGISTER_COUNT]{};
    ID3D11ShaderResourceView* savedVSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11ShaderResourceView* savedPSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11SamplerState* savedVSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11SamplerState* savedPSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11Buffer* savedVSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11Buffer* savedPSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11ShaderResourceView* savedGSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11SamplerState* savedGSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11Buffer* savedGSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11ShaderResourceView* savedHSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11SamplerState* savedHSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11Buffer* savedHSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11ShaderResourceView* savedDSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11SamplerState* savedDSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11Buffer* savedDSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11ClassInstance* savedVSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedPSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedGSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedHSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedDSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedCSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    UINT savedCSClassCount_{D3D11_SHADER_MAX_INTERFACES};
    UINT savedVSClassCount_{D3D11_SHADER_MAX_INTERFACES};
    UINT savedPSClassCount_{D3D11_SHADER_MAX_INTERFACES};
    UINT savedGSClassCount_{D3D11_SHADER_MAX_INTERFACES};
    UINT savedHSClassCount_{D3D11_SHADER_MAX_INTERFACES};
    UINT savedDSClassCount_{D3D11_SHADER_MAX_INTERFACES};
    D3D11_VIEWPORT savedViewports_[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE]{};
    D3D11_RECT savedScissors_[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE]{};
    UINT viewportCount_{}, scissorCount_{};
    bool active_{};
};

// A D3D11.0 immediate context has no rectangle-aware ClearView. A genuine
// D3D9 menu/HUD TARGET rectangle still needs an EXACT color GPU operation:
// draw a non-game-evidence triangle restricted to that rectangle, with alpha,
// depth, blend, predicate and caller OM/IA/shader state restored on exit.
// Do not clear the entire eye (that would erase vehicle/race geometry).
[[nodiscard]] bool raster_partial_eye_color_clear(
    ID3D11DeviceContext* context, ID3D11RenderTargetView* target,
    std::uint32_t width, std::uint32_t height, const D3D11_RECT& rect,
    const float (&rgba)[4]) noexcept {
    if (!context || !target || !width || !height ||
        rect.left < 0 || rect.top < 0 || rect.right <= rect.left ||
        rect.bottom <= rect.top ||
        static_cast<std::uint32_t>(rect.right) > width ||
        static_cast<std::uint32_t>(rect.bottom) > height)
        return false;
    Microsoft::WRL::ComPtr<ID3D11Device> device;
    context->GetDevice(device.GetAddressOf());
    if (!device) return false;
    static std::mutex mutex;
    static Microsoft::WRL::ComPtr<ID3D11Device> cachedDevice;
    static Microsoft::WRL::ComPtr<ID3D11VertexShader> vertex;
    static Microsoft::WRL::ComPtr<ID3D11PixelShader> pixel;
    static Microsoft::WRL::ComPtr<ID3D11Buffer> constants;
    static Microsoft::WRL::ComPtr<ID3D11DepthStencilState> noDepth;
    std::lock_guard<std::mutex> lock(mutex);
    if (cachedDevice.Get() != device.Get()) {
        vertex.Reset(); pixel.Reset(); constants.Reset(); noDepth.Reset();
        cachedDevice = device;
    }
    if (!vertex || !pixel || !constants || !noDepth) {
        constexpr char shader[] = R"(
            cbuffer SourceClear : register(b0) { float4 clearColor; };
            float4 VS(uint id : SV_VertexID) : SV_POSITION {
                float2 uv = float2((id << 1) & 2, id & 2);
                return float4(uv * float2(2, -2) + float2(-1, 1), 0, 1);
            }
            float4 PS() : SV_TARGET { return clearColor; })";
        HMODULE module = LoadLibraryW(L"d3dcompiler_47.dll");
        if (!module) return false;
        struct CompilerLifetime {
            HMODULE handle;
            ~CompilerLifetime() noexcept { if (handle) FreeLibrary(handle); }
        } compiler{module};
        Microsoft::WRL::ComPtr<ID3DBlob> vsBlob, psBlob;
        const auto compile = reinterpret_cast<decltype(&D3DCompile)>(
            GetProcAddress(module, "D3DCompile"));
        if (!compile ||
            FAILED(compile(shader, sizeof(shader) - 1u, nullptr,
                nullptr, nullptr, "VS", "vs_4_0", 0u, 0u,
                vsBlob.GetAddressOf(), nullptr)) ||
            FAILED(compile(shader, sizeof(shader) - 1u, nullptr,
                nullptr, nullptr, "PS", "ps_4_0", 0u, 0u,
                psBlob.GetAddressOf(), nullptr)))
            return false;
        Microsoft::WRL::ComPtr<ID3D11VertexShader> v;
        Microsoft::WRL::ComPtr<ID3D11PixelShader> p;
        Microsoft::WRL::ComPtr<ID3D11Buffer> cb;
        Microsoft::WRL::ComPtr<ID3D11DepthStencilState> depthOff;
        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = 16u;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        D3D11_DEPTH_STENCIL_DESC ds{};
        ds.DepthEnable = FALSE;
        ds.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
        ds.StencilEnable = FALSE;
        if (FAILED(device->CreateVertexShader(
                vsBlob->GetBufferPointer(), vsBlob->GetBufferSize(),
                nullptr, v.GetAddressOf())) ||
            FAILED(device->CreatePixelShader(
                psBlob->GetBufferPointer(), psBlob->GetBufferSize(),
                nullptr, p.GetAddressOf())) ||
            FAILED(device->CreateBuffer(&desc, nullptr, cb.GetAddressOf())) ||
            FAILED(device->CreateDepthStencilState(
                &ds, depthOff.GetAddressOf())))
            return false;
        vertex = std::move(v); pixel = std::move(p);
        constants = std::move(cb); noDepth = std::move(depthOff);
    }
    ScopedNativeGameEyeOutput restore(context, width, height);
    if (!restore.valid()) return false;
    context->UpdateSubresource(constants.Get(), 0u, nullptr, rgba, 0u, 0u);
    context->OMSetRenderTargets(1u, &target, nullptr);
    context->OMSetDepthStencilState(noDepth.Get(), 0u);
    context->OMSetBlendState(nullptr, nullptr, 0xffffffffu);
    context->RSSetState(nullptr); // game Clear ignores saved scissor/cull
    const D3D11_VIEWPORT viewport{
        static_cast<float>(rect.left), static_cast<float>(rect.top),
        static_cast<float>(rect.right - rect.left),
        static_cast<float>(rect.bottom - rect.top), 0.0f, 1.0f};
    context->RSSetViewports(1u, &viewport);
    context->IASetInputLayout(nullptr);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(vertex.Get(), nullptr, 0u);
    context->PSSetShader(pixel.Get(), nullptr, 0u);
    context->GSSetShader(nullptr, nullptr, 0u);
    context->HSSetShader(nullptr, nullptr, 0u);
    context->DSSetShader(nullptr, nullptr, 0u);
    ID3D11Buffer* cb = constants.Get();
    context->PSSetConstantBuffers(0u, 1u, &cb);
    context->Draw(3u, 0u); // authored Clear, never native game Draw evidence
    return true;
}

// D3D11 ClearDepthStencilView ignores rectangles. Replay an original game's
// bounded Z/stencil Clear with a depth-only draw: a one-viewport triangle
// writes SV_Depth and/or REPLACE stencil without touching either eye color.
// This is GPU scene-state work, NOT a game-authored geometry Draw. The scoped
// pipeline also restores the original MRTs, shaders, IA and raster state.
[[nodiscard]] bool raster_partial_eye_depth_clear(
    ID3D11DeviceContext* context, ID3D11DepthStencilView* depthView,
    std::uint32_t width, std::uint32_t height, const D3D11_RECT& rect,
    float depth, std::uint8_t stencil,
    bool clearDepth, bool clearStencil) noexcept {
    if (!context || !depthView || !width || !height ||
        (!clearDepth && !clearStencil) ||
        rect.left < 0 || rect.top < 0 ||
        rect.right <= rect.left || rect.bottom <= rect.top ||
        static_cast<std::uint32_t>(rect.right) > width ||
        static_cast<std::uint32_t>(rect.bottom) > height ||
        (clearDepth && (!std::isfinite(depth) || depth < 0.f || depth > 1.f)))
        return false;
    Microsoft::WRL::ComPtr<ID3D11Device> device;
    context->GetDevice(device.GetAddressOf());
    if (!device) return false;

    // Shared immutable shader/state, one mutable CB and one immediate-context
    // submission at a time. Rebuild on device recreation/Reset.
    static std::mutex mutex;
    static Microsoft::WRL::ComPtr<ID3D11Device> cachedDevice;
    static Microsoft::WRL::ComPtr<ID3D11VertexShader> vertex;
    static Microsoft::WRL::ComPtr<ID3D11PixelShader> pixel;
    static Microsoft::WRL::ComPtr<ID3D11Buffer> constants;
    static Microsoft::WRL::ComPtr<ID3D11DepthStencilState> states[3];
    std::lock_guard<std::mutex> lock(mutex);
    if (cachedDevice.Get() != device.Get()) {
        cachedDevice = device;
        vertex.Reset();
        pixel.Reset();
        constants.Reset();
        for (auto& state : states) state.Reset();
    }
    if (!vertex || !pixel || !constants) {
        constexpr char shader[] = R"(
            cbuffer GameDepth : register(b0) { float4 value; };
            struct Vertex { float4 pos : SV_POSITION; };
            Vertex VS(uint id : SV_VertexID) {
                Vertex v;
                float2 uv = float2((id << 1) & 2, id & 2);
                v.pos = float4(uv * float2(2, -2) + float2(-1, 1), 0, 1);
                return v;
            }
            float PS(Vertex v) : SV_Depth { return value.x; })";
        HMODULE module = LoadLibraryW(L"d3dcompiler_47.dll");
        if (!module) return false;
        struct ModuleLifetime {
            HMODULE handle;
            ~ModuleLifetime() noexcept { if (handle) FreeLibrary(handle); }
        } compiler{module};
        // Blob COM Release must precede FreeLibrary for d3dcompiler_47.
        Microsoft::WRL::ComPtr<ID3DBlob> vsBlob, psBlob;
        const auto compile = reinterpret_cast<decltype(&D3DCompile)>(
            GetProcAddress(module, "D3DCompile"));
        if (!compile ||
            FAILED(compile(shader, sizeof(shader) - 1u, nullptr,
                nullptr, nullptr, "VS", "vs_4_0", 0u, 0u,
                vsBlob.GetAddressOf(), nullptr)) ||
            FAILED(compile(shader, sizeof(shader) - 1u, nullptr,
                nullptr, nullptr, "PS", "ps_4_0", 0u, 0u,
                psBlob.GetAddressOf(), nullptr)))
            return false;
        Microsoft::WRL::ComPtr<ID3D11VertexShader> v;
        Microsoft::WRL::ComPtr<ID3D11PixelShader> p;
        Microsoft::WRL::ComPtr<ID3D11Buffer> cb;
        if (FAILED(device->CreateVertexShader(
                vsBlob->GetBufferPointer(), vsBlob->GetBufferSize(),
                nullptr, v.GetAddressOf())) ||
            FAILED(device->CreatePixelShader(
                psBlob->GetBufferPointer(), psBlob->GetBufferSize(),
                nullptr, p.GetAddressOf())))
            return false;
        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = 16u;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        if (FAILED(device->CreateBuffer(&desc, nullptr, cb.GetAddressOf())))
            return false;
        vertex = std::move(v);
        pixel = std::move(p);
        constants = std::move(cb);
    }
    const unsigned mode = clearDepth ? (clearStencil ? 2u : 0u) : 1u;
    if (!states[mode]) {
        D3D11_DEPTH_STENCIL_DESC desc{};
        desc.DepthEnable = clearDepth ? TRUE : FALSE;
        desc.DepthWriteMask = clearDepth
            ? D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
        desc.DepthFunc = D3D11_COMPARISON_ALWAYS;
        desc.StencilEnable = clearStencil ? TRUE : FALSE;
        desc.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
        desc.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
        desc.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
        desc.FrontFace.StencilPassOp = D3D11_STENCIL_OP_REPLACE;
        desc.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
        desc.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
        desc.BackFace = desc.FrontFace;
        if (FAILED(device->CreateDepthStencilState(
                &desc, states[mode].GetAddressOf())))
            return false;
    }
    ScopedNativeGameEyeOutput saved(context, width, height);
    if (!saved.valid()) return false;
    const float values[4]{clearDepth ? depth : 1.f, 0.f, 0.f, 0.f};
    context->UpdateSubresource(constants.Get(), 0u, nullptr, values, 0u, 0u);
    context->OMSetRenderTargets(0u, nullptr, depthView);
    context->OMSetDepthStencilState(states[mode].Get(), stencil);
    context->OMSetBlendState(nullptr, nullptr, 0xffffffffu);
    context->RSSetState(nullptr); // disable inherited game scissor
    const D3D11_VIEWPORT viewport{
        static_cast<float>(rect.left), static_cast<float>(rect.top),
        static_cast<float>(rect.right - rect.left),
        static_cast<float>(rect.bottom - rect.top), 0.f, 1.f};
    context->RSSetViewports(1u, &viewport);
    context->IASetInputLayout(nullptr);
    ID3D11Buffer* emptyVB = nullptr;
    const UINT zero = 0u;
    context->IASetVertexBuffers(0u, 1u, &emptyVB, &zero, &zero);
    context->IASetIndexBuffer(nullptr, DXGI_FORMAT_UNKNOWN, 0u);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(vertex.Get(), nullptr, 0u);
    context->PSSetShader(pixel.Get(), nullptr, 0u);
    context->GSSetShader(nullptr, nullptr, 0u);
    context->HSSetShader(nullptr, nullptr, 0u);
    context->DSSetShader(nullptr, nullptr, 0u);
    ID3D11Buffer* cb = constants.Get();
    context->PSSetConstantBuffers(0u, 1u, &cb);
    context->Draw(3u, 0u);
    return true;
}
} // namespace

// A real game post-process StretchRect is not a CopySubresourceRegion: the
// source and destination spans can differ. Rasterize the genuine GPU color
// through point/linear filtering in a bounded eye viewport. This operation
// cannot certify new game geometry Draws and never touches D3D9/FFB/input.
bool NativeGameEyeDrawEncoder::stretch_game_surface(
    ID3D11Texture2D* source, const D3D11_BOX& srcBox,
    const D3D11_RECT& dest, bool linearFilter,
    UINT sourceArraySlice, UINT sourceMipSlice) noexcept {
    if (!source || !context_ || !eye_targets_bound()) return false;
    Microsoft::WRL::ComPtr<ID3D11Resource> resource;
    eyeTarget_->GetResource(resource.GetAddressOf());
    Microsoft::WRL::ComPtr<ID3D11Texture2D> eye;
    if (!resource || FAILED(resource.As(&eye)) || !eye ||
        eye.Get() == source) return false;
    Microsoft::WRL::ComPtr<ID3D11Device> device, owner;
    context_->GetDevice(device.GetAddressOf());
    source->GetDevice(owner.GetAddressOf());
    if (!device || device.Get() != owner.Get()) return false;
    D3D11_TEXTURE2D_DESC sd{}, ed{};
    source->GetDesc(&sd);
    eye->GetDesc(&ed);
    const auto sourceMip = native_game_postpass_mip_extent(
        sd.Width, sd.Height, sd.MipLevels, sourceMipSlice,
        sd.ArraySize, sourceArraySlice, sd.SampleDesc.Count);
    if (!sourceMip.valid) return false;
    const UINT mipWidth = sourceMip.width;
    const UINT mipHeight = sourceMip.height;
    constexpr UINT shared = D3D11_RESOURCE_MISC_SHARED |
        D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
        D3D11_RESOURCE_MISC_SHARED_NTHANDLE;
    if (!sd.Width || !sd.Height || sd.Format == DXGI_FORMAT_UNKNOWN ||
        sd.MipLevels == 0u || ed.Format == DXGI_FORMAT_UNKNOWN ||
        sd.ArraySize == 0u || sourceArraySlice >= sd.ArraySize ||
        ed.MipLevels != 1u ||
        ed.ArraySize != 1u || sd.SampleDesc.Count == 0u ||
        ed.SampleDesc.Count != 1u || ed.SampleDesc.Quality != 0u ||
        sd.Usage != D3D11_USAGE_DEFAULT ||
        sd.CPUAccessFlags != 0u || (sd.MiscFlags & shared) != 0u ||
        !native_game_postpass_gpu_source(
            sd.BindFlags, sd.SampleDesc.Count,
            D3D11_BIND_RENDER_TARGET, D3D11_BIND_SHADER_RESOURCE,
            D3D11_BIND_UNORDERED_ACCESS) ||
        ed.Width != targetWidth_ || ed.Height != targetHeight_ ||
        srcBox.front != 0u || srcBox.back != 1u ||
        srcBox.left >= srcBox.right || srcBox.top >= srcBox.bottom ||
        srcBox.right > mipWidth || srcBox.bottom > mipHeight) return false;
    const auto clipped = native_game_stretch_clipped_region(
        mipWidth, mipHeight, srcBox.left, srcBox.top,
        srcBox.right, srcBox.bottom, targetWidth_, targetHeight_,
        dest.left, dest.top, dest.right, dest.bottom);
    if (!clipped.valid) return false;
    // D3D11 postpass sampling converts the real game source into the eye's
    // render-target format; unlike GPU CopyResource, a filtered StretchRect
    // does not require identical DXGI formats. Menu/car offscreen RTs often
    // use a different format or have a full mip chain. Sample mip zero only.
    UINT sourceSupport = 0u, eyeSupport = 0u;
    if (FAILED(device->CheckFormatSupport(sd.Format, &sourceSupport)) ||
        FAILED(device->CheckFormatSupport(ed.Format, &eyeSupport)))
        return false;
    const auto transfer = native_game_stretch_source_transfer(
        sd.MipLevels, sd.SampleDesc.Count, sd.SampleDesc.Quality,
        (sd.BindFlags & D3D11_BIND_RENDER_TARGET) != 0u,
        (sd.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0u,
        (sourceSupport & D3D11_FORMAT_SUPPORT_SHADER_SAMPLE) != 0u,
        (eyeSupport & D3D11_FORMAT_SUPPORT_RENDER_TARGET) != 0u,
        (sourceSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) != 0u,
        (sd.BindFlags == 0u ||
         (sd.BindFlags & D3D11_BIND_UNORDERED_ACCESS) != 0u) &&
        sd.SampleDesc.Count == 1u);
    if (transfer == NativeGameStretchSourceTransfer::Reject)
        return false;

    // Compile once per D3D11 device, never once per Draw/menu postpass.
    // Serialize the cache and immediate-context state handoff across users.
    static std::mutex mutex;
    static Microsoft::WRL::ComPtr<ID3D11Device> cachedDevice;
    static Microsoft::WRL::ComPtr<ID3D11VertexShader> vs;
    static Microsoft::WRL::ComPtr<ID3D11PixelShader> ps;
    static Microsoft::WRL::ComPtr<ID3D11SamplerState> point, linear;
    static Microsoft::WRL::ComPtr<ID3D11Buffer> constants;
    static Microsoft::WRL::ComPtr<ID3D11Texture2D> sampledScratch;
    static NativeGamePostpassScratchKey sampledScratchKey{};
    std::lock_guard<std::mutex> lock(mutex);
    if (cachedDevice.Get() != device.Get()) {
        // Reset/device loss: do not carry any old-device sampled eye source.
        sampledScratch.Reset();
        sampledScratchKey = {};
    }
    if (cachedDevice.Get() != device.Get() || !vs ||
        !ps || !point || !linear || !constants) {
        constexpr char shader[] = R"(
            cbuffer Region : register(b0) { float4 uvRegion; float4 uvClamp; };
            Texture2D image : register(t0);
            SamplerState texSampler : register(s0);
            struct Varying { float4 position : SV_POSITION; float2 uv : TEXCOORD0; };
            Varying VS(uint i : SV_VertexID) {
                Varying v;
                v.uv = float2((i << 1) & 2, i & 2);
                v.position = float4(v.uv * float2(2,-2) + float2(-1,1), 0, 1);
                return v;
            }
            float4 PS(Varying v) : SV_TARGET {
                float2 requestedUv = uvRegion.xy + v.uv * uvRegion.zw;
                return image.SampleLevel(texSampler,
                    clamp(requestedUv, uvClamp.xy, uvClamp.zw), 0);
            })";
        // Load before allocating compiler-owned ID3DBlob interfaces.
        // The COM blob vtables live in d3dcompiler_47.dll: their Release()
        // must run BEFORE FreeLibrary, including failure/early-return paths.
        // Earlier the module guard was declared after the blobs, which
        // unloaded the DLL first and crashed Win32 WARP at first StretchRect.
        HMODULE compiler = LoadLibraryW(L"d3dcompiler_47.dll");
        if (!compiler) return false;
        struct ScopedCompilerModule {
            HMODULE handle{};
            ~ScopedCompilerModule() noexcept { if (handle) FreeLibrary(handle); }
        } compilerLifetime{compiler};
        Microsoft::WRL::ComPtr<ID3DBlob> vc, pc;
        Microsoft::WRL::ComPtr<ID3D11VertexShader> v;
        Microsoft::WRL::ComPtr<ID3D11PixelShader> p;
        Microsoft::WRL::ComPtr<ID3D11SamplerState> s0, s1;
        Microsoft::WRL::ComPtr<ID3D11Buffer> cb;
        const auto compile = reinterpret_cast<decltype(&D3DCompile)>(
            GetProcAddress(compiler, "D3DCompile"));
        if (!compile) return false;
        if (FAILED(compile(shader, sizeof(shader)-1u, nullptr,
                nullptr, nullptr, "VS", "vs_4_0", 0u, 0u,
                vc.GetAddressOf(), nullptr)) ||
            FAILED(compile(shader, sizeof(shader)-1u, nullptr,
                nullptr, nullptr, "PS", "ps_4_0", 0u, 0u,
                pc.GetAddressOf(), nullptr)) ||
            FAILED(device->CreateVertexShader(vc->GetBufferPointer(),
                vc->GetBufferSize(), nullptr, v.GetAddressOf())) ||
            FAILED(device->CreatePixelShader(pc->GetBufferPointer(),
                pc->GetBufferSize(), nullptr, p.GetAddressOf())))
            return false;
        D3D11_SAMPLER_DESC sample{};
        sample.AddressU = sample.AddressV = sample.AddressW =
            D3D11_TEXTURE_ADDRESS_CLAMP;
        sample.MaxLOD = D3D11_FLOAT32_MAX;
        sample.Filter = D3D11_FILTER_MIN_MAG_MIP_POINT;
        if (FAILED(device->CreateSamplerState(&sample, s0.GetAddressOf())))
            return false;
        sample.Filter = D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;
        if (FAILED(device->CreateSamplerState(&sample, s1.GetAddressOf())))
            return false;
        D3D11_BUFFER_DESC desc{};
        desc.ByteWidth = sizeof(float) * 8u;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        if (FAILED(device->CreateBuffer(&desc, nullptr, cb.GetAddressOf())))
            return false;
        cachedDevice = device;
        vs = std::move(v);
        ps = std::move(p);
        point = std::move(s0);
        linear = std::move(s1);
        constants = std::move(cb);
    }

    // Extract only the selected camera slice of bindless GPU game output
    // into an SRV; never CPU Map or recycle the other native eye's pixels.
    // Shader-readable single-slice sources can be sampled in place. A
    // TEXTURE2DARRAY source is not compatible with the postpass Texture2D
    // pixel shader: extract only the selected game camera into a one-slice
    // mip-zero GPU SRV. The shader always samples LOD 0; copying all atlas
    // mips or the other eye would be incorrect and needlessly expensive.
    const bool directSingleSlice =
        transfer == NativeGameStretchSourceTransfer::DirectSample &&
        sd.ArraySize == 1u && sourceMipSlice == 0u;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> sampled;
    if (directSingleSlice)
        sampled = source;
    else {
        D3D11_TEXTURE2D_DESC desc = sd;
        desc.Width = mipWidth;
        desc.Height = mipHeight;
        desc.MipLevels = 1u;
        desc.ArraySize = 1u;
        desc.SampleDesc.Count = 1u;
        desc.SampleDesc.Quality = 0u;
        desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        desc.MiscFlags = 0u;
        const NativeGamePostpassScratchKey key{
            desc.Width, desc.Height,
            static_cast<std::uint32_t>(desc.Format), desc.BindFlags};
        // Reuse the same GPU-resident temporary across ordered camera
        // Copy/Resolve -> shader Draw sequences; a full mip chain or array
        // is reduced to a one-slice mip-zero eye source on every replay.
        // This mutex is held through the Draw, not just the allocation.
        if (!sampledScratch ||
            !native_game_postpass_scratch_matches(sampledScratchKey, key)) {
            Microsoft::WRL::ComPtr<ID3D11Texture2D> fresh;
            if (FAILED(device->CreateTexture2D(
                    &desc, nullptr, fresh.GetAddressOf())) || !fresh)
                return false;
            sampledScratch = std::move(fresh);
            sampledScratchKey = key;
        }
        sampled = sampledScratch;
    }
    Microsoft::WRL::ComPtr<ID3D11ShaderResourceView> srv;
    if (FAILED(device->CreateShaderResourceView(
            sampled.Get(), nullptr, srv.GetAddressOf()))) return false;
    // Context-state swap snapshots ALL graphics bindings: MRT0..7, DSV,
    // shaders, class instances, IA buffers, samplers, blend, raster and Z.
    // The original D3D9 fallback and the next native eye draw are untouched.
    // Reuse the proven eye-Draw pipeline owner. It captures OM0..7/DSV,
    // viewport/scissor, VS/PS/GS/HS/DS, IA and shader-bound resources.
    // A separate context-state swap can retain an invalid game source COM
    // binding across native eye pass teardown; restore synchronously here.
    ScopedNativeGameEyeOutput restore(context_, targetWidth_, targetHeight_);
    if (!restore.valid()) return false;
    ScopedNativePostpassOutputs outputs(context_);
    context_->OMSetRenderTargets(0u, nullptr, nullptr);
    if (sampled.Get() != source) {
        // Subresource 0 of EACH array slice is the camera's full-sized
        // color. This also handles multisampled color and multi-mip
        // RTV-only postpasses without ever copying unrelated eye pixels.
        const UINT sourceSubresource =
            D3D11CalcSubresource(sourceMipSlice, sourceArraySlice,
                                 sd.MipLevels);
        if (transfer == NativeGameStretchSourceTransfer::ResolveToSampled)
            context_->ResolveSubresource(
                sampled.Get(), 0u, source, sourceSubresource, sd.Format);
        else
            context_->CopySubresourceRegion(
                sampled.Get(), 0u, 0u, 0u, 0u,
                source, sourceSubresource, nullptr);
    }
    ID3D11RenderTargetView* target = eyeTarget_;
    context_->OMSetRenderTargets(1u, &target, nullptr);
    // A game StretchRect can begin offscreen during menu/car transitions.
    // Clip the actual eye viewport, not just its origin; the adjusted
    // constants preserve the source pixel each surviving output pixel maps to.
    const D3D11_VIEWPORT viewport{
        float(clipped.left), float(clipped.top),
        float(clipped.right - clipped.left),
        float(clipped.bottom - clipped.top), 0.f, 1.f};
    context_->RSSetViewports(1u, &viewport);
    context_->RSSetState(nullptr);
    context_->OMSetBlendState(nullptr, nullptr, 0xffffffffu);
    context_->OMSetDepthStencilState(nullptr, 0u);
    // The shader's bilinear footprint must stay within the original
    // game crop, including 1-texel menu glyphs and adjacent car atlas tiles.
    context_->UpdateSubresource(
        constants.Get(), 0u, nullptr, clipped.uv.constants.data(), 0u, 0u);
    ID3D11Buffer* cb = constants.Get();
    ID3D11ShaderResourceView* view = srv.Get();
    ID3D11SamplerState* sample = linearFilter ? linear.Get() : point.Get();
    context_->IASetInputLayout(nullptr);
    context_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context_->VSSetShader(vs.Get(), nullptr, 0u);
    context_->PSSetShader(ps.Get(), nullptr, 0u);
    context_->GSSetShader(nullptr, nullptr, 0u);
    context_->HSSetShader(nullptr, nullptr, 0u);
    context_->DSSetShader(nullptr, nullptr, 0u);
    context_->PSSetConstantBuffers(0u, 1u, &cb);
    context_->PSSetShaderResources(0u, 1u, &view);
    context_->PSSetSamplers(0u, 1u, &sample);
    context_->Draw(3u, 0u); // GPU postpass, not game geometry evidence
    return true;
}

void NativeGameStereoSubmission::release_local() noexcept {
    for (auto& eye : eyes_) eye.Reset();
    context_.Reset();
    eyeViews_[0] = eyeViews_[1] = 0;
    eyeArraySlices_[0] = eyeArraySlices_[1] = 0u;
    eyeMipSlices_[0] = eyeMipSlices_[1] = 0u;
    frameId_ = poseSequence_ = 0;
    slot_ = OutRunVR::RenderFrameRingSize;
    state_ = State::Idle;
}

bool NativeGameStereoSubmission::begin(
    ID3D11DeviceContext* context, std::uint64_t frameId,
    std::uint32_t sourcePoseSequence,
    const OutRunVR::Core::FrameAck* ack) noexcept
{
    if (active() || !ring_.activation_ready() || !context ||
        context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE ||
        !frameId || frameId > (std::numeric_limits<std::uint32_t>::max)() ||
        !sourcePoseSequence)
        return false;
    std::uint32_t acquired = OutRunVR::RenderFrameRingSize;
    if (!ring_.try_acquire_slot(context, frameId, ack, acquired))
        return false;
    context_ = context;
    frameId_ = frameId;
    poseSequence_ = sourcePoseSequence;
    slot_ = acquired;
    state_ = State::Acquired;
    return true;
}

bool NativeGameStereoSubmission::source_is_live(
    ID3D11Texture2D* source, UINT arraySlice, UINT mipSlice) const noexcept
{
    if (!context_ || !source) return false;
    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice, sourceDevice;
    context_->GetDevice(contextDevice.GetAddressOf());
    source->GetDevice(sourceDevice.GetAddressOf());
    if (!contextDevice || contextDevice.Get() != sourceDevice.Get())
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    source->GetDesc(&desc);
    // Preserve selected game camera mip geometry across the native stereo
    // producer and OpenXR shared ring; a larger atlas mip0 is not the eye.
    const auto mip = native_game_postpass_mip_extent(
        desc.Width, desc.Height, desc.MipLevels, mipSlice,
        desc.ArraySize, arraySlice, desc.SampleDesc.Count);
    return mip.valid && mip.width == ring_.width() &&
        mip.height == ring_.height() &&
        desc.Format == ring_.format() &&
        (desc.SampleDesc.Count == 1u || desc.MipLevels == 1u) &&
        desc.Usage == D3D11_USAGE_DEFAULT && desc.CPUAccessFlags == 0u &&
        (native_game_eye_local_render_target_admitted(
            desc.BindFlags, desc.MiscFlags, D3D11_BIND_RENDER_TARGET,
            D3D11_RESOURCE_MISC_SHARED |
            D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
            D3D11_RESOURCE_MISC_SHARED_NTHANDLE) ||
         native_game_eye_gpu_copy_only_source_admitted(
            desc.BindFlags, desc.MiscFlags, desc.SampleDesc.Count,
            D3D11_RESOURCE_MISC_SHARED |
            D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
            D3D11_RESOURCE_MISC_SHARED_NTHANDLE) ||
         native_game_eye_gpu_shader_postpass_source_admitted(
             desc.BindFlags, desc.MiscFlags, desc.SampleDesc.Count,
             D3D11_BIND_SHADER_RESOURCE,
             D3D11_RESOURCE_MISC_SHARED |
             D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
             D3D11_RESOURCE_MISC_SHARED_NTHANDLE) ||
         native_game_eye_gpu_compute_source_admitted(
            desc.BindFlags, desc.MiscFlags, desc.SampleDesc.Count,
            D3D11_BIND_UNORDERED_ACCESS, D3D11_BIND_RENDER_TARGET,
            D3D11_BIND_DEPTH_STENCIL,
            D3D11_RESOURCE_MISC_SHARED |
            D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
            D3D11_RESOURCE_MISC_SHARED_NTHANDLE));
}

bool NativeGameStereoSubmission::capture_eye(
    std::uint32_t eyeIndex, ID3D11Texture2D* nativeColor,
    std::uint64_t nativeDrawCount, std::uint64_t eyeViewSignature,
    std::uint32_t sourcePoseSequence, UINT sourceArraySlice,
    UINT sourceMipSlice) noexcept
{
    if (state_ != State::Acquired || eyeIndex >= 2u ||
        eyes_[eyeIndex] || !nativeDrawCount || !eyeViewSignature ||
        sourcePoseSequence != poseSequence_ ||
        !source_is_live(nativeColor, sourceArraySlice, sourceMipSlice))
        return false;
    eyes_[eyeIndex] = nativeColor;
    eyeViews_[eyeIndex] = eyeViewSignature;
    eyeArraySlices_[eyeIndex] = sourceArraySlice;
    eyeMipSlices_[eyeIndex] = sourceMipSlice;
    return true;
}

bool NativeGameStereoSubmission::render_game_eye_passes(
    NativeGameEyePass pass, void* user,
    std::uint32_t sourcePoseSequence,
    const NativeGameEyeColorSeed* fullTargetClear,
    const NativeGameEyeRasterState* gameRaster,
    const NativeGameEyePartialTargetClear* partialTargetClear) noexcept
{
    if (state_ != State::Acquired || !context_ || !pass ||
        eyes_[0] || eyes_[1] || sourcePoseSequence == 0u ||
        sourcePoseSequence != poseSequence_)
        return false;

    // Source-supplied eye camera rectangles must be safe before any GPU
    // recording. Invalid game input remains cancellable and the D3D9 game
    // frame stays authoritative rather than submitting a partial XR eye.
    if (gameRaster) {
        for (std::uint32_t eye = 0; eye < 2u; ++eye) {
            const auto& v = gameRaster->viewport[eye];
            const auto& r = gameRaster->scissor[eye];
            const float z = gameRaster->depthClear[eye];
            if (!std::isfinite(v.TopLeftX) || !std::isfinite(v.TopLeftY) ||
                !std::isfinite(v.Width) || !std::isfinite(v.Height) ||
                !std::isfinite(v.MinDepth) || !std::isfinite(v.MaxDepth) ||
                v.TopLeftX < 0.0f || v.TopLeftY < 0.0f ||
                v.Width <= 0.0f || v.Height <= 0.0f ||
                v.TopLeftX + v.Width > static_cast<float>(ring_.width()) ||
                v.TopLeftY + v.Height > static_cast<float>(ring_.height()) ||
                v.MinDepth < 0.0f || v.MinDepth > 1.0f ||
                v.MaxDepth < 0.0f || v.MaxDepth > 1.0f ||
                r.left < 0 || r.top < 0 || r.right <= r.left ||
                r.bottom <= r.top ||
                r.right > static_cast<LONG>(ring_.width()) ||
                r.bottom > static_cast<LONG>(ring_.height()) ||
                !std::isfinite(z) || z < 0.0f || z > 1.0f)
                return false;
        }
    }

    // Partial TARGET clears need the D3D11.1 rectangle-aware ClearView.
    // Validate BOTH eyes and obtain the interface before any GPU write. No
    // silent whole-RT fallback is allowed for an unsupported game Clear.
    Microsoft::WRL::ComPtr<ID3D11DeviceContext1> rectClearContext;
    if (partialTargetClear) {
        bool needsClearView = false;
        bool needsPostpassShader = false;
        for (std::uint32_t eye = 0u; eye < 2u; ++eye) {
            const std::uint32_t count = partialTargetClear->count[eye];
            if (count > NativeGameEyePartialTargetClear::kMaxRectsPerEye)
                return false;
            for (std::uint32_t i = 0u; i < count; ++i) {
                const auto& event = partialTargetClear->entries[eye][i];
                if (i != 0u &&
                    event.afterDrawOrdinal <
                        partialTargetClear->entries[eye][i - 1u].afterDrawOrdinal)
                    return false;
                if (event.kind ==
                    NativeGameEyePartialTargetClear::Kind::TargetRect) {
                    const auto& rect = event.rect;
                    if (rect.left < 0 || rect.top < 0 ||
                        rect.right <= rect.left || rect.bottom <= rect.top ||
                        rect.right > static_cast<LONG>(ring_.width()) ||
                        rect.bottom > static_cast<LONG>(ring_.height()))
                        return false;
                    needsClearView |= !live_game_stereo::full_eye_target_rect(
                        rect.left, rect.top, rect.right, rect.bottom,
                        ring_.width(), ring_.height());
                } else if (event.kind ==
                           NativeGameEyePartialTargetClear::Kind::FullDepthStencil) {
                    // Empty RECT or an explicit entire-eye RECT maps
                    // to base D3D11.0 ClearDepthStencilView. Only cropped
                    // source regions need the bounded depth/stencil raster.
                    // Preflight the same route for BOTH eyes before commands.
                    const auto& rect = event.rect;
                    const bool hasRect = rect.left || rect.top ||
                        rect.right || rect.bottom;
                    const auto route = live_game_stereo::depth_clear_route(
                        hasRect, rect.left, rect.top, rect.right, rect.bottom,
                        ring_.width(), ring_.height());
                    if ((!event.clearDepth && !event.clearStencil) ||
                        (event.clearDepth &&
                         (!std::isfinite(event.depth) ||
                          event.depth < 0.0f || event.depth > 1.0f)) ||
                        route == live_game_stereo::NativeDepthClearRoute::Reject)
                        return false;
                    // A cropped Z/stencil Clear always rasterizes on D3D11,
                    // including 11.1: ClearView is a color operation here.
                    // Verify d3dcompiler before recording eye L, not after
                    // partially mutating the stereo pair during eye replay.
                    if (route == live_game_stereo::NativeDepthClearRoute::PartialRaster)
                        needsPostpassShader = true;
                } else if (event.kind ==
                               NativeGameEyePartialTargetClear::Kind::SourceCopy ||
                           event.kind ==
                               NativeGameEyePartialTargetClear::Kind::SourceStretch) {
                    // Reject malformed/foreign GPU intermediates in BOTH eyes
                    // before the first eye can enqueue any command. The
                    // encoder performs the full format/alias admission at use.
                    if (!event.source) return false;
                    Microsoft::WRL::ComPtr<ID3D11Device> producer, sourceOwner;
                    context_->GetDevice(producer.GetAddressOf());
                    event.source->GetDevice(sourceOwner.GetAddressOf());
                    D3D11_TEXTURE2D_DESC desc{};
                    event.source->GetDesc(&desc);
                    const auto& b = event.sourceBox;
                    const auto sourceMip = native_game_postpass_source_box(
                        desc.Width, desc.Height, desc.MipLevels,
                        event.sourceMipSlice, desc.ArraySize,
                        event.sourceArraySlice, desc.SampleDesc.Count,
                        b.left, b.top, b.right, b.bottom);
                    constexpr UINT sharedMask =
                        D3D11_RESOURCE_MISC_SHARED |
                        D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
                        D3D11_RESOURCE_MISC_SHARED_NTHANDLE;
                    if (!producer || producer.Get() != sourceOwner.Get() ||
                        desc.Usage != D3D11_USAGE_DEFAULT ||
                        desc.CPUAccessFlags != 0u ||
                        (desc.MiscFlags & sharedMask) != 0u ||
                        !sourceMip.valid ||
                        !native_game_postpass_gpu_source(
                            desc.BindFlags, desc.SampleDesc.Count,
                            D3D11_BIND_RENDER_TARGET,
                            D3D11_BIND_SHADER_RESOURCE,
                            D3D11_BIND_UNORDERED_ACCESS) ||
                        b.front != 0u || b.back != 1u)
                        return false;
                    if (event.kind ==
                        NativeGameEyePartialTargetClear::Kind::SourceCopy) {
                        // Validate source format, GPU sample mode and conversion
                        // for BOTH cameras before recording the first eye.
                        // Otherwise eye L can write a live XR ring slot before
                        // a late eye R conversion/resolve is found unsupported.
                        if (desc.SampleDesc.Count == 0u ||
                            desc.SampleDesc.Count > 32u ||
                            (desc.SampleDesc.Count == 1u &&
                             desc.SampleDesc.Quality != 0u) ||
                            (desc.SampleDesc.Count > 1u &&
                             (desc.MipLevels != 1u ||
                              (desc.BindFlags &
                               D3D11_BIND_RENDER_TARGET) == 0u)))
                            return false;
                        if (desc.Format != ring_.format()) {
                            needsPostpassShader = true;
                            // Unscaled D3D9 StretchRect permits format
                            // conversion; the native encoder implements it
                            // via the same point-sampled GPU shader as Stretch.
                            UINT sourceSupport = 0u, eyeSupport = 0u;
                            if (FAILED(producer->CheckFormatSupport(
                                    desc.Format, &sourceSupport)) ||
                                FAILED(producer->CheckFormatSupport(
                                    ring_.format(), &eyeSupport)) ||
                                native_game_stretch_source_transfer(
                                    desc.MipLevels, desc.SampleDesc.Count,
                                    desc.SampleDesc.Quality,
                                    (desc.BindFlags &
                                     D3D11_BIND_RENDER_TARGET) != 0u,
                                    (desc.BindFlags &
                                     D3D11_BIND_SHADER_RESOURCE) != 0u,
                                    (sourceSupport &
                                     D3D11_FORMAT_SUPPORT_SHADER_SAMPLE) != 0u,
                                    (eyeSupport &
                                     D3D11_FORMAT_SUPPORT_RENDER_TARGET) != 0u,
                                    (sourceSupport &
                                     D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) != 0u,
                                    (desc.BindFlags == 0u ||
                                     (desc.BindFlags & D3D11_BIND_UNORDERED_ACCESS) != 0u) &&
                                    desc.SampleDesc.Count == 1u) ==
                                    NativeGameStretchSourceTransfer::Reject)
                                return false;
                        } else if (desc.SampleDesc.Count > 1u) {
                            UINT support = 0u;
                            if (FAILED(producer->CheckFormatSupport(
                                    desc.Format, &support)) ||
                                (support &
                                 D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) == 0u)
                                return false;
                        }
                        // Preflight both eyes with the exact same GPU Copy
                        // clipping as the encoder. A fully offscreen copy
                        // remains invalid before any eye queues GPU work.
                        if (!native_game_copy_clipped_region(
                                sourceMip.width, sourceMip.height,
                                b.left, b.top, b.right, b.bottom,
                                ring_.width(), ring_.height(),
                                event.destX, event.destY).valid)
                            return false;
                    } else {
                        needsPostpassShader = true;
                        const auto& d = event.destination;
                        // D3D9 game RTs may be RTV-only. The native postpass
                        // copies mip zero to an SRV; replay admission must
                        // also permit supported CopyToSampled/ResolveToSampled.
                        UINT sourceSupport = 0u, eyeSupport = 0u;
                        if (FAILED(producer->CheckFormatSupport(
                                desc.Format, &sourceSupport)) ||
                            FAILED(producer->CheckFormatSupport(
                                ring_.format(), &eyeSupport)) ||
                            native_game_stretch_source_transfer(
                                desc.MipLevels, desc.SampleDesc.Count,
                                desc.SampleDesc.Quality,
                                (desc.BindFlags & D3D11_BIND_RENDER_TARGET) != 0u,
                                (desc.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0u,
                                (sourceSupport &
                                 D3D11_FORMAT_SUPPORT_SHADER_SAMPLE) != 0u,
                                (eyeSupport &
                                 D3D11_FORMAT_SUPPORT_RENDER_TARGET) != 0u,
                                (sourceSupport &
                                 D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE) != 0u,
                                (desc.BindFlags == 0u ||
                                 (desc.BindFlags & D3D11_BIND_UNORDERED_ACCESS) != 0u) &&
                                desc.SampleDesc.Count == 1u) ==
                                NativeGameStretchSourceTransfer::Reject ||
                            !native_game_stretch_clipped_region(
                                sourceMip.width, sourceMip.height,
                                b.left, b.top, b.right, b.bottom,
                                ring_.width(), ring_.height(),
                                d.left, d.top, d.right, d.bottom).valid)
                            return false;
                    }
                } else {
                    return false;
                }
            }
        }
        if (needsClearView &&
            FAILED(context_->QueryInterface(
                IID_PPV_ARGS(rectClearContext.GetAddressOf())))) {
            // D3D11.0 cannot ClearView partial rectangles. The real cropped
            // game TARGET replay uses a bounded GPU color raster instead.
            // Check both eye formats and shader compiler availability before
            // either eye starts writing. Fail closed on missing dependencies.
            // Check BOTH typed ring RTVs with the same supported D3D11.0
            // GPU color raster contract before the first eye queues commands.
            // A game camera may store pixels in a typeless texture; only its
            // typed view format defines a legal pixel shader output.
            for (std::uint32_t eye = 0u; eye < 2u; ++eye) {
                if (!native_game_partial_color_shader_rtv(
                        context_.Get(), ring_.rtv(slot_, eye)))
                    return false;
            }
            needsPostpassShader = true;
        }
        // Actual game Copy format conversion and scaled Stretch replay
        // also compile a native GPU shader. Preflight before either eye
        // queues commands to avoid a partial L-eye mutation when R fails.
        if (needsPostpassShader) {
            HMODULE compiler = LoadLibraryW(L"d3dcompiler_47.dll");
            if (!compiler) return false;
            const bool ready = GetProcAddress(compiler, "D3DCompile") != nullptr;
            FreeLibrary(compiler);
            if (!ready) return false;
        }
    }

    // The shared-eye ring owns one independent Z/stencil pair PER SLOT,
    // reused only after the prior frame's GPU fence/consumer ACK releases
    // that slot. ClearDepthStencilView below initializes BOTH planes on
    // every frame; no stale menu/car/race depth may bleed across frames.
    // Allocate before the first GPU command, preserving DX9Ex on failure.
    ID3D11DepthStencilView* depthViews[2]{};
    if (!ring_.acquire_depth_pair(
            context_.Get(), slot_, frameId_, depthViews))
        return false;
    struct EyePassDispatch {
        NativeGameEyePass callback{};
        void* user{};
        std::uint32_t poseSequence{};
        NativeGameEyeDrawEvidence eye[2]{};
        std::uint32_t width{}, height{};
        ID3D11DepthStencilView* depth[2]{};
        const NativeGameEyeColorSeed* fullTargetClear{};
        const NativeGameEyeRasterState* gameRaster{};
        const NativeGameEyePartialTargetClear* partialTargetClear{};
    } dispatch{pass, user, sourcePoseSequence, {},
               ring_.width(), ring_.height(),
               {depthViews[0], depthViews[1]},
               fullTargetClear, gameRaster, partialTargetClear};

    // The ring verifies the immediate context and reserves the exact frame
    // before entering this recorder. It marks GPU work as queued first:
    // partial render failures require hard retirement, never slot recycling.
    const auto record = [](void* opaque, ID3D11DeviceContext* ctx,
                           ID3D11RenderTargetView* left,
                           ID3D11RenderTargetView* right) noexcept -> bool {
        auto& invocation = *static_cast<EyePassDispatch*>(opaque);
        ScopedNativeGameEyeOutput output(ctx, invocation.width, invocation.height);
        ID3D11RenderTargetView* targets[2]{left, right};
        for (std::uint32_t eyeIndex = 0u; eyeIndex < 2u; ++eyeIndex) {
            if (!output.bind(targets[eyeIndex],
                             invocation.depth[eyeIndex],
                             invocation.gameRaster, eyeIndex))
                return false;
            // The game's verified full-RT Clear is part of scene replay, not
            // optional decoration. Clear this eye's own target before its
            // native Draw/DrawIndexed; otherwise a reused ACK'd ring slot
            // exposes stale menu/car/race pixels where the next draw has holes.
            // Do not synthesize a color seed when the game cleared only a RECT.
            if (invocation.fullTargetClear) {
                const std::uint32_t argb =
                    invocation.fullTargetClear->argb[eyeIndex];
                constexpr float normalize = 1.0f / 255.0f;
                const float rgba[4]{
                    static_cast<float>((argb >> 16) & 0xffu) * normalize,
                    static_cast<float>((argb >> 8) & 0xffu) * normalize,
                    static_cast<float>(argb & 0xffu) * normalize,
                    static_cast<float>((argb >> 24) & 0xffu) * normalize};
                ctx->ClearRenderTargetView(targets[eyeIndex], rgba);
            }
            // Replay the captured game Clear timeline inside Draw/DrawIndexed,
            // not as pre-draw seeds which overwrite out-of-order scene pixels.
            // Native D3D11 depth/stencil are private per frame AND per eye;
            // initialize both planes before the game's Draw/DrawIndexed
            // replay. The renderer may then perform the source's own clears.
            ctx->ClearDepthStencilView(
                invocation.depth[eyeIndex],
                D3D11_CLEAR_DEPTH | D3D11_CLEAR_STENCIL,
                invocation.gameRaster
                    ? invocation.gameRaster->depthClear[eyeIndex] : 1.0f,
                invocation.gameRaster
                    ? invocation.gameRaster->stencilClear[eyeIndex] : 0u);
            NativeGameEyeDrawEncoder encoder(
                ctx, targets[eyeIndex], invocation.depth[eyeIndex],
                invocation.width, invocation.height,
                invocation.fullTargetClear != nullptr);
            encoder.set_source_clear_timeline(
                invocation.partialTargetClear, eyeIndex);
            if (!invocation.callback(invocation.user, ctx,
                                     targets[eyeIndex], eyeIndex,
                                     invocation.eye[eyeIndex], encoder))
                return false;
            // The callback is finished, but source-authored Clears and GPU
            // postpasses can be scheduled at the final Draw ordinal. Strip
            // any callback predicate/SO binding before finishing that tail:
            // e.g. right-eye menu HUD Clear at draw ordinal six must render
            // even if a host postpass left an unready occlusion predicate.
            // ScopedNativeGameEyeOutput restores caller state on every exit.
            // The authentic last game Draw may finish on a menu/vehicle
            // intermediate RTV with an off-eye viewport. Chronological
            // source Clears/Copy/Stretch at that final Draw ordinal still
            // target the game's OWN full-resolution stereo eye. Rebind the
            // ring RTV/DSV and original camera raster before replaying the
            // tail; otherwise a legitimate offscreen last pass drops both
            // native XR eyes or silently clips the final HUD composite.
            // Restoring the recorded IA/shader state here is safe: the game
            // callback has already issued all source geometry, and the
            // remaining commands carry their own actual GPU source resources.
            // Failure quarantines prior GPU writes through render_eye_pair.
            if (!output.bind(targets[eyeIndex],
                             invocation.depth[eyeIndex],
                             invocation.gameRaster, eyeIndex))
                return false;
            output.prepare_source_timeline_tail();
            if (!encoder.finish_source_clear_timeline())
                return false;
            const auto& evidence = invocation.eye[eyeIndex];
            if (!live_game_stereo::authored_visible_eye_frame_ready(
                    encoder.draw_count(), encoder.color_draw_count(),
                    encoder.authored_color_postpass_count(),
                    encoder.authored_full_color_clear_count(),
                    encoder.last_full_clear_draw_ordinal(),
                    encoder.unpredicated_game_draw_count(),
                    encoder.unpredicated_at_last_full_clear(),
                    encoder.unpredicated_eye_draw_count(),
                    encoder.unpredicated_eye_at_last_full_clear()) ||
                evidence.drawCount != encoder.draw_count() ||
                !evidence.viewSignature ||
                evidence.sourcePoseSequence != invocation.poseSequence ||
                (eyeIndex == 1u &&
                 evidence.viewSignature == invocation.eye[0].viewSignature))
                return false;
        }
        return true;
    };
    if (!ring_.render_eye_pair(context_.Get(), slot_, frameId_,
                               record, &dispatch))
        return false;

    eyeViews_[0] = dispatch.eye[0].viewSignature;
    eyeViews_[1] = dispatch.eye[1].viewSignature;
    state_ = State::GpuPending;
    return true;
}

bool NativeGameStereoSubmission::render_direct_eyes(
    NativeSharedEyeRing::NativeEyeDrawRecorder recorder, void* user,
    std::uint64_t leftDrawCount, std::uint64_t rightDrawCount,
    std::uint64_t leftViewSignature, std::uint64_t rightViewSignature,
    std::uint32_t sourcePoseSequence) noexcept
{
    // A direct GPU producer owns two real game-camera draws, not a mono
    // texture copied to both OpenXR eyes. Reject before entering a recorder
    // that may have GPU side effects; keep the original D3D9 path valid.
    if (state_ != State::Acquired || !context_ || !recorder ||
        eyes_[0] || eyes_[1] || !leftDrawCount || !rightDrawCount ||
        !leftViewSignature || !rightViewSignature ||
        leftViewSignature == rightViewSignature ||
        sourcePoseSequence == 0u || sourcePoseSequence != poseSequence_)
        return false;
    // render_eye_pair owns the same exact frame/slot identity as the
    // copy-based submission and arms one EVENT after both GPU eye writes.
    // If the callback fails after recording commands, the ring remains
    // faulted and neither cancellation nor new-frame reuse is permitted.
    if (!ring_.render_eye_pair(context_.Get(), slot_, frameId_, recorder, user))
        return false;
    eyeViews_[0] = leftViewSignature;
    eyeViews_[1] = rightViewSignature;
    state_ = State::GpuPending;
    return true;
}

bool NativeGameStereoSubmission::submit() noexcept
{
    if (state_ != State::Acquired || !eyes_[0] || !eyes_[1] ||
        eyeViews_[0] == 0u || eyeViews_[1] == 0u ||
        eyeViews_[0] == eyeViews_[1] ||
        !source_is_live(eyes_[0].Get(), eyeArraySlices_[0], eyeMipSlices_[0]) ||
        !source_is_live(eyes_[1].Get(), eyeArraySlices_[1], eyeMipSlices_[1]))
        return false;

    // submit_eye_pair itself checks canonical COM identities, every ring-owned
    // allocation, both source descriptors and MSAA resolve compatibility.
    // It queues BOTH GPU transfers before one producer EVENT. On a partial
    // command/fence failure the ring quarantines its allocation.
    if (!ring_.submit_eye_pair(context_.Get(), slot_, frameId_,
                               eyes_[0].Get(), eyes_[1].Get(),
                               eyeArraySlices_[0], eyeArraySlices_[1],
                               eyeMipSlices_[0], eyeMipSlices_[1]))
        return false;
    eyes_[0].Reset();
    eyes_[1].Reset();
    state_ = State::GpuPending;
    return true;
}

bool NativeGameStereoSubmission::try_publish(
    NativeGameStereoPublishedFrame& published) noexcept
{
    published = {};
    if (state_ != State::GpuPending ||
        !ring_.publish_if_fence_complete(context_.Get(), slot_, frameId_))
        return false;

    NativeSharedEyePublication candidate{};
    if (!ring_.snapshot_published_frame(slot_, frameId_, candidate) ||
        !ring_.validate_publication_snapshot(candidate))
        return false;
    published.gpu = candidate;
    published.sourcePoseSequence = poseSequence_;
    published.eyeViewSignature[0] = eyeViews_[0];
    published.eyeViewSignature[1] = eyeViews_[1];
    release_local();
    return true;
}


bool NativeGameStereoSubmission::attach_host_frame(
    const NativeGameStereoPublishedFrame& source,
    OutRunVR::SharedRenderFrameState& gameFrame) const noexcept
{
    const auto& published = source.gpu;
    constexpr std::uint32_t completeFlags =
        OutRunVR::RenderFrameStereoComplete |
        OutRunVR::RenderFrameWorldStereo |
        OutRunVR::RenderFrameDrawDuplicated |
        OutRunVR::RenderFrameEffectivePoseValid;
    const auto left = reinterpret_cast<std::uintptr_t>(published.left_handle);
    const auto right = reinterpret_cast<std::uintptr_t>(published.right_handle);
    // The game DLL and Frame.v1 shared-handle words are 32-bit. Reject a
    // truncated Win64-style handle instead of shipping an invalid OpenXR eye.
    if (!ring_.validate_publication_snapshot(published) ||
        !source.sourcePoseSequence ||
        !source.eyeViewSignature[0] || !source.eyeViewSignature[1] ||
        source.eyeViewSignature[0] == source.eyeViewSignature[1] ||
        !left || !right || left == right ||
        left > (std::numeric_limits<std::uint32_t>::max)() ||
        right > (std::numeric_limits<std::uint32_t>::max)() ||
        !published.width || !published.height ||
        published.frame_id == 0u ||
        published.frame_id > (std::numeric_limits<std::uint32_t>::max)() ||
        published.slot >= OutRunVR::RenderFrameRingSize ||
        gameFrame.clientPid != published.identity.producerPid ||
        gameFrame.reserved[OutRunVR::RenderFrameRunGenerationIndex] !=
            published.identity.runGeneration ||
        gameFrame.frameId != published.frame_id ||
        gameFrame.sourcePoseSequence != source.sourcePoseSequence ||
        gameFrame.state != OutRunVR::StereoSbsActive ||
        gameFrame.presentQpc <= 0 ||
        (gameFrame.flags & completeFlags) != completeFlags ||
        (gameFrame.flags & OutRunVR::RenderFramePresentInFlight) != 0u)
        return false;

    // Do not forge any stereo completion, render-state or camera-pose flags.
    // They must already come from the real game Draw/DrawIndexed producer.
    // Match the host's direct eye texture dimensions, which can differ from
    // the 2D desktop backbuffer while in headset-native resolution.
    gameFrame.backbufferWidth = published.width;
    gameFrame.backbufferHeight = published.height;
    gameFrame.reserved[OutRunVR::RenderFrameDirectLeftHandleIndex] =
        static_cast<std::uint32_t>(left);
    gameFrame.reserved[OutRunVR::RenderFrameDirectRightHandleIndex] =
        static_cast<std::uint32_t>(right);
    gameFrame.reserved[OutRunVR::RenderFrameDirectWidthIndex] = published.width;
    gameFrame.reserved[OutRunVR::RenderFrameDirectHeightIndex] = published.height;
    gameFrame.reserved[OutRunVR::RenderFrameDirectFormatIndex] =
        static_cast<std::uint32_t>(published.format);
    gameFrame.reserved[OutRunVR::RenderFrameDirectGenerationIndex] =
        published.identity.generation;
    gameFrame.reserved[OutRunVR::RenderFrameDirectSlotIndex] = published.slot;
    gameFrame.flags |= OutRunVR::RenderFrameDirectGpuTransport;
    return true;
}

bool NativeGameStereoSubmission::cancel() noexcept
{
    if (state_ == State::Idle) return true;
    // If GPU commands may have been queued, cancellation is unsafe even if
    // submission failed before a fence was successfully armed.
    if (state_ != State::Acquired ||
        !ring_.cancel_acquired_slot(slot_, frameId_))
        return false;
    release_local();
    return true;
}

} // namespace outrun::vr::dx11
