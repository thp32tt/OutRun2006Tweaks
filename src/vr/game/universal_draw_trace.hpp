#pragma once
// Diagnostic-only, bounded R84 physical Draw family accounting.
// Read-only: never changes original game arguments, GPU state or routing.
#include <array>
#include <atomic>
#include <cstdint>
#include <cstddef>
#include "render_semantics.hpp"

namespace OutRunVR::UniversalTrace
{
    using OutRunVR::GameSemantic::PhysicalDrawCommand;
    using OutRunVR::GameSemantic::ProducerToken;
    using OutRunVR::GameSemantic::RenderScope;

    // OUTER_CABE_CANDIDATE is a source *candidate*: exact parent identity
    // is not proven merely by the 2D projected-effect RenderScope.
    enum class Family : std::uint8_t {
        CentreC993, OuterCABEProjectedCandidate, OtherProjectedEffect,
        SkyGlow, GameplayHud, ProjectedRank, ScreenOverlay, World, Unknown,
        // Append-only diagnostic categories. Never grant GPU stereo ownership
        // from these labels; they solely distinguish failure investigations.
        StageExtension, RankDisplay, GoalAndResult, HudGlyph,
        PauseArrow, CarShadow, WorldParticles, Reflections, SceneFx,
        WorldBillboards, UnprovenLensCentre, Count
    };
    enum class DrawApi : std::uint8_t {
        Primitive, Indexed, PrimitiveUP, IndexedUP, Count
    };
    enum class Route : std::uint8_t {
        NoRouteEvidence, R30FixedSprite, R30Xyzrhw, R33HudStereo,
        R33FastWorld, R29Fallback, OriginalPreserved, StateBlockRaw,
        R26ScreenSpace, R26LowerFallback, R26ExternalImGui, Count
    };
    constexpr std::size_t RouteCount = static_cast<std::size_t>(Route::Count);
    constexpr std::size_t FamilyCount = static_cast<std::size_t>(Family::Count);
    constexpr std::size_t ApiCount = static_cast<std::size_t>(DrawApi::Count);

    constexpr Family Classify(const PhysicalDrawCommand& cmd) noexcept
    {
        if (cmd.IsDirectWorldLensCentre())
            return Family::CentreC993;
        // Lost original-lens call/c64 ownership must remain distinguishable
        // from a successfully proven C993 stereo source.
        if (cmd.producer == ProducerToken::LensFlareCentre)
            return Family::UnprovenLensCentre;
        if (cmd.scope == RenderScope::ProjectedScreenEffect2D)
            return !cmd.queued
                ? Family::OuterCABEProjectedCandidate
                : Family::OtherProjectedEffect;
        if (cmd.scope == RenderScope::SkyGlow)
            return Family::SkyGlow;
        if (cmd.scope == RenderScope::ScreenHud) {
            switch (cmd.producer) {
            case ProducerToken::StageExtensionTime:
                return Family::StageExtension;
            case ProducerToken::DispRankFirst:
            case ProducerToken::DispRankClipSprite:
                return Family::RankDisplay;
            case ProducerToken::GoalTimeHelper:
            case ProducerToken::GoalTime020:
            case ProducerToken::GoalTime150:
            case ProducerToken::ResultProgress:
            case ProducerToken::ResultTextB9200:
                return Family::GoalAndResult;
            case ProducerToken::OutRunHudText:
            case ProducerToken::OutRunHudPeripheralText:
            case ProducerToken::TextGlyphPutSprite:
            case ProducerToken::OutRunStagePrintf:
            case ProducerToken::ExactScreenHudClipSprite:
                return Family::HudGlyph;
            default:
                return Family::GameplayHud;
            }
        }
        if (cmd.scope == RenderScope::ProjectedWorldMarker2D)
            return Family::ProjectedRank;
        if (cmd.scope == RenderScope::ScreenOverlay2D)
            return cmd.producer == ProducerToken::PauseOptionArrow
                ? Family::PauseArrow : Family::ScreenOverlay;
        if (cmd.scope == RenderScope::WorldParticle)
            return cmd.producer == ProducerToken::CarBaseShadow
                ? Family::CarShadow : Family::WorldParticles;
        if (cmd.scope == RenderScope::ReflectionCube)
            return Family::Reflections;
        if (cmd.scope == RenderScope::SceneEffect)
            return Family::SceneFx;
        if (cmd.scope == RenderScope::WorldBillboard)
            return Family::WorldBillboards;
        // World is a retained legacy bucket for future source scopes.
        // Do not infer menu vs car-select vs F11 from unlabeled draws.
        return Family::Unknown;
    }

