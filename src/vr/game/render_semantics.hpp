#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <mutex>

namespace OutRunVR::GameSemantic
{
    // Game-level render ownership recovered from the original mod's reverse
    // engineering. This complements D3D-state heuristics; it never replaces
    // the fail-closed target/depth/WVP gates by itself.
    enum class RenderScope : std::uint8_t
    {
        None = 0,
        SceneEffect,
        SkyGlow,
        WorldParticle,
        WorldBillboard,
        // Exact vehicle-relative world anchor that the game already projected
        // into its 640x480 sprite coordinate system before queueing.
        ProjectedWorldMarker2D,
        // Canonical lens/SceneEffect producer at EXE+0xCABE: the game has
        // already projected the light/effect into screen-oriented geometry,
        // but the draw still needs an exact VR owner rather than generic alpha.
        ProjectedScreenEffect2D,
        ReflectionCube,
        // Generic canonical 2D queue content is NOT evidence of game
        // world geometry or an exact named HUD producer. The current
        // R51 R26+HUD renderer nevertheless uses the same finite,
        // recentered HUD-plane eye transform when it can prove a safe
        // original c64 (VS) or source geometry (XYZRHW). Never describe
        // the *current* accepted ScreenOverlay2D GPU route as FOV-only.
        ScreenOverlay2D,
        ScreenHud,
    };

    struct ProjectedMarkerInfo
    {
        bool valid = false;
        float viewX = 0.0f;
        float viewY = 0.0f;
        float viewZ = 0.0f;
    };

    // Bounded diagnostic identity for exact producer families recovered from
    // original-mod callsites. This token never grants render ownership by
    // itself; it only follows already-explicit semantic tags so queue -> c64 ->
    // draw lifetime can be correlated without broadening HUD/world heuristics.
    enum class ProducerToken : std::uint8_t
    {
        None = 0,
        RankMarkerSprani,
        RankMarkerClipSprite,
        ExactScreenHudClipSprite,
        RivalMarkerSprani,
        TextGlyphPutSprite,
        OutRunStagePrintf,
        ResultProgress,
        // Original GOAL stage/result print parent at 19 exact
        // EXE 0x97xxx CALLs -> sub_4B9200; unlike the progress bar
        // calls, these print elapsed record/stage text.
        ResultTextB9200,
        // Three exact 0x989xx sprani producers in original gameplay
        // extension-time transition (NOT 0x97xxx final GOAL result).
        StageExtensionTime,
        GoalTimeHelper,
        OutRunHudText,
        DispRankFirst,
        // Two independent original GOAL E8 helper parents. Keep the
        // generic token for historic records, but distinguish the actual
        // 0xBEA5A vs 0xBEA5F result glyph source in HMD evidence.
        GoalTime020,
        GoalTime150,
        // R64 HMD-confirmed 6th/6 isolate: kind-0 exact DispRank
        // children are not generic result/time/right-aligned clip HUD.
        // Keep their source distinct so D3DXSprite::Flush never widens
        // to menu, result, +TIME, DDS or all ScreenHud.
        DispRankClipSprite,
    };

    inline thread_local RenderScope CurrentScope = RenderScope::None;
    // An explicit SpriteNode producer owns its render space through the
    // complete queue draw. Temporary helper scopes must not replace it.
    // Generic untagged ScreenOverlay2D is deliberately excluded.
    inline thread_local RenderScope CurrentQueueExactScope = RenderScope::None;
    inline thread_local RenderScope NextDrawScope = RenderScope::None;
    inline thread_local unsigned ExternalOverlaySemanticDepth = 0;

    inline const char* Name(RenderScope scope) noexcept
    {
        switch (scope)
        {
        case RenderScope::SceneEffect: return "SCENE_EFFECT";
        case RenderScope::SkyGlow: return "SKY_GLOW";
        case RenderScope::WorldParticle: return "WORLD_PARTICLE";
        case RenderScope::WorldBillboard: return "WORLD_BILLBOARD";
        case RenderScope::ProjectedWorldMarker2D: return "PROJECTED_WORLD_MARKER_2D";
        case RenderScope::ProjectedScreenEffect2D: return "PROJECTED_SCREEN_EFFECT_2D";
        case RenderScope::ReflectionCube: return "REFLECTION_CUBE";
        case RenderScope::ScreenOverlay2D: return "SCREEN_OVERLAY_2D";
        case RenderScope::ScreenHud: return "SCREEN_HUD";
        default: return "NONE";
        }
    }

