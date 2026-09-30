#pragma once

#include "../game/render_semantics.hpp"
#include "../hud_semantics.hpp"
#include "../d3d9/vr_pass_policy.hpp"

#include <cstdint>

namespace OutRunVR::Render
{
    // Neutral semantic contract used while R-series classifiers are flattened.
    // These mappings do not change routing by themselves; existing owners remain
    // authoritative until an explicit migration switches them to this contract.
    enum class DrawClass : std::uint8_t
    {
        Unknown = 0,
        World,
        ScreenHud,
        ScreenOverlay2D,
        WorldBillboard,
        SkyGlow,
        FragileEffect,
        Auxiliary,
        ZeroDisparity,
    };

    constexpr DrawClass FromGameSemantic(
        GameSemantic::RenderScope scope) noexcept
    {
        switch (scope)
        {
        case GameSemantic::RenderScope::SceneEffect:
            return DrawClass::FragileEffect;
        case GameSemantic::RenderScope::SkyGlow:
            return DrawClass::SkyGlow;
        case GameSemantic::RenderScope::WorldParticle:
            return DrawClass::World;
        case GameSemantic::RenderScope::WorldBillboard:
            return DrawClass::WorldBillboard;
        case GameSemantic::RenderScope::ReflectionCube:
            return DrawClass::Auxiliary;
        case GameSemantic::RenderScope::ScreenOverlay2D:
            return DrawClass::ScreenOverlay2D;
        case GameSemantic::RenderScope::ScreenHud:
            return DrawClass::ScreenHud;
        default:
            return DrawClass::Unknown;
        }
    }

    constexpr DrawClass FromHudSpace(
        OutRunVRHudSemantics::SpacePolicy space) noexcept
    {
        switch (space)
        {
        case OutRunVRHudSemantics::SpacePolicy::ScreenHud:
            return DrawClass::ScreenHud;
        case OutRunVRHudSemantics::SpacePolicy::WorldBillboard:
            return DrawClass::WorldBillboard;
        default:
            return DrawClass::Unknown;
        }
    }

    constexpr DrawClass FromPassSemantic(
        PassPolicy::RenderSemantic semantic) noexcept
    {
        switch (semantic)
        {
        case PassPolicy::RenderSemantic::World3D:
            return DrawClass::World;
        case PassPolicy::RenderSemantic::ScreenSpace2D:
            return DrawClass::ScreenOverlay2D;
        case PassPolicy::RenderSemantic::Auxiliary:
        case PassPolicy::RenderSemantic::InternalStereo:
            return DrawClass::Auxiliary;
        default:
            return DrawClass::Unknown;
        }
    }

    static_assert(FromGameSemantic(GameSemantic::RenderScope::ScreenHud) ==
        DrawClass::ScreenHud);
    static_assert(FromGameSemantic(GameSemantic::RenderScope::WorldBillboard) ==
        DrawClass::WorldBillboard);
    static_assert(FromGameSemantic(GameSemantic::RenderScope::SkyGlow) ==
        DrawClass::SkyGlow);
    static_assert(FromHudSpace(OutRunVRHudSemantics::SpacePolicy::ScreenHud) ==
        DrawClass::ScreenHud);
    static_assert(FromHudSpace(OutRunVRHudSemantics::SpacePolicy::WorldBillboard) ==
        DrawClass::WorldBillboard);
    static_assert(FromPassSemantic(PassPolicy::RenderSemantic::World3D) ==
        DrawClass::World);
    static_assert(FromPassSemantic(PassPolicy::RenderSemantic::ScreenSpace2D) ==
        DrawClass::ScreenOverlay2D);
    static_assert(FromPassSemantic(PassPolicy::RenderSemantic::Unknown) ==
        DrawClass::Unknown);
}