    constexpr const char* Name(Family f) noexcept
    {
        switch (f) {
            case Family::CentreC993: return "CENTRE_C993";
            case Family::OuterCABEProjectedCandidate: return "OUTER_CABE_CANDIDATE";
            case Family::OtherProjectedEffect: return "OTHER_PROJECTED_EFFECT";
            case Family::SkyGlow: return "SKYGLOW";
            case Family::GameplayHud: return "HUD";
            case Family::ProjectedRank: return "PROJECTED_RANK";
            case Family::ScreenOverlay: return "SCREEN_OVERLAY";
            case Family::World: return "WORLD";
            case Family::Unknown: return "UNKNOWN";
            case Family::StageExtension: return "STAGE_PLUS_TIME";
            case Family::RankDisplay: return "RANK_6TH_OF_6";
            case Family::GoalAndResult: return "GOAL_RESULT_TIMER";
            case Family::HudGlyph: return "HUD_TEXT_DIGITS";
            case Family::PauseArrow: return "PAUSE_OPTION_ARROW";
            case Family::CarShadow: return "PLAYER_CAR_SHADOW";
            case Family::WorldParticles: return "WORLD_PARTICLES";
            case Family::Reflections: return "REFLECTIONS";
            case Family::SceneFx: return "SCENE_FX";
            case Family::WorldBillboards: return "WORLD_BILLBOARD";
            case Family::UnprovenLensCentre: return "LENS_CENTRE_UNPROVEN";
            default: return "INVALID";
        }
    }
    static_assert(Classify({RenderScope::WorldBillboard,
        ProducerToken::LensFlareCentre,nullptr,0,false,9}) ==
        Family::CentreC993);
    static_assert(Classify({RenderScope::WorldBillboard,
        ProducerToken::None,nullptr,0,false,0}) == Family::WorldBillboards);
    static_assert(Classify({RenderScope::ProjectedScreenEffect2D,
        ProducerToken::None,nullptr,0,false,0}) ==
        Family::OuterCABEProjectedCandidate);
    static_assert(Classify({RenderScope::ProjectedScreenEffect2D,
        ProducerToken::None,nullptr,3,true,0}) ==
        Family::OtherProjectedEffect);
    static_assert(Classify({RenderScope::SkyGlow,
        ProducerToken::None,nullptr,0,false,0}) == Family::SkyGlow);


    // Producer identity from game semantics, not texture/FVF heuristics.
    static_assert(Classify({RenderScope::ScreenHud,
        ProducerToken::StageExtensionTime,nullptr,0,false,0}) ==
        Family::StageExtension);
    static_assert(Classify({RenderScope::ScreenHud,
        ProducerToken::DispRankFirst,nullptr,0,false,0}) ==
        Family::RankDisplay);
    static_assert(Classify({RenderScope::ScreenHud,
        ProducerToken::GoalTime020,nullptr,0,false,0}) ==
        Family::GoalAndResult);
    static_assert(Classify({RenderScope::ProjectedWorldMarker2D,
        ProducerToken::RankMarkerSprani,nullptr,0,false,0}) ==
        Family::ProjectedRank);
    static_assert(Classify({RenderScope::ScreenOverlay2D,
        ProducerToken::PauseOptionArrow,nullptr,0,false,0}) ==
        Family::PauseArrow);
    static_assert(Classify({RenderScope::WorldParticle,
        ProducerToken::CarBaseShadow,nullptr,0,false,0}) ==
        Family::CarShadow);
    static_assert(Classify({RenderScope::ScreenHud,
        ProducerToken::None,nullptr,0,false,0}) ==
        Family::GameplayHud);
    static_assert(Classify({RenderScope::WorldBillboard,
        ProducerToken::LensFlareCentre,nullptr,0,false,0}) ==
        Family::UnprovenLensCentre);

