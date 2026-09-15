#pragma once

#include <cstdint>

// Explicit VR render-pass policy shared by the D3D9 stereo and renderer-pose
// hardening layers. The design follows the same conservative principle used by
// mature emulator VR implementations: classify each pass first, then choose the
// least invasive rendering action. This file intentionally contains no D3D9
// state access so the policy remains deterministic and compile-time testable.
//
// Emulator review retained as behavior/design guidance only (no source copied):
// - PPSSPP: distinguish 3D geometry from flat/screen-space geometry before
//   applying headset transforms.
// - Dolphin: treat perspective and orthographic projection as first-class,
//   different renderer states; camera transforms belong to perspective draws.
// - PCSX2: require several corroborating render-state signals rather than one
//   heuristic before classifying a draw specially.
// - RPCS3: preserve explicit frame ownership; OutRun keeps one immutable pose
//   until Present and resets the ownership boundary only after Present.
//
// OutRun-specific rule: only a perspective draw targeting the real main
// backbuffer may receive the HMD WVP. Auxiliary/reflection/shadow targets and
// orthographic/screen-space draws keep stock matrices, while MRT/query hazards
// are classified single-execution rather than replayed per eye.
namespace OutRunVR::PassPolicy
{
    enum class PoseInjectionPolicy : std::uint8_t
    {
        InternalStereo,
        MainBackbuffer,
        AuxiliaryStock
    };

    constexpr PoseInjectionPolicy ClassifyPoseInjection(
        bool internalStereo,
        bool mainBackbuffer,
        bool auxiliaryRenderTargetActive) noexcept
    {
        if (internalStereo)
            return PoseInjectionPolicy::InternalStereo;
        if (mainBackbuffer && !auxiliaryRenderTargetActive)
            return PoseInjectionPolicy::MainBackbuffer;
        return PoseInjectionPolicy::AuxiliaryStock;
    }

    constexpr bool AllowsPoseInjection(PoseInjectionPolicy policy) noexcept
    {
        return policy == PoseInjectionPolicy::MainBackbuffer;
    }

    // D3DX perspective matrices used by OutRun have |m34| == 1 and m44 == 0;
    // orthographic matrices have m34 == 0 and |m44| == 1.  Classify only these
    // structural terms so FOV/aspect/near/far changes cannot turn UI into world
    // geometry. Unknown signatures fail closed to the stock game matrix.
    enum class ProjectionClass : std::uint8_t
    {
        Unknown,
        Perspective3D,
        Orthographic2D
    };

    constexpr float Abs(float value) noexcept
    {
        return value < 0.0f ? -value : value;
    }

    constexpr bool Near(float value, float expected, float epsilon = 0.05f) noexcept
    {
        return Abs(value - expected) <= epsilon;
    }

    constexpr ProjectionClass ClassifyProjectionSignature(
        float m34, float m44) noexcept
    {
        // Accept either handedness/sign convention for the perspective divide;
        // OutRun itself is RH and normally supplies m34=-1, m44=0.
        if (Near(Abs(m34), 1.0f) && Near(m44, 0.0f))
            return ProjectionClass::Perspective3D;
        if (Near(m34, 0.0f) && Near(Abs(m44), 1.0f))
            return ProjectionClass::Orthographic2D;
        return ProjectionClass::Unknown;
    }

    // Multi-signal scene semantics: target identity and projection semantics
    // must agree before a draw is allowed into the head-tracked world path.
    // This is intentionally fail-closed: an unknown main-backbuffer projection
    // remains stock until runtime evidence proves it belongs to 3D world space.
    enum class RenderSemantic : std::uint8_t
    {
        InternalStereo,
        Auxiliary,
        World3D,
        ScreenSpace2D,
        Unknown
    };

