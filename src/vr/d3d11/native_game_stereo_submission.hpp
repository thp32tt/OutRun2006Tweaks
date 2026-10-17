#pragma once

#include "native_shared_eye_ring.hpp"

namespace outrun::vr::dx11 {

struct NativeGameEyePartialTargetClear;

// Renderer-side source evidence must be recorded AFTER this eye's native game
// D3D11 draw commands, rather than fabricated at frame submission time.
// Submit real D3D11 game-eye geometry commands on the immediate context.
// The per-eye callback cannot certify stereo from a self-reported count:
// only commands issued through this recorder contribute to drawCount.
// A successful API issue is not proof of a visible Quest3 pixel.
class NativeGameEyeDrawEncoder final {
public:
    explicit NativeGameEyeDrawEncoder(
        ID3D11DeviceContext* context, ID3D11RenderTargetView* eyeTarget,
        ID3D11DepthStencilView* eyeDepth,
        UINT targetWidth, UINT targetHeight,
        bool gameAuthoredFullColorSeed = false) noexcept
        : context_(context), eyeTarget_(eyeTarget), eyeDepth_(eyeDepth),
          targetWidth_(targetWidth), targetHeight_(targetHeight),
          authoredFullColorClearCount_(gameAuthoredFullColorSeed ? 1u : 0u) {}
    NativeGameEyeDrawEncoder(const NativeGameEyeDrawEncoder&) = delete;
    NativeGameEyeDrawEncoder& operator=(const NativeGameEyeDrawEncoder&) = delete;