    struct Counters
    {
        std::atomic<std::uint64_t> attempts{0};
        std::atomic<std::uint64_t> success{0};
        std::atomic<std::uint64_t> failure{0};
        std::atomic<std::uint64_t> r33BothEyes{0};
        std::atomic<std::uint64_t> r33EyeOrRestoreFailed{0};
        std::atomic<std::uint64_t> r30BothEyes{0};
        std::atomic<std::uint64_t> r30EyeOrRestoreFailed{0};
        // No proven R30 OR R33 physical eye-pair outcome: unknown, NOT mono.
        std::atomic<std::uint64_t> noR33EyeEvidence{0};
        std::array<std::atomic<std::uint64_t>,ApiCount> api{};
        std::array<std::atomic<std::uint64_t>,RouteCount> route{};
        std::atomic<std::uint64_t> queued{0};
        std::atomic<std::uint64_t> unknownProducer{0};
        std::atomic<std::uint64_t> badQueueProvenance{0};
        std::atomic<std::uint64_t> lastQueueEpoch{0};
        std::atomic<unsigned> lastProducer{0};
        std::atomic<unsigned> lastScope{0};
        std::atomic<std::uint64_t> latestDrawId{0};
        std::atomic<std::uint64_t> latestCentreCall{0};
    };
    inline std::array<Counters,FamilyCount> Counts{};
    inline std::atomic<std::uint64_t> NextDrawId{1};

    struct Window
    {
        Family family = Family::Unknown;
        std::uint64_t attempts = 0, success = 0, failure = 0;
        std::uint64_t r33BothEyes = 0, r33EyeOrRestoreFailed = 0;
        std::uint64_t r30BothEyes = 0, r30EyeOrRestoreFailed = 0;
        std::uint64_t noR33EyeEvidence = 0;
        std::array<std::uint64_t,ApiCount> api{};
        std::array<std::uint64_t,RouteCount> route{};
        std::uint64_t queued = 0, unknownProducer = 0, badQueueProvenance = 0;
        std::uint64_t lastQueueEpoch = 0;
        unsigned lastProducer = 0, lastScope = 0;
        std::uint64_t latestDrawId = 0, latestCentreCall = 0;
    };

    // Drain only on the R33 Present telemetry interval; the hot path
    // performs bounded atomic increments, never file I/O or D3D queries.
    inline std::array<Window,FamilyCount> DrainWindow() noexcept
    {
        std::array<Window,FamilyCount> result{};
        for (std::size_t i=0; i<FamilyCount; ++i) {
            auto& src = Counts[i];
            auto& w = result[i];
            w.family = static_cast<Family>(i);
            w.attempts = src.attempts.exchange(0,std::memory_order_relaxed);
            w.success = src.success.exchange(0,std::memory_order_relaxed);
            w.failure = src.failure.exchange(0,std::memory_order_relaxed);
            w.r33BothEyes = src.r33BothEyes.exchange(0,std::memory_order_relaxed);
            w.r33EyeOrRestoreFailed =
                src.r33EyeOrRestoreFailed.exchange(0,std::memory_order_relaxed);
            w.r30BothEyes = src.r30BothEyes.exchange(0,std::memory_order_relaxed);
            w.r30EyeOrRestoreFailed =
                src.r30EyeOrRestoreFailed.exchange(0,std::memory_order_relaxed);
            w.noR33EyeEvidence =
                src.noR33EyeEvidence.exchange(0,std::memory_order_relaxed);
            for (std::size_t j=0;j<ApiCount;++j)
                w.api[j] = src.api[j].exchange(0,std::memory_order_relaxed);
            for (std::size_t j=0;j<RouteCount;++j)
                w.route[j] = src.route[j].exchange(0,std::memory_order_relaxed);
            w.queued = src.queued.exchange(0,std::memory_order_relaxed);
            w.unknownProducer = src.unknownProducer.exchange(
                0,std::memory_order_relaxed);
            w.badQueueProvenance = src.badQueueProvenance.exchange(
                0,std::memory_order_relaxed);
            w.lastQueueEpoch = src.lastQueueEpoch.load(std::memory_order_relaxed);
            w.lastProducer = src.lastProducer.load(std::memory_order_relaxed);
            w.lastScope = src.lastScope.load(std::memory_order_relaxed);
            w.latestDrawId = src.latestDrawId.load(std::memory_order_relaxed);
            w.latestCentreCall = src.latestCentreCall.load(std::memory_order_relaxed);
        }
        return result;
    }