    constexpr RenderSemantic ClassifyRenderSemantic(
        PoseInjectionPolicy targetPolicy,
        ProjectionClass projectionClass) noexcept
    {
        if (targetPolicy == PoseInjectionPolicy::InternalStereo)
            return RenderSemantic::InternalStereo;
        if (targetPolicy != PoseInjectionPolicy::MainBackbuffer)
            return RenderSemantic::Auxiliary;
        if (projectionClass == ProjectionClass::Perspective3D)
            return RenderSemantic::World3D;
        if (projectionClass == ProjectionClass::Orthographic2D)
            return RenderSemantic::ScreenSpace2D;
        return RenderSemantic::Unknown;
    }

    constexpr bool AllowsWorldStereo(RenderSemantic semantic) noexcept
    {
        return semantic == RenderSemantic::World3D;
    }

    enum class DrawReplayPolicy : std::uint8_t
    {
        Legacy,
        ForcedMonoShadow,
        UnsafeSingleExecution
    };

    constexpr DrawReplayPolicy ClassifyDrawReplay(
        bool gameDevice,
        bool internalStereo,
        bool mainBackbuffer,
        bool forceMonoShadow,
        bool stereoWanted,
        bool stereoSeeded,
        bool unsafeMrt,
        bool unsafeOcclusion) noexcept
    {
        if (!gameDevice || internalStereo || !mainBackbuffer)
            return DrawReplayPolicy::Legacy;
        if (forceMonoShadow)
            return DrawReplayPolicy::ForcedMonoShadow;
        if (stereoWanted && stereoSeeded && (unsafeMrt || unsafeOcclusion))
            return DrawReplayPolicy::UnsafeSingleExecution;
        return DrawReplayPolicy::Legacy;
    }

    // Compile-time policy invariants. These deliberately encode the safety
    // contract rather than individual hook implementation details.
    static_assert(ClassifyPoseInjection(false, true, false) ==
        PoseInjectionPolicy::MainBackbuffer);
    static_assert(ClassifyPoseInjection(false, true, true) ==
        PoseInjectionPolicy::AuxiliaryStock);
    static_assert(ClassifyPoseInjection(true, true, false) ==
        PoseInjectionPolicy::InternalStereo);

    static_assert(ClassifyProjectionSignature(-1.0f, 0.0f) ==
        ProjectionClass::Perspective3D);
    static_assert(ClassifyProjectionSignature(1.0f, 0.0f) ==
        ProjectionClass::Perspective3D);
    static_assert(ClassifyProjectionSignature(0.0f, 1.0f) ==
        ProjectionClass::Orthographic2D);
    static_assert(ClassifyProjectionSignature(0.25f, 0.25f) ==
        ProjectionClass::Unknown);

    static_assert(ClassifyRenderSemantic(
        PoseInjectionPolicy::MainBackbuffer, ProjectionClass::Perspective3D) ==
        RenderSemantic::World3D);
    static_assert(ClassifyRenderSemantic(
        PoseInjectionPolicy::MainBackbuffer, ProjectionClass::Orthographic2D) ==
        RenderSemantic::ScreenSpace2D);
    static_assert(ClassifyRenderSemantic(
        PoseInjectionPolicy::AuxiliaryStock, ProjectionClass::Perspective3D) ==
        RenderSemantic::Auxiliary);
    static_assert(!AllowsWorldStereo(ClassifyRenderSemantic(
        PoseInjectionPolicy::MainBackbuffer, ProjectionClass::Unknown)));

    static_assert(ClassifyDrawReplay(true, false, true, false, true, true, true, false) ==
        DrawReplayPolicy::UnsafeSingleExecution);
    static_assert(ClassifyDrawReplay(true, false, true, false, true, false, true, true) ==
        DrawReplayPolicy::Legacy);
    static_assert(ClassifyDrawReplay(true, false, true, true, true, true, false, false) ==
        DrawReplayPolicy::ForcedMonoShadow);
    static_assert(ClassifyDrawReplay(true, false, false, false, true, true, true, true) ==
        DrawReplayPolicy::Legacy);
}