    inline const char* Name(ProducerToken token) noexcept
    {
        switch (token)
        {
        case ProducerToken::RankMarkerSprani: return "RANK_MARKER_SPRANI";
        case ProducerToken::RankMarkerClipSprite: return "RANK_MARKER_CLIP";
        case ProducerToken::ExactScreenHudClipSprite: return "EXACT_SCREEN_HUD_CLIP";
        case ProducerToken::RivalMarkerSprani: return "RIVAL_MARKER_SPRANI";
        case ProducerToken::TextGlyphPutSprite: return "TEXT_GLYPH_PUTSPRITE";
        case ProducerToken::OutRunStagePrintf: return "OUTRUN_STAGE_PRINT";
        case ProducerToken::ResultProgress: return "OUTRUN_RESULT_PROGRESS";
        case ProducerToken::ResultTextB9200: return "OUTRUN_RESULT_TEXT_B9200";
        case ProducerToken::StageExtensionTime: return "OUTRUN_STAGE_EXTENSION_TIME";
        case ProducerToken::GoalTimeHelper: return "GOAL_TIME_HELPER";
        case ProducerToken::OutRunHudText: return "OUTRUN_HUD_TEXT";
        case ProducerToken::DispRankFirst: return "DISPLAY_RANK_FIRST";
        case ProducerToken::GoalTime020: return "GOAL_TIME_HELPER_020";
        case ProducerToken::GoalTime150: return "GOAL_TIME_HELPER_150";
        case ProducerToken::DispRankClipSprite: return "DISPRANK_KIND0_CLIP";
        default: return "NONE";
        }
    }

    class ScopedRenderSemantic
    {
        RenderScope previous_ = RenderScope::None;
    public:
        explicit ScopedRenderSemantic(RenderScope scope) noexcept
            : previous_(CurrentScope)
        {
            CurrentScope = scope;
        }
        ~ScopedRenderSemantic()
        {
            CurrentScope = previous_;
        }
        ScopedRenderSemantic(const ScopedRenderSemantic&) = delete;
        ScopedRenderSemantic& operator=(const ScopedRenderSemantic&) = delete;
    };

    class ScopedExternalOverlaySemantic
    {
        RenderScope previous_ = RenderScope::None;
    public:
        explicit ScopedExternalOverlaySemantic(RenderScope scope) noexcept
            : previous_(CurrentScope)
        {
            ++ExternalOverlaySemanticDepth;
            CurrentScope = scope;
        }
        ~ScopedExternalOverlaySemantic()
        {
            if (ExternalOverlaySemanticDepth != 0)
                --ExternalOverlaySemanticDepth;
            CurrentScope = previous_;
        }
        ScopedExternalOverlaySemantic(const ScopedExternalOverlaySemantic&) = delete;
        ScopedExternalOverlaySemantic& operator=(const ScopedExternalOverlaySemantic&) = delete;
    };

    inline RenderScope EffectiveScope() noexcept
    {
        // F11 is an external overlay, never a game SpriteNode consumer.
        if (ExternalOverlaySemanticDepth != 0)
            return CurrentScope;
        if (CurrentQueueExactScope == RenderScope::ScreenHud ||
            CurrentQueueExactScope == RenderScope::WorldBillboard ||
            CurrentQueueExactScope == RenderScope::ProjectedWorldMarker2D)
            return CurrentQueueExactScope;
        return CurrentScope;
    }

    inline void ArmNextDraw(RenderScope scope) noexcept
    {
        NextDrawScope = scope;
    }

    inline RenderScope ConsumeForDraw() noexcept
    {
        // External UI such as the F11 ImGui overlay is not a game producer.
        // Never let it consume a pending game semantic token.
        if (ExternalOverlaySemanticDepth != 0)
            return CurrentScope;
        if (NextDrawScope != RenderScope::None)
        {
            const RenderScope scope = NextDrawScope;
            NextDrawScope = RenderScope::None;
            return scope;
        }
        return EffectiveScope();
    }

    inline bool ForceZeroDisparity(RenderScope scope) noexcept
    {
        return scope == RenderScope::SkyGlow ||
            scope == RenderScope::ScreenOverlay2D;
    }

