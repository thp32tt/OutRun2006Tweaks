#pragma once

#include "dispatch_semantics.hpp"
#include "../d3d9/screen_space_policy.hpp"
#include "../d3d9/vr_pass_policy.hpp"
#include "../lifecycle/reset_replay_policy.hpp"

namespace OutRunVR::Core::RefactorContract
{
    static_assert(SemanticRouteFor(GameSemantic::RenderScope::ScreenHud) ==
        SemanticRoute::ScreenHud);
    static_assert(SemanticRouteFor(GameSemantic::RenderScope::WorldBillboard) ==
        SemanticRoute::World);
    static_assert(ScreenSpacePolicy::DirectKind(
        SemanticRoute::ProjectedWorld) ==
        ScreenSpacePolicy::Kind::ProjectedWorldMarker2D);
    static_assert(PassPolicy::AllowsWorldStereo(
        PassPolicy::RenderSemantic::World3D));
    static_assert(!PassPolicy::AllowsWorldStereo(
        PassPolicy::RenderSemantic::Unknown));
    static_assert(Lifecycle::ResetReplayHealthy(true, true));
    static_assert(!Lifecycle::ResetReplayHealthy(true, false));
    static_assert(!Lifecycle::ResetReplayHealthy(false, true));
    static_assert(!Lifecycle::ResetReplayHealthy(false, false));
    constexpr bool CheckDrawReplayCase(unsigned mask) noexcept
    {
        const bool gameDevice = (mask & 0x01u) != 0;
        const bool internalStereo = (mask & 0x02u) != 0;
        const bool mainBackbuffer = (mask & 0x04u) != 0;
        const bool forceMonoShadow = (mask & 0x08u) != 0;
        const bool stereoWanted = (mask & 0x10u) != 0;
        const bool stereoSeeded = (mask & 0x20u) != 0;
        const bool unsafeMrt = (mask & 0x40u) != 0;
        const bool unsafeOcclusion = (mask & 0x80u) != 0;

        PassPolicy::DrawReplayPolicy expected = PassPolicy::DrawReplayPolicy::Legacy;
        if (gameDevice && !internalStereo && mainBackbuffer)
        {
            if (forceMonoShadow)
                expected = PassPolicy::DrawReplayPolicy::ForcedMonoShadow;
            else if (stereoWanted && stereoSeeded &&
                (unsafeMrt || unsafeOcclusion))
                expected = PassPolicy::DrawReplayPolicy::UnsafeSingleExecution;
        }
        return PassPolicy::ClassifyDrawReplay(
            gameDevice, internalStereo, mainBackbuffer, forceMonoShadow,
            stereoWanted, stereoSeeded, unsafeMrt, unsafeOcclusion) == expected;
    }

    constexpr bool CheckEffectCase(unsigned mask) noexcept
    {
        const bool alphaBlend = (mask & 0x01u) != 0;
        const bool alphaTest = (mask & 0x02u) != 0;
        const bool depthWrite = (mask & 0x04u) != 0;
        const bool depthTest = (mask & 0x08u) != 0;
        const bool cullNone = (mask & 0x10u) != 0;
        const auto expected = depthTest
            ? PassPolicy::EffectStereoPolicy::WorldStereo
            : PassPolicy::EffectStereoPolicy::ZeroDisparity;
        return PassPolicy::ClassifyEffectStereo(
            alphaBlend, alphaTest, depthWrite, depthTest, cullNone) == expected;
    }

    constexpr bool CheckFixedFunctionCase(unsigned id) noexcept
    {
        const unsigned projectionId = id % 3u;
        const bool gameplay = ((id / 3u) & 1u) != 0;
        const bool depthTest = ((id / 6u) & 1u) != 0;
        const auto projection = projectionId == 0
            ? PassPolicy::ProjectionClass::Unknown
            : (projectionId == 1
                ? PassPolicy::ProjectionClass::Perspective3D
                : PassPolicy::ProjectionClass::Orthographic2D);
        const auto expected =
            (!gameplay || projection != PassPolicy::ProjectionClass::Perspective3D)
            ? PassPolicy::FixedFunctionStereoPolicy::NonWorld
            : (depthTest
                ? PassPolicy::FixedFunctionStereoPolicy::WorldStereo
                : PassPolicy::FixedFunctionStereoPolicy::SkyRotationOnly);
        return PassPolicy::ClassifyFixedFunctionStereo(
            projection, gameplay, depthTest) == expected;
    }

