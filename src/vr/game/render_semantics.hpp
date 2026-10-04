#pragma once

#include "disasm_render_contract.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <atomic>
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
        // R57: a world-space anchor that the game has already projected into
        // the 640x480 sprite coordinate system before queueing the SpriteNode.
        // Unlike WorldBillboard, the final draw is intentionally 2D.
        ProjectedWorldMarker2D,
        ReflectionCube,
        // Generic canonical 2D queue content. It needs only per-eye
        // asymmetric-FOV alignment, never head/IPD/world-plane placement.
        ScreenOverlay2D,
        ScreenHud,
        // R65: exact game producer already projected a world/light effect into
        // screen space. Treat it as eye-FOV-corrected 2D without HUD ownership.
        ProjectedScreenEffect2D,
    };

    [[nodiscard]] constexpr RenderScope RenderScopeFromSpacePolicy(
        OutRunVR::DisasmContract::SpacePolicy policy) noexcept
    {
        using Policy = OutRunVR::DisasmContract::SpacePolicy;
        switch (policy)
        {
        case Policy::ScreenHud: return RenderScope::ScreenHud;
        case Policy::WorldBillboard: return RenderScope::WorldBillboard;
        case Policy::ProjectedWorldMarker2D:
            return RenderScope::ProjectedWorldMarker2D;
        case Policy::ProjectedScreenEffect2D:
            return RenderScope::ProjectedScreenEffect2D;
        default: return RenderScope::None;
        }
    }

    static_assert(RenderScopeFromSpacePolicy(
        OutRunVR::DisasmContract::SpacePolicy::ProjectedWorldMarker2D) ==
        RenderScope::ProjectedWorldMarker2D);
    static_assert(RenderScopeFromSpacePolicy(
        OutRunVR::DisasmContract::SpacePolicy::ProjectedScreenEffect2D) ==
        RenderScope::ProjectedScreenEffect2D);

    [[nodiscard]] constexpr RenderScope ClassifyCriticalProducer(
        std::uintptr_t callerRva) noexcept
    {
        return RenderScopeFromSpacePolicy(
            OutRunVR::DisasmContract::ClassifyCriticalProducer(callerRva));
    }

    static_assert(
        ClassifyCriticalProducer(0x000B9F3Au) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BA052u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BEA5Au) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BEA5Fu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BD32Eu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BD397u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BD414u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BD472u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000B9096u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000B90B3u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000B90F6u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BDE3Au) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BDAE8u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BBA89u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00060A21u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00060D40u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00060FBCu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00096AC7u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00096B14u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00096B39u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00096B94u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00096BE1u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00096C10u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x00096C6Au) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FC84Eu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FC882u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FC8B4u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FC9EBu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCA1Eu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCA51u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCB20u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCDC1u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCDEAu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCEB0u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCED9u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCF22u) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000FCF4Fu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BE5CDu) == RenderScope::ScreenHud);
    static_assert(
        ClassifyCriticalProducer(0x000BB0FBu) == RenderScope::WorldBillboard);

    struct ProjectedMarkerInfo
    {
        bool valid = false;
        float viewX = 0.0f;
        float viewY = 0.0f;
        float viewZ = 0.0f;
    };

    inline thread_local RenderScope CurrentScope = RenderScope::None;
    inline thread_local ProjectedMarkerInfo LatestProjectedScreenAnchor{};
    inline thread_local RenderScope NextDrawScope = RenderScope::None;
    inline thread_local RenderScope CurrentProducerScope = RenderScope::None;
    inline thread_local ProjectedMarkerInfo CurrentProducerMarker{};
    inline thread_local RenderScope CurrentQueueExactScope = RenderScope::None;
    inline std::atomic<int> HudExperimentMode{ 0 };

    inline void SetHudExperimentMode(int mode) noexcept
    {
        HudExperimentMode.store(mode < 0 ? 0 : (mode > 4 ? 4 : mode),
            std::memory_order_release);
    }

    inline int GetHudExperimentMode() noexcept
    {
        return HudExperimentMode.load(std::memory_order_acquire);
    }

    [[nodiscard]] constexpr bool IsExactHudScope(RenderScope scope) noexcept
    {
        // R59: ProjectedWorldMarker2D is also an exact queue owner. R58 HMD
        // telemetry proved kind-0 rank nodes were tagged correctly but helper
        // scopes overwrote CurrentScope before the D3D draw. Keep the exact
        // projected owner sticky just like SCREEN_HUD/WORLD_BILLBOARD.
        return scope == RenderScope::ScreenHud ||
            scope == RenderScope::WorldBillboard ||
            scope == RenderScope::ProjectedWorldMarker2D;
    }

    // R71 DXVK visual ownership: c64/WVP classification happens before the
    // final D3D draw consumes the queue semantic. Production mode 2 already
    // keeps exact queue ownership sticky for ConsumeForDraw(), but the generic
    // EffectiveScope() intentionally waits until mode 3. Expose only the exact
    // queue tag to the c64 boundary at mode 2; never widen untagged
    // ScreenOverlay2D into finite HUD ownership.
    [[nodiscard]] constexpr RenderScope ResolveWvpUploadScope(
        int mode, RenderScope currentScope,
        RenderScope queueExactScope) noexcept
    {
        if (mode >= 2 && IsExactHudScope(queueExactScope))
            return queueExactScope;
        if (mode >= 4 && currentScope == RenderScope::ScreenOverlay2D)
            return RenderScope::ScreenHud;
        return currentScope;
    }

    static_assert(ResolveWvpUploadScope(
        2, RenderScope::ScreenOverlay2D, RenderScope::ScreenHud) ==
        RenderScope::ScreenHud);
    static_assert(ResolveWvpUploadScope(
        2, RenderScope::ScreenOverlay2D, RenderScope::WorldBillboard) ==
        RenderScope::WorldBillboard);
    static_assert(ResolveWvpUploadScope(
        2, RenderScope::ScreenOverlay2D,
        RenderScope::ProjectedWorldMarker2D) ==
        RenderScope::ProjectedWorldMarker2D);
    static_assert(ResolveWvpUploadScope(
        2, RenderScope::ScreenOverlay2D, RenderScope::None) ==
        RenderScope::ScreenOverlay2D);
    static_assert(ResolveWvpUploadScope(
        1, RenderScope::ScreenOverlay2D, RenderScope::ScreenHud) ==
        RenderScope::ScreenOverlay2D);

    inline RenderScope EffectiveWvpUploadScope() noexcept
    {
        return ResolveWvpUploadScope(
            GetHudExperimentMode(), CurrentScope, CurrentQueueExactScope);
    }

    inline RenderScope EffectiveScope() noexcept
    {
        const int mode = GetHudExperimentMode();
        if (mode >= 3 && IsExactHudScope(CurrentQueueExactScope))
            return CurrentQueueExactScope;
        if (mode >= 4 && CurrentScope == RenderScope::ScreenOverlay2D)
            return RenderScope::ScreenHud;
        return CurrentScope;
    }

    inline const char* Name(RenderScope scope) noexcept
    {
        switch (scope)
        {
        case RenderScope::SceneEffect: return "SCENE_EFFECT";
        case RenderScope::SkyGlow: return "SKY_GLOW";
        case RenderScope::WorldParticle: return "WORLD_PARTICLE";
        case RenderScope::WorldBillboard: return "WORLD_BILLBOARD";
        case RenderScope::ProjectedWorldMarker2D: return "PROJECTED_WORLD_MARKER_2D";
        case RenderScope::ReflectionCube: return "REFLECTION_CUBE";
        case RenderScope::ScreenOverlay2D: return "SCREEN_OVERLAY_2D";
        case RenderScope::ProjectedScreenEffect2D: return "PROJECTED_SCREEN_EFFECT_2D";
        case RenderScope::ScreenHud: return "SCREEN_HUD";
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

    // Exact producer ownership survives nested sprite helpers without relying on
    // x86 stack walking. put_sprite_ex/put_sprite_ex2 sample this scope while
    // the producer call is active and attach it to every queued SpriteNode.
    class ScopedProducerSemantic
    {
        RenderScope previousScope_ = RenderScope::None;
        ProjectedMarkerInfo previousMarker_{};
    public:
        explicit ScopedProducerSemantic(
            RenderScope scope,
            const ProjectedMarkerInfo* marker = nullptr) noexcept
            : previousScope_(CurrentProducerScope),
              previousMarker_(CurrentProducerMarker)
        {
            CurrentProducerScope = scope;
            CurrentProducerMarker =
                marker ? *marker : ProjectedMarkerInfo{};
        }
        ~ScopedProducerSemantic()
        {
            CurrentProducerScope = previousScope_;
            CurrentProducerMarker = previousMarker_;
        }
        ScopedProducerSemantic(const ScopedProducerSemantic&) = delete;
        ScopedProducerSemantic& operator=(const ScopedProducerSemantic&) = delete;
    };

    inline RenderScope ProducerScope() noexcept
    {
        return CurrentProducerScope;
    }

    inline const ProjectedMarkerInfo* ProducerProjectedMarker() noexcept
    {
        return CurrentProducerMarker.valid ? &CurrentProducerMarker : nullptr;
    }

    inline void SetLatestProjectedScreenAnchor(
        const ProjectedMarkerInfo& marker) noexcept
    {
        LatestProjectedScreenAnchor = marker;
    }

    inline void ClearLatestProjectedScreenAnchor() noexcept
    {
        LatestProjectedScreenAnchor = {};
    }

    inline const ProjectedMarkerInfo* ProjectedScreenAnchor() noexcept
    {
        return LatestProjectedScreenAnchor.valid
            ? &LatestProjectedScreenAnchor : nullptr;
    }

    inline void ArmNextDraw(RenderScope scope) noexcept
    {
        NextDrawScope = scope;
    }

    inline RenderScope ConsumeForDraw() noexcept
    {
        if (NextDrawScope != RenderScope::None)
        {
            const RenderScope scope = NextDrawScope;
            NextDrawScope = RenderScope::None;
            return scope;
        }

        const int mode = GetHudExperimentMode();
        if (mode >= 2 && IsExactHudScope(CurrentQueueExactScope))
            return CurrentQueueExactScope;
        if (mode >= 4 && CurrentScope == RenderScope::ScreenOverlay2D)
            return RenderScope::ScreenHud;
        return CurrentScope;
    }

    inline bool ForceZeroDisparity(RenderScope scope) noexcept
    {
        return scope == RenderScope::SkyGlow ||
            scope == RenderScope::ScreenOverlay2D ||
            scope == RenderScope::ProjectedScreenEffect2D;
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
    enum class SpriteNodeOwner : std::uint8_t
    {
        None = 0,
        DispRank = 1,
    };

    struct SpriteNodeSemanticTag
    {
        const void* node = nullptr;
        RenderScope scope = RenderScope::None;
        std::uint64_t serial = 0;
        ProjectedMarkerInfo projectedMarker{};
        SpriteNodeOwner owner = SpriteNodeOwner::None;
    };

    inline constexpr std::size_t SpriteNodeSemanticCapacity = 0x230;
    // Producer hooks and the canonical queue renderer are not guaranteed to run
    // on the same thread. The old thread_local table therefore lost exact
    // SCREEN_HUD/WORLD_BILLBOARD ownership before draw time. Keep only the
    // semantic tag table shared; CurrentScope itself remains render-thread local.
    inline std::array<SpriteNodeSemanticTag,
        SpriteNodeSemanticCapacity> SpriteNodeSemanticTags{};
    inline std::size_t SpriteNodeSemanticCount = 0;
    inline std::atomic<std::size_t> SpriteNodeSemanticPublishedCount{ 0 };
    inline std::mutex SpriteNodeSemanticMutex;
    inline std::atomic<std::uint64_t> SpriteNodeSemanticNextSerial{ 1 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticRegistered{ 0 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticConsumed{ 0 };
    inline std::atomic<std::uint64_t> SpriteNodeSemanticStaleCleared{ 0 };
    // F16: table pressure must never evict an already-published exact owner.
    // Reject only the newest unique registration and expose the event so an
    // abnormal producer burst is diagnosable without corrupting queued nodes.
    inline std::atomic<std::uint64_t> SpriteNodeSemanticOverflowRejected{ 0 };
    inline thread_local std::uint64_t SpriteQueueSemanticCutoff = 0;
    inline thread_local RenderScope SpriteQueuePreviousScope = RenderScope::None;
    inline thread_local unsigned SpriteQueueDepth = 0;
    // Monotonic per-thread identity for the canonical queue node currently
    // being rendered. This is diagnostic/provenance state only; it does not
    // change semantic classification or draw ownership.
    inline thread_local const void* CurrentSpriteQueueNode = nullptr;
    inline thread_local std::uint64_t SpriteQueueNodeEpoch = 0;
    inline thread_local ProjectedMarkerInfo CurrentQueueProjectedMarker{};
    inline thread_local SpriteNodeOwner CurrentQueueOwner =
        SpriteNodeOwner::None;

    inline const void* CurrentQueueNode() noexcept
    {
        return CurrentSpriteQueueNode;
    }

    inline std::uint64_t CurrentQueueNodeEpoch() noexcept
    {
        return SpriteQueueNodeEpoch;
    }

    inline const ProjectedMarkerInfo* CurrentProjectedMarker() noexcept
    {
        return CurrentQueueProjectedMarker.valid
            ? &CurrentQueueProjectedMarker : nullptr;
    }

    inline SpriteNodeOwner CurrentSpriteOwner() noexcept
    {
        return CurrentQueueOwner;
    }

    inline bool QueueRenderActive() noexcept
    {
        return SpriteQueueDepth != 0;
    }

    inline void RegisterSpriteNodeScope(
        const void* node, RenderScope scope,
        const ProjectedMarkerInfo* projectedMarker = nullptr,
        SpriteNodeOwner owner = SpriteNodeOwner::None) noexcept
    {
        if (!node || scope == RenderScope::None)
            return;

        const std::uint64_t serial =
            SpriteNodeSemanticNextSerial.fetch_add(1, std::memory_order_acq_rel);
        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node == node)
            {
                SpriteNodeSemanticTags[i].scope = scope;
                SpriteNodeSemanticTags[i].serial = serial;
                SpriteNodeSemanticTags[i].projectedMarker =
                    projectedMarker ? *projectedMarker : ProjectedMarkerInfo{};
                SpriteNodeSemanticTags[i].owner = owner;
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
                { node, scope, serial,
                  projectedMarker ? *projectedMarker : ProjectedMarkerInfo{},
                  owner };
            SpriteNodeSemanticPublishedCount.store(
                SpriteNodeSemanticCount, std::memory_order_release);
            SpriteNodeSemanticRegistered.fetch_add(
                1, std::memory_order_relaxed);
            return;
        }

        // F16 fail-closed overflow policy. Existing entries may describe
        // SpriteNodes that are already queued for this render walk; evicting
        // the oldest live entry can silently turn an exact HUD/world marker
        // into generic overlay ownership. Preserve every published tag and
        // reject only this newest unique registration. A later freed slot can
        // accept the producer normally.
        SpriteNodeSemanticOverflowRejected.fetch_add(
            1, std::memory_order_relaxed);
        return;
    }

    inline RenderScope ConsumeSpriteNodeScope(
        const void* node,
        RenderScope fallback = RenderScope::ScreenOverlay2D) noexcept
    {
        if (!node ||
            SpriteNodeSemanticPublishedCount.load(
                std::memory_order_acquire) == 0)
            return fallback;

        std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node != node)
                continue;
            const RenderScope scope = SpriteNodeSemanticTags[i].scope;
            CurrentQueueProjectedMarker =
                SpriteNodeSemanticTags[i].projectedMarker;
            CurrentQueueOwner =
                SpriteNodeSemanticTags[i].owner;
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
            SpriteQueuePreviousScope = CurrentScope;
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
            const std::uint64_t next =
                SpriteNodeSemanticNextSerial.load(std::memory_order_acquire);
            SpriteQueueSemanticCutoff = next > 0 ? next - 1 : 0;
        }
        CurrentSpriteQueueNode = node;
        CurrentQueueProjectedMarker = {};
        CurrentQueueOwner = SpriteNodeOwner::None;
        if (++SpriteQueueNodeEpoch == 0)
            ++SpriteQueueNodeEpoch;
        CurrentScope = ConsumeSpriteNodeScope(
            node, RenderScope::ScreenOverlay2D);
        CurrentQueueExactScope = IsExactHudScope(CurrentScope)
            ? CurrentScope : RenderScope::None;

        // R54-A: one-shot handoff to the next D3D draw. This survives helper
        // scopes that overwrite CurrentScope between queue-node selection and
        // the actual draw call.
        if (GetHudExperimentMode() == 1 &&
            CurrentQueueExactScope != RenderScope::None)
            ArmNextDraw(CurrentQueueExactScope);
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
            CurrentQueueExactScope = RenderScope::None;
            CurrentQueueProjectedMarker = {};
            CurrentQueueOwner = SpriteNodeOwner::None;

            // Remove only tags that existed before this queue walk began.
            // A producer thread may already be preparing the next frame while
            // the render thread is finishing this one; preserve those newer tags.
            std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);
            std::size_t write = 0;
            for (std::size_t read = 0; read < SpriteNodeSemanticCount; ++read)
            {
                const auto& tag = SpriteNodeSemanticTags[read];
                if (tag.serial != 0 && tag.serial <= SpriteQueueSemanticCutoff)
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