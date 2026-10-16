#include "native_game_stereo_submission.hpp"
#include "native_game_eye_pair_sources.hpp"
#include <limits>
#include <cmath>

namespace outrun::vr::dx11 {

// Only game Draws addressed to THIS eye's real RTV+DSV are source evidence.
// A callback may unbind OM to render a menu texture; counting that Draw
// would publish an unchanged/stale XR eye although the GPU issued commands.
bool NativeGameEyeDrawEncoder::eye_output_bound() const noexcept {
    if (!context_ || !eyeTarget_ || !eyeDepth_) return false;
    ID3D11RenderTargetView* actualTarget = nullptr;
    ID3D11DepthStencilView* actualDepth = nullptr;
    context_->OMGetRenderTargets(1u, &actualTarget, &actualDepth);
    const bool matches = actualTarget == eyeTarget_ && actualDepth == eyeDepth_;
    if (actualTarget) actualTarget->Release();
    if (actualDepth) actualDepth->Release();
    return matches;
}

bool NativeGameEyeDrawEncoder::bind_eye_output() noexcept {
    if (!context_ || !eyeTarget_ || !eyeDepth_) return false;
    ID3D11RenderTargetView* target = eyeTarget_;
    context_->OMSetRenderTargets(1u, &target, eyeDepth_);
    return eye_output_bound();
}

bool NativeGameEyeDrawEncoder::draw(
    UINT vertexCount, UINT startVertex) noexcept {
    if (!vertexCount || !eye_output_bound() ||
        drawCount_ == (std::numeric_limits<std::uint64_t>::max)())
        return false;
    context_->Draw(vertexCount, startVertex);
    ++drawCount_;
    return true;
}

bool NativeGameEyeDrawEncoder::draw_indexed(
    UINT indexCount, UINT startIndex, INT baseVertex) noexcept {
    if (!indexCount || !eye_output_bound() ||
        drawCount_ == (std::numeric_limits<std::uint64_t>::max)())
        return false;
    context_->DrawIndexed(indexCount, startIndex, baseVertex);
    ++drawCount_;
    return true;
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
        context_->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
                                     savedTargets_, &savedDepth_);
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
        // Preserve shader inputs for both game camera draws. The first eye
        // can swap or unbind resources; the second must start from the same
        // source game state, including vertex texture fetch and constant data.
        context_->VSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedVSResources_);
        context_->PSGetShaderResources(0u, D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT, savedPSResources_);
        context_->VSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedVSSamplers_);
        context_->PSGetSamplers(0u, D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT, savedPSSamplers_);
        context_->VSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedVSConstants_);
        context_->PSGetConstantBuffers(0u, D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT, savedPSConstants_);
        viewportCount_ = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
        context_->RSGetViewports(&viewportCount_, savedViewports_);
        scissorCount_ = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
        context_->RSGetScissorRects(&scissorCount_, savedScissors_);
        active_ = true;
    }
    ~ScopedNativeGameEyeOutput() noexcept {
        if (!active_) return;
        context_->OMSetRenderTargets(
            D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT, savedTargets_, savedDepth_);
        context_->OMSetBlendState(savedBlend_, savedBlendFactors_, savedSampleMask_);
        context_->OMSetDepthStencilState(savedDepthState_, savedStencilRef_);
        context_->RSSetState(savedRasterizer_);
        restore_draw_pipeline(false);
        context_->RSSetViewports(viewportCount_,
                                 viewportCount_ ? savedViewports_ : nullptr);
        context_->RSSetScissorRects(scissorCount_,
                                   scissorCount_ ? savedScissors_ : nullptr);
        for (auto*& target : savedTargets_) {
            if (target) { target->Release(); target = nullptr; }
        }
        if (savedDepth_) { savedDepth_->Release(); savedDepth_ = nullptr; }
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
        for (auto* p : savedPSConstants_) if (p) p->Release();
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
private:
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
    }
    ID3D11DeviceContext* context_{};
    std::uint32_t width_{}, height_{};
    ID3D11RenderTargetView* savedTargets_[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
    ID3D11DepthStencilView* savedDepth_{};
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
    ID3D11ShaderResourceView* savedVSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11ShaderResourceView* savedPSResources_[D3D11_COMMONSHADER_INPUT_RESOURCE_SLOT_COUNT]{};
    ID3D11SamplerState* savedVSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11SamplerState* savedPSSamplers_[D3D11_COMMONSHADER_SAMPLER_SLOT_COUNT]{};
    ID3D11Buffer* savedVSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11Buffer* savedPSConstants_[D3D11_COMMONSHADER_CONSTANT_BUFFER_API_SLOT_COUNT]{};
    ID3D11ClassInstance* savedVSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedPSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedGSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedHSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
    ID3D11ClassInstance* savedDSClasses_[D3D11_SHADER_MAX_INTERFACES]{};
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
} // namespace

