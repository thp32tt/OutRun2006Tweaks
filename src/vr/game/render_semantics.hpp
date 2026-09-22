#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

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
        ReflectionCube,
        ScreenHud,
    };

    inline thread_local RenderScope CurrentScope = RenderScope::None;
    inline thread_local RenderScope NextDrawScope = RenderScope::None;

    inline const char* Name(RenderScope scope) noexcept
    {
        switch (scope)
        {
        case RenderScope::SceneEffect: return "SCENE_EFFECT";
        case RenderScope::SkyGlow: return "SKY_GLOW";
        case RenderScope::WorldParticle: return "WORLD_PARTICLE";
        case RenderScope::WorldBillboard: return "WORLD_BILLBOARD";
        case RenderScope::ReflectionCube: return "REFLECTION_CUBE";
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
        return CurrentScope;
    }

    inline bool ForceZeroDisparity(RenderScope scope) noexcept
    {
        return scope == RenderScope::SkyGlow;
    }

    inline bool CorroboratesWorld(RenderScope scope) noexcept
    {
        return scope == RenderScope::WorldParticle ||
            scope == RenderScope::WorldBillboard;
    }

    inline bool CorroboratesHud(RenderScope scope) noexcept
    {
        return scope == RenderScope::ScreenHud;
    }

    // Canonical OR2006C2C.EXE queue renderer recovered by static reverse analysis:
    //   0x42D734 enters the per-priority SpriteNode walk,
    //   0x42D762 begins one node, and
    //   0x42DCB4 is the common epilogue.
    // The queue is the authoritative ownership boundary for ordinary 2D HUD/menu
    // sprites. Individual original-mod call sites may tag a node as a world
    // billboard before it reaches this renderer.
    struct SpriteNodeSemanticTag
    {
        const void* node = nullptr;
        RenderScope scope = RenderScope::None;
    };

    inline constexpr std::size_t SpriteNodeSemanticCapacity = 0x230;
    inline thread_local std::array<SpriteNodeSemanticTag,
        SpriteNodeSemanticCapacity> SpriteNodeSemanticTags{};
    inline thread_local std::size_t SpriteNodeSemanticCount = 0;
    inline thread_local RenderScope SpriteQueuePreviousScope = RenderScope::None;
    inline thread_local unsigned SpriteQueueDepth = 0;

    inline void RegisterSpriteNodeScope(
        const void* node, RenderScope scope) noexcept
    {
        if (!node || scope == RenderScope::None)
            return;
        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node == node)
            {
                SpriteNodeSemanticTags[i].scope = scope;
                return;
            }
        }
        if (SpriteNodeSemanticCount < SpriteNodeSemanticTags.size())
        {
            SpriteNodeSemanticTags[SpriteNodeSemanticCount++] =
                { node, scope };
        }
    }

    inline RenderScope ConsumeSpriteNodeScope(
        const void* node, RenderScope fallback = RenderScope::None) noexcept
    {
        if (node)
        {
            for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
            {
                if (SpriteNodeSemanticTags[i].node != node)
                    continue;
                const RenderScope scope = SpriteNodeSemanticTags[i].scope;
                SpriteNodeSemanticTags[i] =
                    SpriteNodeSemanticTags[--SpriteNodeSemanticCount];
                SpriteNodeSemanticTags[SpriteNodeSemanticCount] = {};
                return scope;
            }
        }
        return fallback;
    }

    inline void BeginSpriteQueueRender() noexcept
    {
        if (SpriteQueueDepth++ == 0)
        {
            SpriteQueuePreviousScope = CurrentScope;
            // Queue membership alone is not HUD evidence. Runtime ea7c322d
            // proved blanket queue->SCREEN_HUD promotion can world-lock tens of
            // thousands of XYZRHW draws while the independent HUD inspector
            // resolves zero verified HUD semantics. Untagged nodes fail closed.
            CurrentScope = RenderScope::None;
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
        }
        CurrentScope = ConsumeSpriteNodeScope(node, RenderScope::None);
    }

    inline void EndSpriteQueueRender() noexcept
    {
        if (!SpriteQueueDepth)
            return;
        if (--SpriteQueueDepth == 0)
        {
            CurrentScope = SpriteQueuePreviousScope;
            SpriteQueuePreviousScope = RenderScope::None;
            SpriteNodeSemanticCount = 0;
        }
    }
}
