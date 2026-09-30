#pragma once

#include "../game/render_semantics.hpp"

namespace OutRunVR::Render
{
    using DrawSemantic = GameSemantic::RenderScope;
    using ScopedDrawSemantic = GameSemantic::ScopedRenderSemantic;

    inline DrawSemantic AcquireDrawSemantic(bool consumeNextDraw) noexcept
    {
        return consumeNextDraw
            ? GameSemantic::ConsumeForDraw()
            : GameSemantic::CurrentScope;
    }
}