void NativeGameStereoSubmission::release_local() noexcept {
    for (auto& eye : eyes_) eye.Reset();
    context_.Reset();
    eyeViews_[0] = eyeViews_[1] = 0;
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
    ID3D11Texture2D* source) const noexcept
{
    if (!context_ || !source) return false;
    Microsoft::WRL::ComPtr<ID3D11Device> contextDevice, sourceDevice;
    context_->GetDevice(contextDevice.GetAddressOf());
    source->GetDevice(sourceDevice.GetAddressOf());
    if (!contextDevice || contextDevice.Get() != sourceDevice.Get())
        return false;
    D3D11_TEXTURE2D_DESC desc{};
    source->GetDesc(&desc);
    return desc.Width == ring_.width() && desc.Height == ring_.height() &&
        desc.Format == ring_.format() && desc.MipLevels == 1u &&
        desc.ArraySize == 1u && desc.SampleDesc.Count != 0u &&
        desc.Usage == D3D11_USAGE_DEFAULT && desc.CPUAccessFlags == 0u &&
        native_game_eye_local_render_target_admitted(
            desc.BindFlags, desc.MiscFlags, D3D11_BIND_RENDER_TARGET,
            D3D11_RESOURCE_MISC_SHARED |
            D3D11_RESOURCE_MISC_SHARED_KEYEDMUTEX |
            D3D11_RESOURCE_MISC_SHARED_NTHANDLE);
}

bool NativeGameStereoSubmission::capture_eye(
    std::uint32_t eyeIndex, ID3D11Texture2D* nativeColor,
    std::uint64_t nativeDrawCount, std::uint64_t eyeViewSignature,
    std::uint32_t sourcePoseSequence) noexcept
{
    if (state_ != State::Acquired || eyeIndex >= 2u ||
        eyes_[eyeIndex] || !nativeDrawCount || !eyeViewSignature ||
        sourcePoseSequence != poseSequence_ ||
        !source_is_live(nativeColor))
        return false;
    eyes_[eyeIndex] = nativeColor;
    eyeViews_[eyeIndex] = eyeViewSignature;
    return true;
}

bool NativeGameStereoSubmission::render_game_eye_passes(
    NativeGameEyePass pass, void* user,
    std::uint32_t sourcePoseSequence,
    const NativeGameEyeColorSeed* fullTargetClear,
    const NativeGameEyeRasterState* gameRaster) noexcept
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

    // Allocate separate, full-size native depth/stencil attachments BEFORE
    // any GPU recording. A failed allocation keeps the ring cancellable and
    // cannot expose a color-only race frame to the OpenXR consumer.
    Microsoft::WRL::ComPtr<ID3D11Device> device;
    context_->GetDevice(device.GetAddressOf());
    if (!device || !ring_.width() || !ring_.height()) return false;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> depthTextures[2];
    Microsoft::WRL::ComPtr<ID3D11DepthStencilView> depthViews[2];
    for (std::uint32_t eye = 0; eye < 2u; ++eye) {
        ID3D11Texture2D* color = ring_.eye(slot_, eye);
        if (!color) return false;
        D3D11_TEXTURE2D_DESC colorDesc{};
        color->GetDesc(&colorDesc);
        if (colorDesc.Width != ring_.width() ||
            colorDesc.Height != ring_.height() ||
            colorDesc.SampleDesc.Count == 0u)
            return false;
        D3D11_TEXTURE2D_DESC depthDesc{};
        depthDesc.Width = colorDesc.Width;
        depthDesc.Height = colorDesc.Height;
        depthDesc.MipLevels = 1u;
        depthDesc.ArraySize = 1u;
        depthDesc.Format = DXGI_FORMAT_D24_UNORM_S8_UINT;
        depthDesc.SampleDesc = colorDesc.SampleDesc;
        depthDesc.Usage = D3D11_USAGE_DEFAULT;
        depthDesc.BindFlags = D3D11_BIND_DEPTH_STENCIL;
        if (FAILED(device->CreateTexture2D(
                &depthDesc, nullptr, depthTextures[eye].GetAddressOf())) ||
            FAILED(device->CreateDepthStencilView(
                depthTextures[eye].Get(), nullptr,
                depthViews[eye].GetAddressOf())))
            return false;
    }
    struct EyePassDispatch {
        NativeGameEyePass callback{};
        void* user{};
        std::uint32_t poseSequence{};
        NativeGameEyeDrawEvidence eye[2]{};
        std::uint32_t width{}, height{};
        ID3D11DepthStencilView* depth[2]{};
        const NativeGameEyeColorSeed* fullTargetClear{};
        const NativeGameEyeRasterState* gameRaster{};
    } dispatch{pass, user, sourcePoseSequence, {},
               ring_.width(), ring_.height(),
               {depthViews[0].Get(), depthViews[1].Get()},
               fullTargetClear, gameRaster};

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
                ctx, targets[eyeIndex], invocation.depth[eyeIndex]);
            if (!invocation.callback(invocation.user, ctx,
                                     targets[eyeIndex], eyeIndex,
                                     invocation.eye[eyeIndex], encoder))
                return false;
            const auto& evidence = invocation.eye[eyeIndex];
            if (!encoder.draw_count() ||
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
        !source_is_live(eyes_[0].Get()) ||
        !source_is_live(eyes_[1].Get()))
        return false;

    // submit_eye_pair itself checks canonical COM identities, every ring-owned
    // allocation, both source descriptors and MSAA resolve compatibility.
    // It queues BOTH GPU transfers before one producer EVENT. On a partial
    // command/fence failure the ring quarantines its allocation.
    if (!ring_.submit_eye_pair(context_.Get(), slot_, frameId_,
                               eyes_[0].Get(), eyes_[1].Get()))
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