    inline bool CorroboratesWorld(RenderScope scope) noexcept
    {
        return scope == RenderScope::WorldParticle ||
            scope == RenderScope::WorldBillboard;
    }

    inline bool CorroboratesProjectedWorldMarker(RenderScope scope) noexcept
    {
        return scope == RenderScope::ProjectedWorldMarker2D;
    }

    inline bool CorroboratesProjectedScreenEffect(RenderScope scope) noexcept
    {
        return scope == RenderScope::ProjectedScreenEffect2D;
    }

    inline bool CorroboratesScreenOverlay2D(RenderScope scope) noexcept
    {
        return scope == RenderScope::ScreenOverlay2D;
    }

    inline bool CorroboratesHud(RenderScope scope) noexcept
    {
        // ScreenOverlay2D is intentionally NOT a finite/world-locked HUD.
        // Only exact producer evidence may enter ScreenHud.
        return scope == RenderScope::ScreenHud;
    }

    // Canonical OR2006C2C.EXE queue renderer recovered by static reverse analysis:
    //   0x42D734 enters the per-priority SpriteNode walk,
    //   0x42D762 begins one node, and
    //   0x42DCB4 is the common epilogue.
    // The queue provides a stable per-node execution boundary, but queue
    // membership alone is NOT semantic finite-HUD evidence. Untagged nodes are
    // generic ScreenOverlay2D: correct only the OpenXR asymmetric-FOV mapping,
    // without head inverse, eye translation, depth reset, or world-plane
    // placement. Exact producer evidence may still tag ScreenHud/WorldBillboard.
    struct SpriteNodeSemanticTag
    {
        const void* node = nullptr;
        RenderScope scope = RenderScope::None;
        ProducerToken producer = ProducerToken::None;
        std::uint64_t serial = 0;
        ProjectedMarkerInfo projectedMarker{};
    };

    inline constexpr std::size_t SpriteNodeSemanticCapacity = 0x230;

