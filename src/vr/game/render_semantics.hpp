#pragma once

#include <array>
#include <cmath>
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
        // Generic canonical 2D queue content. It needs only per-eye
        // asymmetric-FOV alignment, never head/IPD/world-plane placement.
        ScreenOverlay2D,
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
        case RenderScope::ScreenOverlay2D: return "SCREEN_OVERLAY_2D";
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
        return scope == RenderScope::SkyGlow ||
            scope == RenderScope::ScreenOverlay2D;
    }

    inline bool CorroboratesWorld(RenderScope scope) noexcept
    {
        return scope == RenderScope::WorldParticle ||
            scope == RenderScope::WorldBillboard;
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
        // R52: Calc3D2D still owns the real camera/view-space depth before
        // rival-rank sprites are flattened into screen XY. Preserve that Z on
        // the exact node so R30 can reconstruct a constant-depth billboard for
        // each eye instead of treating the marker like HUD.
        float worldBillboardViewZ = 0.0f;
        bool hasWorldBillboardViewZ = false;
    };

    inline constexpr std::size_t SpriteNodeSemanticCapacity = 0x230;
    inline thread_local std::array<SpriteNodeSemanticTag,
        SpriteNodeSemanticCapacity> SpriteNodeSemanticTags{};
    inline thread_local std::size_t SpriteNodeSemanticCount = 0;
    inline thread_local RenderScope SpriteQueuePreviousScope = RenderScope::None;
    inline thread_local unsigned SpriteQueueDepth = 0;
    inline thread_local float CurrentWorldBillboardViewZ = 0.0f;
    inline thread_local bool CurrentWorldBillboardViewZValid = false;

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

    inline void RegisterSpriteNodeWorldBillboard(
        const void* node, float viewZ) noexcept
    {
        if (!node || !std::isfinite(viewZ) ||
            std::fabs(viewZ) <= 1.0e-4f ||
            std::fabs(viewZ) >= 1000000.0f)
        {
            RegisterSpriteNodeScope(node, RenderScope::WorldBillboard);
            return;
        }

        for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
        {
            if (SpriteNodeSemanticTags[i].node != node)
                continue;
            SpriteNodeSemanticTags[i].scope = RenderScope::WorldBillboard;
            SpriteNodeSemanticTags[i].worldBillboardViewZ = viewZ;
            SpriteNodeSemanticTags[i].hasWorldBillboardViewZ = true;
            return;
        }
        if (SpriteNodeSemanticCount < SpriteNodeSemanticTags.size())
        {
            SpriteNodeSemanticTags[SpriteNodeSemanticCount++] =
                { node, RenderScope::WorldBillboard, viewZ, true };
        }
    }

    inline bool TryGetCurrentWorldBillboardViewZ(float& outViewZ) noexcept
    {
        if (!CurrentWorldBillboardViewZValid ||
            !std::isfinite(CurrentWorldBillboardViewZ))
            return false;
        outViewZ = CurrentWorldBillboardViewZ;
        return true;
    }

    inline RenderScope ConsumeSpriteNodeScope(
        const void* node,
        RenderScope fallback = RenderScope::ScreenOverlay2D) noexcept
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
        }
        CurrentWorldBillboardViewZ = 0.0f;
        CurrentWorldBillboardViewZValid = false;
        if (node)
        {
            for (std::size_t i = 0; i < SpriteNodeSemanticCount; ++i)
            {
                if (SpriteNodeSemanticTags[i].node != node)
                    continue;
                const auto tag = SpriteNodeSemanticTags[i];
                SpriteNodeSemanticTags[i] =
                    SpriteNodeSemanticTags[--SpriteNodeSemanticCount];
                SpriteNodeSemanticTags[SpriteNodeSemanticCount] = {};
                CurrentScope = tag.scope;
                if (tag.scope == RenderScope::WorldBillboard &&
                    tag.hasWorldBillboardViewZ)
                {
                    CurrentWorldBillboardViewZ = tag.worldBillboardViewZ;
                    CurrentWorldBillboardViewZValid = true;
                }
                return;
            }
        }
        CurrentScope = RenderScope::ScreenOverlay2D;
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
            CurrentWorldBillboardViewZ = 0.0f;
            CurrentWorldBillboardViewZValid = false;
        }
    }
}
