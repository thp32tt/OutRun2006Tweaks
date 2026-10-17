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
        Count
    };
    enum class DrawApi : std::uint8_t {
        Primitive, Indexed, PrimitiveUP, IndexedUP, Count
    };
    constexpr std::size_t FamilyCount = static_cast<std::size_t>(Family::Count);
    constexpr std::size_t ApiCount = static_cast<std::size_t>(DrawApi::Count);

    constexpr Family Classify(const PhysicalDrawCommand& cmd) noexcept
    {
        if (cmd.IsDirectWorldLensCentre())
            return Family::CentreC993;
        if (cmd.scope == RenderScope::ProjectedScreenEffect2D)
            return !cmd.queued
                ? Family::OuterCABEProjectedCandidate
                : Family::OtherProjectedEffect;
        if (cmd.scope == RenderScope::SkyGlow)
            return Family::SkyGlow;
        if (cmd.scope == RenderScope::ScreenHud)
            return Family::GameplayHud;
        if (cmd.scope == RenderScope::ProjectedWorldMarker2D)
            return Family::ProjectedRank;
        if (cmd.scope == RenderScope::ScreenOverlay2D)
            return Family::ScreenOverlay;
        if (cmd.scope == RenderScope::WorldBillboard ||
            cmd.scope == RenderScope::WorldParticle ||
            cmd.scope == RenderScope::SceneEffect ||
            cmd.scope == RenderScope::ReflectionCube)
            return Family::World;
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
            default: return "INVALID";
        }
    }
    static_assert(Classify({RenderScope::WorldBillboard,
        ProducerToken::LensFlareCentre,nullptr,0,false,9}) ==
        Family::CentreC993);
    static_assert(Classify({RenderScope::WorldBillboard,
        ProducerToken::None,nullptr,0,false,0}) == Family::World);
    static_assert(Classify({RenderScope::ProjectedScreenEffect2D,
        ProducerToken::None,nullptr,0,false,0}) ==
        Family::OuterCABEProjectedCandidate);
    static_assert(Classify({RenderScope::ProjectedScreenEffect2D,
        ProducerToken::None,nullptr,3,true,0}) ==
        Family::OtherProjectedEffect);
    static_assert(Classify({RenderScope::SkyGlow,
        ProducerToken::None,nullptr,0,false,0}) == Family::SkyGlow);

    struct Counters
    {
        std::atomic<std::uint64_t> attempts{0};
        std::atomic<std::uint64_t> success{0};
        std::atomic<std::uint64_t> failure{0};
        std::atomic<std::uint64_t> r33BothEyes{0};
        std::atomic<std::uint64_t> r33EyeOrRestoreFailed{0};
        // This includes successful R30 early-exit stereo draws, as those
        // don't pass the R33 HUD-specific eye-pair callback. NOT "mono".
        std::atomic<std::uint64_t> noR33EyeEvidence{0};
        std::array<std::atomic<std::uint64_t>,ApiCount> api{};
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
        std::uint64_t noR33EyeEvidence = 0;
        std::array<std::uint64_t,ApiCount> api{};
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
            w.noR33EyeEvidence =
                src.noR33EyeEvidence.exchange(0,std::memory_order_relaxed);
            for (std::size_t j=0;j<ApiCount;++j)
                w.api[j] = src.api[j].exchange(0,std::memory_order_relaxed);
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
        bool paired_ = false;
        bool pairOk_ = false;
        Family family_ = Family::Unknown;
        inline static thread_local ScopedDraw* current_ = nullptr;
    public:
        ScopedDraw(bool enabled, DrawApi api) noexcept
        {
            if (!enabled) return; // no semantic snapshot in release mode
            const auto cmd = GameSemantic::CapturePhysicalDrawCommand();
            family_ = Classify(cmd);
            auto& ctr = Counts[static_cast<std::size_t>(family_)];
            ctr.attempts.fetch_add(1,std::memory_order_relaxed);
            ctr.api[static_cast<std::size_t>(api)].fetch_add(
                1,std::memory_order_relaxed);
            ctr.latestDrawId.store(
                NextDrawId.fetch_add(1,std::memory_order_relaxed),
                std::memory_order_relaxed);
            if (family_ == Family::CentreC993)
                ctr.latestCentreCall.store(
                    cmd.lensCentreCallEpoch,std::memory_order_relaxed);
            previous_=current_;
            current_=this;
            active_=true;
        }
        ScopedDraw(const ScopedDraw&)=delete;
        ScopedDraw& operator=(const ScopedDraw&)=delete;
        ~ScopedDraw() noexcept
        {
            if (!active_) return;
            auto& ctr = Counts[static_cast<std::size_t>(family_)];
            (succeeded_ ? ctr.success : ctr.failure).fetch_add(
                1,std::memory_order_relaxed);
            if (paired_) {
                (pairOk_ ? ctr.r33BothEyes :
                    ctr.r33EyeOrRestoreFailed).fetch_add(
                    1,std::memory_order_relaxed);
            } else {
                ctr.noR33EyeEvidence.fetch_add(1,std::memory_order_relaxed);
            }
            current_=previous_;
        }
        void SetResult(bool succeeded) noexcept { succeeded_=succeeded; }
        static void RecordR33EyePair(bool leftOk,bool rightOk,
                                    bool restored) noexcept
        {
            if (!current_ || !current_->active_) return;
            current_->paired_=true;
            current_->pairOk_=leftOk && rightOk && restored;
        }
    };
} // namespace OutRunVR::UniversalTrace