    // Exact semantic producers and the canonical SpriteNode queue renderer are
    // not guaranteed to execute on the same thread. Keep only the tag registry
    // shared and synchronized; render cursor/scope state below remains local.
    // PublishedCount lets the overwhelmingly common no-tag path avoid taking
    // the mutex at all.
    inline std::array<SpriteNodeSemanticTag,
        SpriteNodeSemanticCapacity> SpriteNodeSemanticTags{};
    inline std::size_t SpriteNodeSemanticCount = 0;
    inline std::atomic<std::size_t> SpriteNodeSemanticPublishedCount{ 0 };
    inline std::mutex SpriteNodeSemanticMutex;
    inline std::atomic<std::uint64_t> SpriteNodeSemanticNextSerial{ 1 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticRegistered{ 0 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticConsumed{ 0 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticStaleCleared{ 0 };
    inline thread_local std::uint64_t SpriteQueueSemanticCutoff = 0;

    inline thread_local RenderScope SpriteQueuePreviousScope = RenderScope::None;
    inline thread_local unsigned SpriteQueueDepth = 0;
    // Monotonic per-thread identity for the canonical queue node currently
    // being rendered. This is diagnostic/provenance state only; it does not
    // change semantic classification or draw ownership.
    inline thread_local const void* CurrentSpriteQueueNode = nullptr;
    inline thread_local std::uint64_t SpriteQueueNodeEpoch = 0;
    inline thread_local ProducerToken CurrentSpriteQueueProducer =
        ProducerToken::None;
    inline thread_local ProjectedMarkerInfo CurrentQueueProjectedMarker{};

    inline const void* CurrentQueueNode() noexcept
    {
        return CurrentSpriteQueueNode;
    }

    inline std::uint64_t CurrentQueueNodeEpoch() noexcept
    {
        return SpriteQueueNodeEpoch;
    }

    inline ProducerToken CurrentQueueProducerToken() noexcept
    {
        return CurrentSpriteQueueProducer;
    }

    inline const ProjectedMarkerInfo* CurrentProjectedMarker() noexcept
    {
        return CurrentQueueProjectedMarker.valid
            ? &CurrentQueueProjectedMarker : nullptr;
    }

    inline bool QueueRenderActive() noexcept
    {
        return SpriteQueueDepth != 0;
    }

    inline void RegisterSpriteNodeScope(
        const void* node, RenderScope scope,
        ProducerToken producer = ProducerToken::None,
        const ProjectedMarkerInfo* projectedMarker = nullptr) noexcept
    {
        if (!node || scope == RenderScope::None)
            return;

        // Publish serial and tag atomically with respect to queue cutoff.
        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        const std::uint64_t serial =
            SpriteNodeSemanticNextSerial.fetch_add(
                1, std::memory_order_acq_rel);
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node == node)
            {
                SpriteNodeSemanticTags[i].scope = scope;
                SpriteNodeSemanticTags[i].producer = producer;
                SpriteNodeSemanticTags[i].serial = serial;
                SpriteNodeSemanticTags[i].projectedMarker =
                    projectedMarker ? *projectedMarker : ProjectedMarkerInfo{};
                SpriteNodeSemanticPublishedCount.store(
                    SpriteNodeSemanticCount, std::memory_order_release);
                SpriteNodeSemanticRegistered.fetch_add(
                    1, std::memory_order_relaxed);
                return;
            }
        }

        if (SpriteNodeSemanticCount < SpriteNodeSemanticTags.size())
        {
            SpriteNodeSemanticTags[SpriteNodeSemanticCount++] =
                { node, scope, producer, serial,
                  projectedMarker ? *projectedMarker : ProjectedMarkerInfo{} };
            SpriteNodeSemanticPublishedCount.store(
                SpriteNodeSemanticCount, std::memory_order_release);
            SpriteNodeSemanticRegistered.fetch_add(
                1, std::memory_order_relaxed);
            return;
        }

        // Exact producers are sparse. If a broken frame fills the bounded
        // table, replace the oldest tag rather than silently losing semantic
        // ownership for the remainder of the run.
        std::size_t oldest = 0;
        for (std::size_t i = 1; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].serial <
                SpriteNodeSemanticTags[oldest].serial)
                oldest = i;
        }
        SpriteNodeSemanticTags[oldest] =
            { node, scope, producer, serial,
              projectedMarker ? *projectedMarker : ProjectedMarkerInfo{} };
        SpriteNodeSemanticRegistered.fetch_add(
            1, std::memory_order_relaxed);
        SpriteNodeSemanticStaleCleared.fetch_add(
            1, std::memory_order_relaxed);
    }

    inline RenderScope PeekSpriteNodeScope(
        const void* node,
        RenderScope fallback = RenderScope::None,
        ProducerToken* producer = nullptr,
        ProjectedMarkerInfo* projectedMarker = nullptr) noexcept
    {
        if (producer)
            *producer = ProducerToken::None;
        if (projectedMarker)
            *projectedMarker = {};
        if (!node ||
            SpriteNodeSemanticPublishedCount.load(
                std::memory_order_acquire) == 0)
            return fallback;

        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node != node)
                continue;
            if (producer)
                *producer = SpriteNodeSemanticTags[i].producer;
            if (projectedMarker)
                *projectedMarker = SpriteNodeSemanticTags[i].projectedMarker;
            return SpriteNodeSemanticTags[i].scope;
        }
        return fallback;
    }

    inline ProducerToken PeekSpriteNodeProducerToken(
        const void* node) noexcept
    {
        ProducerToken producer = ProducerToken::None;
        (void)PeekSpriteNodeScope(
            node, RenderScope::None, &producer);
        return producer;
    }

    inline RenderScope ConsumeSpriteNodeScope(
        const void* node,
        RenderScope fallback = RenderScope::ScreenOverlay2D,
        ProducerToken* producer = nullptr,
        bool* exactTag = nullptr) noexcept
    {
        if (producer)
            *producer = ProducerToken::None;
        if (exactTag)
            *exactTag = false;
        if (!node ||
            SpriteNodeSemanticPublishedCount.load(
                std::memory_order_acquire) == 0)
            return fallback;

        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        CurrentQueueProjectedMarker = {};
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node != node)
                continue;
            const RenderScope scope = SpriteNodeSemanticTags[i].scope;
            if (exactTag)
                *exactTag = true;
            if (producer)
                *producer = SpriteNodeSemanticTags[i].producer;
            CurrentQueueProjectedMarker =
                SpriteNodeSemanticTags[i].projectedMarker;
            SpriteNodeSemanticTags[i] =
                SpriteNodeSemanticTags[--SpriteNodeSemanticCount];
            SpriteNodeSemanticTags[SpriteNodeSemanticCount] = {};
            SpriteNodeSemanticPublishedCount.store(
                SpriteNodeSemanticCount, std::memory_order_release);
            SpriteNodeSemanticConsumed.fetch_add(
                1, std::memory_order_relaxed);
            return scope;
        }
        return fallback;
    }

    inline void BeginSpriteQueueRender() noexcept
    {
        if (SpriteQueueDepth++ == 0)
        {
            CurrentQueueExactScope = RenderScope::None;
            SpriteQueuePreviousScope = CurrentScope;
            // Serial publication and queue snapshot must share a mutex.
            {
                std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
                const std::uint64_t next =
                    SpriteNodeSemanticNextSerial.load(std::memory_order_acquire);
                SpriteQueueSemanticCutoff = next > 0 ? next - 1 : 0;
            }
            // Runtime ea7c322d proved queue->SCREEN_HUD is too strong, while
            // runtime 9554272a proved queue->NONE leaves 2D content duplicated
            // at identical D3D screen coordinates, which does not converge under
            // asymmetric OpenXR eye FOV. Generic queue content therefore owns
            // only the per-eye FOV affine, not the finite world-locked HUD plane.
            CurrentScope = RenderScope::ScreenOverlay2D;
        }
    }

    inline void SelectSpriteQueueNode(const void* node) noexcept
    {
        // Do not hook the canonical queue entry at RVA 0x2D734. Two real
        // crashes (EXE+0x2D738 and EXE+0x2D73E) proved that relocating the
        // tiny entry/prologue block with a mid-hook is not runtime-safe.
        //
        // The first node at RVA 0x2D762 is the earliest point where semantic
        // ownership is actually needed, so lazily open the queue scope here.
        if (!SpriteQueueDepth)
        {
            SpriteQueueDepth = 1;
            SpriteQueuePreviousScope = CurrentScope;
            // Serial publication and queue snapshot must share a mutex.
            {
                std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
                const std::uint64_t next =
                    SpriteNodeSemanticNextSerial.load(std::memory_order_acquire);
                SpriteQueueSemanticCutoff = next > 0 ? next - 1 : 0;
            }
        }
        CurrentSpriteQueueNode = node;
        CurrentQueueProjectedMarker = {};
        CurrentQueueExactScope = RenderScope::None;
        if (++SpriteQueueNodeEpoch == 0)
            ++SpriteQueueNodeEpoch;
        CurrentSpriteQueueProducer = ProducerToken::None;
        bool exactTag = false;
        CurrentScope = ConsumeSpriteNodeScope(
            node, RenderScope::ScreenOverlay2D,
            &CurrentSpriteQueueProducer, &exactTag);
        if (exactTag && (CurrentScope == RenderScope::ScreenHud ||
                         CurrentScope == RenderScope::WorldBillboard ||
                         CurrentScope == RenderScope::ProjectedWorldMarker2D))
            CurrentQueueExactScope = CurrentScope;
    }

    inline void EndSpriteQueueRender() noexcept
    {
        if (!SpriteQueueDepth)
            return;
        if (--SpriteQueueDepth == 0)
        {
            CurrentScope = SpriteQueuePreviousScope;
            SpriteQueuePreviousScope = RenderScope::None;
            CurrentSpriteQueueNode = nullptr;
            CurrentSpriteQueueProducer = ProducerToken::None;
            CurrentQueueProjectedMarker = {};
            CurrentQueueExactScope = RenderScope::None;

            // Remove only tags that existed when this queue walk began. A
            // producer thread may already be preparing the next frame while
            // the renderer is finishing this one; preserve those newer tags.
            std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
            std::size_t write = 0;
            for (std::size_t read = 0;
                read < SpriteNodeSemanticCount; ++read)
            {
                const auto& tag = SpriteNodeSemanticTags[read];
                if (tag.serial != 0 &&
                    tag.serial <= SpriteQueueSemanticCutoff)
                {
                    SpriteNodeSemanticStaleCleared.fetch_add(
                        1, std::memory_order_relaxed);
                    continue;
                }
                if (write != read)
                    SpriteNodeSemanticTags[write] = tag;
                ++write;
            }
            while (SpriteNodeSemanticCount > write)
                SpriteNodeSemanticTags[--SpriteNodeSemanticCount] = {};
            SpriteNodeSemanticPublishedCount.store(
                SpriteNodeSemanticCount, std::memory_order_release);
            SpriteQueueSemanticCutoff = 0;
        }
    }

}