    // Nesting-safe: a left native draw may synchronously re-enter another
    // producer. Physical draw IDs remain assigned to the *outer* callback.
    class ScopedDraw final
    {
        ScopedDraw* previous_ = nullptr;
        bool active_ = false;
        bool succeeded_ = false;
        bool initialized_ = false;
        bool pairFromR30_ = false;
        DrawApi api_ = DrawApi::Primitive;
        bool paired_ = false;
        bool pairOk_ = false;
        Route route_ = Route::NoRouteEvidence;
        Family family_ = Family::Unknown;
        inline static thread_local ScopedDraw* current_ = nullptr;
    public:
        ScopedDraw(bool enabled, DrawApi api) noexcept : api_(api)
        {
            if (!enabled) return;
            // Physical provenance is selected by R33Guard's ConsumeForDraw.
            // The pre-consumption one-shot scope may belong to an old Draw.
            previous_=current_;
            current_=this;
            active_=true;
        }
        static void RefreshAfterSemanticSelection() noexcept
        {
            if (!current_ || !current_->active_ || current_->initialized_)
                return;
            auto& self = *current_;
            const auto cmd = GameSemantic::CapturePhysicalDrawCommand();
            self.family_ = Classify(cmd);
            auto& ctr = Counts[static_cast<std::size_t>(self.family_)];
            ctr.attempts.fetch_add(1,std::memory_order_relaxed);
            if (cmd.queued) {
                ctr.queued.fetch_add(1,std::memory_order_relaxed);
                if (!cmd.queueNode || !cmd.queueEpoch)
                    ctr.badQueueProvenance.fetch_add(1,std::memory_order_relaxed);
            }
            if (cmd.producer == ProducerToken::None)
                ctr.unknownProducer.fetch_add(1,std::memory_order_relaxed);
            ctr.lastQueueEpoch.store(cmd.queueEpoch,std::memory_order_relaxed);
            ctr.lastProducer.store(static_cast<unsigned>(cmd.producer),
                                   std::memory_order_relaxed);
            ctr.lastScope.store(static_cast<unsigned>(cmd.scope),
                                std::memory_order_relaxed);
            ctr.api[static_cast<std::size_t>(self.api_)].fetch_add(
                1,std::memory_order_relaxed);
            ctr.latestDrawId.store(
                NextDrawId.fetch_add(1,std::memory_order_relaxed),
                std::memory_order_relaxed);
            if (self.family_ == Family::CentreC993)
                ctr.latestCentreCall.store(
                    cmd.lensCentreCallEpoch,std::memory_order_relaxed);
            self.initialized_ = true;
        }
        ScopedDraw(const ScopedDraw&)=delete;
        ScopedDraw& operator=(const ScopedDraw&)=delete;
        ~ScopedDraw() noexcept
        {
            if (!active_) return;
            if (!initialized_) { current_ = previous_; return; }
            auto& ctr = Counts[static_cast<std::size_t>(family_)];
            ctr.route[static_cast<std::size_t>(route_)].fetch_add(
                1,std::memory_order_relaxed);
            (succeeded_ ? ctr.success : ctr.failure).fetch_add(
                1,std::memory_order_relaxed);
            if (paired_) {
                if (pairFromR30_)
                    (pairOk_ ? ctr.r30BothEyes :
                        ctr.r30EyeOrRestoreFailed).fetch_add(
                        1,std::memory_order_relaxed);
                else
                    (pairOk_ ? ctr.r33BothEyes :
                        ctr.r33EyeOrRestoreFailed).fetch_add(
                        1,std::memory_order_relaxed);
            } else {
                ctr.noR33EyeEvidence.fetch_add(1,std::memory_order_relaxed);
            }
            current_=previous_;
        }
        void SetResult(bool succeeded) noexcept { succeeded_=succeeded; }
        static void RecordRoute(Route route) noexcept
        {
            if (current_ && current_->active_)
                current_->route_=route;
        }
        static void RecordR33EyePair(bool leftOk,bool rightOk,
                                    bool restored) noexcept
        {
            if (!current_ || !current_->initialized_) return;
            current_->paired_=true;
            current_->pairFromR30_=false;
            current_->pairOk_=leftOk && rightOk && restored;
        }
        // R30 early stereo reports both actual eye/restore outcomes;
        // the outer native HRESULT remains the game's left-eye HRESULT.
        static void RecordR30EyePair(bool leftOk,bool rightOk,
                                    bool restored) noexcept
        {
            if (!current_ || !current_->initialized_) return;
            current_->paired_=true;
            current_->pairFromR30_=true;
            current_->pairOk_=leftOk && rightOk && restored;
        }
    };
} // namespace OutRunVR::UniversalTrace