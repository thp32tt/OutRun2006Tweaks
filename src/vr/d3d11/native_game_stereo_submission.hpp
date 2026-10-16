#pragma once

#include "native_shared_eye_ring.hpp"

namespace outrun::vr::dx11 {

// Renderer-side source evidence must be recorded AFTER this eye's native game
// D3D11 draw commands, rather than fabricated at frame submission time.
struct NativeGameEyeDrawEvidence {
    std::uint64_t drawCount{};
    std::uint64_t viewSignature{};
    std::uint32_t sourcePoseSequence{};
};
using NativeGameEyePass = bool (*)(
    void* user, ID3D11DeviceContext* context,
    ID3D11RenderTargetView* eyeTarget, std::uint32_t eyeIndex,
    NativeGameEyeDrawEvidence& evidence) noexcept;

struct NativeGameStereoPublishedFrame {
    NativeSharedEyePublication gpu{};
    // The exact pose snapshot and two camera-view signatures which produced
    // these source textures must accompany the OpenXR frame metadata.
    std::uint32_t sourcePoseSequence{};
    std::uint64_t eyeViewSignature[2]{};
};

// Ingress for TWO separately rendered, game-authored native D3D11 eye frames.
// The legacy full-frame diagnostic bridge exposes only one mono texture;
// feeding that texture to both eyes here is forbidden. A real game stereo
// renderer must call capture_eye separately after each native draw pass with
// its latched eye-view signature and a positive native draw count.
//
// One begun frame owns one ring slot until both GPU copies have been enqueued
// and the producer EVENT is complete. Dropped/partial frames never advertise
// an OpenXR handle, and the ordinary D3D9/SBS/input path is unaffected.
class NativeGameStereoSubmission final {
public:
    explicit NativeGameStereoSubmission(NativeSharedEyeRing& ring) noexcept
        : ring_(ring) {}
    ~NativeGameStereoSubmission() noexcept { (void)cancel(); }
    NativeGameStereoSubmission(const NativeGameStereoSubmission&) = delete;
    NativeGameStereoSubmission& operator=(const NativeGameStereoSubmission&) = delete;

    // Requires an initialized, lifetime-bound ring and the game renderer's
    // current immediate D3D11 context. sourcePoseSequence binds both eyes
    // to the same OpenXR pose snapshot without retaining HMD pose pointers.
    bool begin(ID3D11DeviceContext* context, std::uint64_t frameId,
               std::uint32_t sourcePoseSequence,
               const OutRunVR::Core::FrameAck* ack = nullptr) noexcept;

    // Called once per REAL native eye render. eyeViewSignature must identify
    // the game camera/projection used for that eye, not a synthetic eye index.
    // Distinct signatures prove that the renderer supplied independent views;
    // this is not a substitute for game/Quest3 visual parity verification.
    bool capture_eye(std::uint32_t eyeIndex, ID3D11Texture2D* nativeColor,
                     std::uint64_t nativeDrawCount,
                     std::uint64_t eyeViewSignature,
                     std::uint32_t sourcePoseSequence) noexcept;

    // Copy both genuine game eyes on the producer's single GPU command stream,
    // then arm its asynchronous fence. Never advertise or ACK on mere enqueue.
    // Direct native Draw/DrawIndexed stereo path: the renderer records two
    // genuinely different camera views straight into the ring's L/R RTVs.
    // Unlike capture_eye()/submit(), no extra GPU eye-to-eye copy is needed.
    // The callback must restore its D3D11 state and submit both views on the
    // supplied immediate context. A partial GPU write quarantines the ring.
    // Draw counts and signatures come from actual renderer callsites, never
    // synthetic eye-index identifiers. The original D3D9 frame is untouched.
    // The game renderer records each eye on the provided immediate context
    // and reports distinct camera/pose evidence only after its commands.
    // A rejected second eye quarantines the GPU ring; original D3D9 output
    // and input/FFB continue without a synthesized mono-to-stereo copy.
    bool render_game_eye_passes(
        NativeGameEyePass pass, void* user,
        std::uint32_t sourcePoseSequence) noexcept;

    bool render_direct_eyes(
        NativeSharedEyeRing::NativeEyeDrawRecorder recorder, void* user,
        std::uint64_t leftDrawCount, std::uint64_t rightDrawCount,
        std::uint64_t leftViewSignature, std::uint64_t rightViewSignature,
        std::uint32_t sourcePoseSequence) noexcept;

    bool submit() noexcept;
    bool try_publish(NativeGameStereoPublishedFrame& published) noexcept;

    // Safe only before the first GPU copy. After submit the ring owns all
    // in-flight work; destroy/reset the ring on synchronization failure.
    bool cancel() noexcept;

    // Build the game frame's actual DirectGPU host handoff ONLY after two
    // distinct game eye renders and the producer GPU EVENT completed. The
    // caller owns the Frame.v1 ring's seqlock publication; this edits a local
    // candidate and does not publish partially written shared memory.
    [[nodiscard]] bool attach_host_frame(
        const NativeGameStereoPublishedFrame& source,
        OutRunVR::SharedRenderFrameState& gameFrame) const noexcept;
    [[nodiscard]] bool active() const noexcept { return state_ != State::Idle; }
    [[nodiscard]] bool in_flight() const noexcept { return state_ == State::GpuPending; }

private:
    enum class State : std::uint8_t { Idle, Acquired, GpuPending };
    void release_local() noexcept;
    [[nodiscard]] bool source_is_live(ID3D11Texture2D* source) const noexcept;

    NativeSharedEyeRing& ring_;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> context_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> eyes_[2];
    std::uint64_t eyeViews_[2]{};
    std::uint64_t frameId_{};
    std::uint32_t poseSequence_{};
    std::uint32_t slot_{OutRunVR::RenderFrameRingSize};
    State state_{State::Idle};
};

} // namespace outrun::vr::dx11