    constexpr bool CheckRenderSemanticCase(unsigned id) noexcept
    {
        const unsigned targetId = id % 3u;
        const unsigned projectionId = (id / 3u) % 3u;
        const auto target = targetId == 0
            ? PassPolicy::PoseInjectionPolicy::InternalStereo
            : (targetId == 1
                ? PassPolicy::PoseInjectionPolicy::MainBackbuffer
                : PassPolicy::PoseInjectionPolicy::AuxiliaryStock);
        const auto projection = projectionId == 0
            ? PassPolicy::ProjectionClass::Unknown
            : (projectionId == 1
                ? PassPolicy::ProjectionClass::Perspective3D
                : PassPolicy::ProjectionClass::Orthographic2D);
        PassPolicy::RenderSemantic expected = PassPolicy::RenderSemantic::Unknown;
        if (target == PassPolicy::PoseInjectionPolicy::InternalStereo)
            expected = PassPolicy::RenderSemantic::InternalStereo;
        else if (target != PassPolicy::PoseInjectionPolicy::MainBackbuffer)
            expected = PassPolicy::RenderSemantic::Auxiliary;
        else if (projection == PassPolicy::ProjectionClass::Perspective3D)
            expected = PassPolicy::RenderSemantic::World3D;
        else if (projection == PassPolicy::ProjectionClass::Orthographic2D)
            expected = PassPolicy::RenderSemantic::ScreenSpace2D;
        return PassPolicy::ClassifyRenderSemantic(target, projection) == expected;
    }

    constexpr bool CheckMatrixCase(unsigned id) noexcept
    {
        if (id < 256u)
            return CheckDrawReplayCase(id);
        if (id < 288u)
            return CheckEffectCase(id - 256u);
        if (id < 300u)
            return CheckFixedFunctionCase(id - 288u);
        if (id < 309u)
            return CheckRenderSemanticCase(id - 300u);

        // Remaining ids deliberately recycle the policy families with a
        // different deterministic mapping to guard refactor call-site drift.
        if (id < 336u)
            return CheckDrawReplayCase((id * 73u) & 0xFFu);
        if (id < 352u)
            return CheckEffectCase((id * 11u) & 0x1Fu);
        return CheckDrawReplayCase((id * 151u) & 0xFFu);
    }

    static_assert(CheckMatrixCase(0));
    static_assert(CheckMatrixCase(1));
    static_assert(CheckMatrixCase(2));
    static_assert(CheckMatrixCase(3));
    static_assert(CheckMatrixCase(4));
    static_assert(CheckMatrixCase(5));
    static_assert(CheckMatrixCase(6));
    static_assert(CheckMatrixCase(7));
    static_assert(CheckMatrixCase(8));
    static_assert(CheckMatrixCase(9));
    static_assert(CheckMatrixCase(10));
    static_assert(CheckMatrixCase(11));
    static_assert(CheckMatrixCase(12));
    static_assert(CheckMatrixCase(13));
    static_assert(CheckMatrixCase(14));
    static_assert(CheckMatrixCase(15));
    static_assert(CheckMatrixCase(16));
    static_assert(CheckMatrixCase(17));
    static_assert(CheckMatrixCase(18));
    static_assert(CheckMatrixCase(19));
    static_assert(CheckMatrixCase(20));
    static_assert(CheckMatrixCase(21));
    static_assert(CheckMatrixCase(22));
    static_assert(CheckMatrixCase(23));
    static_assert(CheckMatrixCase(24));
    static_assert(CheckMatrixCase(25));
    static_assert(CheckMatrixCase(26));
    static_assert(CheckMatrixCase(27));
    static_assert(CheckMatrixCase(28));
    static_assert(CheckMatrixCase(29));
    static_assert(CheckMatrixCase(30));
    static_assert(CheckMatrixCase(31));
}