    // A game callback may temporarily switch OM to a menu texture or detach
    // RT0. Explicitly restore the owned eye color+depth target before issuing
    // the next real game Draw; never certify an offscreen/desktop Draw as XR.
    [[nodiscard]] bool bind_eye_output() noexcept;
    [[nodiscard]] bool draw(UINT vertexCount, UINT startVertex) noexcept;
    [[nodiscard]] bool draw_indexed(UINT indexCount, UINT startIndex,
                                    INT baseVertex) noexcept;
    // Replay a genuine game-authored offscreen camera Draw. Unlike the
    // ordinary on-eye Draw, this advances only source chronology: a later
    // authentic game SourceCopy/Stretch must move its pixels into the eye.
    // The target must be the explicitly verified game RT0, not the XR eye
    // or an arbitrary borrowed desktop/foreign-device color attachment.
    [[nodiscard]] bool draw_offscreen(
        ID3D11RenderTargetView* gameTarget,
        UINT vertexCount, UINT startVertex) noexcept;
    [[nodiscard]] bool draw_offscreen_indexed(
        ID3D11RenderTargetView* gameTarget,
        UINT indexCount, UINT startIndex, INT baseVertex) noexcept;
    // Replay authentic game instancing into an independently allocated
    // offscreen menu/vehicle/race RTV. One call advances one source ordinal,
    // even with multiple instances; pixels reach the eye only through a
    // caller-authored Copy/Stretch event, never by direct color certification.
    [[nodiscard]] bool draw_offscreen_instanced(
        ID3D11RenderTargetView* gameTarget, UINT verticesPerInstance,
        UINT instanceCount, UINT startVertex, UINT startInstance) noexcept;
    [[nodiscard]] bool draw_offscreen_indexed_instanced(
        ID3D11RenderTargetView* gameTarget, UINT indicesPerInstance,
        UINT instanceCount, UINT startIndex, INT baseVertex,
        UINT startInstance) noexcept;
    // Game-origin instanced geometry is a single ordered GPU draw command,
    // independent of its instance count. These paths use the SAME bound eye
    // target, source Clear timeline and original D3D9 fail-closed evidence
    // policy as Draw/DrawIndexed; instances never synthesize extra ordinals.
    [[nodiscard]] bool draw_instanced(
        UINT verticesPerInstance, UINT instanceCount,
        UINT startVertex, UINT startInstance) noexcept;
    [[nodiscard]] bool draw_indexed_instanced(
        UINT indicesPerInstance, UINT instanceCount, UINT startIndex,
        INT baseVertex, UINT startInstance) noexcept;
    // Native game-owned auxiliary camera Clears are GPU source commands,
    // not XR-eye Clears or direct-eye Draw/color evidence.
    // D3D9 camera TARGET and Z/stencil rectangle Clears affect ONLY the
    // named source area; never widen a clipped camera Clear to its full RT.
    // Null region preserves original full-camera Clear behavior. All regions
    // are checked against the actual game-owned offscreen resource bounds.
    [[nodiscard]] bool clear_offscreen_game_color(
        ID3D11RenderTargetView* gameTarget, std::uint32_t argb,
        const D3D11_RECT* region = nullptr) noexcept;
    [[nodiscard]] bool clear_offscreen_game_depth_stencil(
        ID3D11RenderTargetView* gameTarget, ID3D11DepthStencilView* gameDepth,
        bool clearDepth, float depth, bool clearStencil,
        std::uint8_t stencil, const D3D11_RECT* region = nullptr) noexcept;
    // Replay a game-authored TARGET Clear at its exact position between
    // menu/vehicle/race eye Draws, never as fabricated draw evidence. Partial
    // clears require D3D11.1 ClearView (no implicit full-eye fallback).
    [[nodiscard]] bool clear_target_argb(
        std::uint32_t argb, const D3D11_RECT* region = nullptr) noexcept;
    // A real D3D9 game Z/stencil Clear can occur between geometry commands.
    [[nodiscard]] bool clear_depth_stencil(
        float depth, std::uint8_t stencil,
        bool clearDepth, bool clearStencil,
        const D3D11_RECT* region = nullptr) noexcept;
    // Replay an actual game-authored, unscaled GPU surface copy (for example
    // an offscreen menu/vehicle post-pass) into THIS bound eye. Accept a
    // game-owned DEFAULT GPU RT or shader-readable intermediate texture.
    // Also resolve a real game multisampled color RT into the eye: full-size
    // resolves stay entirely on GPU, and bounded source patches use a private
    // resolve texture without overwriting untouched eye pixels. Scaling and
    // filtering remain unsupported, with original D3D9 StretchRect fallback;
    // A caller-proven array slice can select the independently rendered L/R
    // GPU surface without duplicating one eye's contents in the other.
    // no foreign desktop RTV and no manufactured Draw evidence.
    [[nodiscard]] bool copy_game_surface(
        ID3D11Texture2D* source, const D3D11_BOX* sourceRegion,
        std::int64_t destX, std::int64_t destY,
        UINT sourceArraySlice = 0u) noexcept;
    // Per-eye native GPU replay for actual game StretchRect source crops
    // and changed-size destination rectangles (point or linear filter).
    // This never counts as a game-authored geometry draw.
    // A game postpass can store separately posed eyes in a texture array.
    // Select the original camera's mip-zero slice before GPU scaling;
    // never mix the other camera into this eye or require a CPU readback.
    [[nodiscard]] bool stretch_game_surface(
        ID3D11Texture2D* source, const D3D11_BOX& sourceRegion,
        const D3D11_RECT& destination, bool linearFilter,
        UINT sourceArraySlice = 0u) noexcept;
    // Game-origin TARGET/depth Clears and GPU Copy/Stretch postpasses are
    // replayed together after N real per-eye Draw/DrawIndexed calls in order.
    // A zero ordinal retains original pre-geometry Clear behavior.
    void set_source_clear_timeline(
        const NativeGameEyePartialTargetClear* clears, std::uint32_t eye) noexcept;
    [[nodiscard]] bool finish_source_clear_timeline() noexcept;
    [[nodiscard]] std::uint64_t draw_count() const noexcept { return drawCount_; }
    // Depth-only and color-masked game Draws still execute and contribute to
    // the command stream, but cannot by themselves certify a visible XR eye.
    [[nodiscard]] std::uint64_t color_draw_count() const noexcept { return colorDrawCount_; }
    // Completed game-authored GPU Copy/Stretch timeline events may provide
    // the eye's real color while on-eye Draws update only depth. These
    // events never increment the genuine geometry draw-count contract.
    [[nodiscard]] std::uint32_t authored_color_postpass_count() const noexcept {
        return authoredColorPostpassCount_;
    }
    // Only the submission owner can supply the original D3D9 full TARGET
    // seed. Later full-size game rectangle clears supersede prior eye color;
    // partial TARGET clears never seed an entire native eye.
    [[nodiscard]] std::uint32_t authored_full_color_clear_count() const noexcept {
        return authoredFullColorClearCount_;
    }
    [[nodiscard]] std::uint64_t last_full_clear_draw_ordinal() const noexcept {
        return lastFullClearDrawOrdinal_;
    }
private:
    [[nodiscard]] bool eye_targets_bound() const noexcept;
    [[nodiscard]] bool game_source_target_bound(
        ID3D11RenderTargetView* gameTarget) const noexcept;
    [[nodiscard]] bool prepare_offscreen_game_draw(
        ID3D11RenderTargetView* gameTarget) noexcept;
    [[nodiscard]] bool eye_output_bound() const noexcept;
    [[nodiscard]] bool eye_color_writable() const noexcept;
    [[nodiscard]] bool unpredicated_color_evidence() const noexcept;
    [[nodiscard]] bool replay_due_source_clears() noexcept;
    ID3D11DeviceContext* context_{};
    ID3D11RenderTargetView* eyeTarget_{};
    ID3D11DepthStencilView* eyeDepth_{};
    UINT targetWidth_{}, targetHeight_{};
    std::uint64_t drawCount_{};
    std::uint64_t colorDrawCount_{};
    std::uint32_t authoredColorPostpassCount_{};
    std::uint32_t authoredFullColorClearCount_{};
    std::uint64_t lastFullClearDrawOrdinal_{};
    const NativeGameEyePartialTargetClear* sourceClears_{};
    std::uint32_t sourceClearEye_{}, sourceClearCursor_{};
};

struct NativeGameEyeDrawEvidence {
    // Must match the encoder's actual Draw/DrawIndexed call count exactly.
    std::uint64_t drawCount{};
    std::uint64_t viewSignature{};
    std::uint32_t sourcePoseSequence{};
};
// A verified game-authored full-RT TARGET Clear can initialize the native
// shared L/R eye color buffers before the corresponding game Draw replay.
// ARGB values must come from each eye's actual D3D9 Clear, never a synthetic
// background or the previous frame. Partial RECT clears belong to the callback.
struct NativeGameEyeColorSeed {
    std::uint32_t argb[2]{};
};
// Actual D3D9 game Clears and GPU intermediate postpasses can occur BETWEEN
// source geometry draws. Keep TARGET, Z/stencil, Copy and Stretch events
// in ONE original per-eye timeline: replaying separately would overwrite
// earlier HUD/menu pixels or restore an older intermediate after a Clear.
// This is source-authored GPU command replay, not synthetic Draw evidence.
// Unsupported source resources/partial depth clears fail closed.
struct NativeGameEyePartialTargetClear {
    // A sustained menu -> selection -> race camera can issue more than eight
    // ordered GPU Copy/Stretch/clear postpasses between game Draws. Keep a
    // bounded per-eye command stream rather than dropping the entire frame.
    static constexpr std::uint32_t kMaxRectsPerEye = 32u;
    enum class Kind : std::uint8_t { TargetRect, FullDepthStencil, SourceCopy, SourceStretch };
    struct Entry {
        D3D11_RECT rect{};
        std::uint32_t argb{};
        std::uint64_t afterDrawOrdinal{}; // source geometry Draws before Clear
        Kind kind{Kind::TargetRect};
        float depth{1.0f};
        std::uint8_t stencil{};
        bool clearDepth{};
        bool clearStencil{};
        // SourceCopy uses an unscaled subresource 0 region/destination offset;
        // SourceStretch uses the original game crop/destination and filter.
        // Source references are borrowed only for synchronous producer replay.
        ID3D11Texture2D* source{};
        D3D11_BOX sourceBox{};
        D3D11_RECT destination{};
        std::int64_t destX{}, destY{};
        UINT sourceArraySlice{};
        bool linearFilter{};
    };
    std::uint32_t count[2]{};
    Entry entries[2][kMaxRectsPerEye]{};
};
// Depth/stencil events accept an empty rect for full-eye Clear or a captured
// bounded game rectangle. The latter is rasterized into only the requested
// depth/stencil pixels (D3D11 ClearDepthStencilView is always whole-view).
// No synthetic source Clear or geometry draw-count increment is permitted.
// Real game camera raster and pre-draw Z/stencil state, independently for L/R.
// Only a captured game source may populate this optional replay payload.
struct NativeGameEyeRasterState {
    D3D11_VIEWPORT viewport[2]{};
    D3D11_RECT scissor[2]{};
    float depthClear[2]{1.0f, 1.0f};
    std::uint8_t stencilClear[2]{};
};

using NativeGameEyePass = bool (*)(
    void* user, ID3D11DeviceContext* context,
    ID3D11RenderTargetView* eyeTarget, std::uint32_t eyeIndex,
    NativeGameEyeDrawEvidence& evidence,
    NativeGameEyeDrawEncoder& encoder) noexcept;

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
                     std::uint32_t sourcePoseSequence,
                     UINT sourceArraySlice = 0u) noexcept;

    // Copy both genuine game eyes on the producer's single GPU command stream,
    // then arm its asynchronous fence. Never advertise or ACK on mere enqueue.
    // Direct native Draw/DrawIndexed stereo path: the renderer records two
    // genuinely different camera views straight into the ring's L/R RTVs.
    // Unlike capture_eye()/submit(), no extra GPU eye-to-eye copy is needed.
    // The callback must restore its D3D11 state and submit both views on the
    // supplied immediate context. A partial GPU write quarantines the ring.
    // Draw counts and signatures come from actual renderer callsites, never
    // synthetic eye-index identifiers. The original D3D9 frame is untouched.
    // The submission binds each ring RTV as OM RT0 with a full-resolution
    // viewport and scissor and owns distinct full-sized D24S8 per-eye depth
    // surfaces, then restores the caller's OM/RS bindings on success/failure.
    // An optional verified source full-TARGET clear seeds BOTH eye colors;
    // otherwise the callback owns every color pixel (no fabricated clear).
    // The callback MUST issue its game Draw/DrawIndexed via encoder and
    // return its exact encoder.draw_count() as evidence.drawCount. Claiming a
    // positive draw count without issuing GPU geometry is rejected.
    // The callback replays game-specific depth clears and depth/blend states;
    // default native Z/stencil initial state is 1.0 / 0 at each eye start.
    // The callback supplies actual Draw/DrawIndexed and
    // restores any other shader/IA/SRV state it modifies.
    // The game renderer records each eye on the provided immediate context
    // and reports distinct camera/pose evidence only after its commands.
    // A rejected second eye quarantines the GPU ring; original D3D9 output
    // and input/FFB continue without a synthesized mono-to-stereo copy.
    bool render_game_eye_passes(
        NativeGameEyePass pass, void* user,
        std::uint32_t sourcePoseSequence,
        const NativeGameEyeColorSeed* fullTargetClear = nullptr,
        const NativeGameEyeRasterState* gameRaster = nullptr,
        const NativeGameEyePartialTargetClear* partialTargetClear = nullptr) noexcept;

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
    [[nodiscard]] bool source_is_live(
        ID3D11Texture2D* source, UINT arraySlice) const noexcept;

    NativeSharedEyeRing& ring_;
    Microsoft::WRL::ComPtr<ID3D11DeviceContext> context_;
    Microsoft::WRL::ComPtr<ID3D11Texture2D> eyes_[2];
    std::uint64_t eyeViews_[2]{};
    UINT eyeArraySlices_[2]{};
    std::uint64_t frameId_{};
    std::uint32_t poseSequence_{};
    std::uint32_t slot_{OutRunVR::RenderFrameRingSize};
    State state_{State::Idle};
};

} // namespace outrun::vr::dx11
