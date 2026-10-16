#include "native_game_stereo_submission.hpp"
#include "native_game_eye_pair_sources.hpp"
#include <limits>

namespace outrun::vr::dx11 {


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
        context_->RSSetViewports(viewportCount_,
                                 viewportCount_ ? savedViewports_ : nullptr);
        context_->RSSetScissorRects(scissorCount_,
                                   scissorCount_ ? savedScissors_ : nullptr);
        for (auto*& target : savedTargets_) {
            if (target) { target->Release(); target = nullptr; }
        }
        if (savedDepth_) { savedDepth_->Release(); savedDepth_ = nullptr; }
    }
    ScopedNativeGameEyeOutput(const ScopedNativeGameEyeOutput&) = delete;
    ScopedNativeGameEyeOutput& operator=(const ScopedNativeGameEyeOutput&) = delete;

    bool bind(ID3D11RenderTargetView* target) noexcept {
        if (!active_ || !target) return false;
        const D3D11_VIEWPORT viewport{
            0.0f, 0.0f, static_cast<float>(width_),
            static_cast<float>(height_), 0.0f, 1.0f};
        const D3D11_RECT scissor{
            0, 0, static_cast<LONG>(width_), static_cast<LONG>(height_)};
        context_->OMSetRenderTargets(1u, &target, nullptr);
        context_->RSSetViewports(1u, &viewport);
        context_->RSSetScissorRects(1u, &scissor);
        return true;
    }
private:
    ID3D11DeviceContext* context_{};
    std::uint32_t width_{}, height_{};
    ID3D11RenderTargetView* savedTargets_[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{};
    ID3D11DepthStencilView* savedDepth_{};
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
    std::uint32_t sourcePoseSequence) noexcept
{
    if (state_ != State::Acquired || !context_ || !pass ||
        eyes_[0] || eyes_[1] || sourcePoseSequence == 0u ||
        sourcePoseSequence != poseSequence_)
        return false;

    struct EyePassDispatch {
        NativeGameEyePass callback{};
        void* user{};
        std::uint32_t poseSequence{};
        NativeGameEyeDrawEvidence eye[2]{};
        std::uint32_t width{}, height{};
    } dispatch{pass, user, sourcePoseSequence, {}, ring_.width(), ring_.height()};

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
            if (!output.bind(targets[eyeIndex]) || !invocation.callback(
                    invocation.user, ctx, targets[eyeIndex], eyeIndex,
                    invocation.eye[eyeIndex]))
                return false;
            const auto& evidence = invocation.eye[eyeIndex];
            if (!evidence.drawCount || !evidence.viewSignature ||
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
