#pragma once

// R84 R30/R33 submit the original game's native left draw before private
// right-eye work. Failed PROJECTION/stream/index, RT/depth/viewport or c64
// restoration leaves the game's GPU state unsafe even if LEFT succeeded.
// Never hide the restore error, or submit the original alpha draw again.
namespace OutRunVR::R30StateRestore
{
    template<class Result>
    constexpr Result ResultAfterRestore(
        Result drawResult, bool stateRestored, Result restoreError) noexcept
    {
        // Preserve a genuine original GPU error. Otherwise propagate the
        // restore failure rather than silently returning the left-eye OK.
        return stateRestored || drawResult < static_cast<Result>(0)
            ? drawResult : restoreError;
    }

    namespace Regression
    {
        static_assert(ResultAfterRestore(0, true, -1) == 0,
            "Native successful stereo and complete restore must stay successful");
        static_assert(ResultAfterRestore(0, false, -1) == -1,
            "Lost original game PROJECTION/stream/indices must fail closed");
        static_assert(ResultAfterRestore(-2, true, -1) == -2,
            "Native GPU draw failures must keep their HRESULT");
        static_assert(ResultAfterRestore(-2, false, -1) == -2,
            "A restore failure must not mask the original GPU failure");
        static_assert(ResultAfterRestore(1, false, -1) == -1,
            "Nonnegative D3D9 success statuses must not hide restore failures");
        // R30 XYZRHW, R33 fast-world/HUD and source-change c64 rollback
        // share the same original-game state contract and native LEFT identity.
        static_assert(ResultAfterRestore(0, false, -3) == -3,
            "Private right-eye RT/depth/viewport rollback must propagate");
        static_assert(ResultAfterRestore(0, false, -4) == -4,
            "R33 HUD source-change c64 rollback failure must propagate");
        static_assert(ResultAfterRestore(0, true, -4) == 0,
            "Correctly restored HUD source veto must retain native LEFT success");
        static_assert(ResultAfterRestore(0, true, -3) == 0,
            "Right-eye-only Draw fault with complete restore retains native LEFT");
        static_assert(ResultAfterRestore(-5, false, -3) == -5,
            "Failed original LEFT draw HRESULT remains authoritative");
    }
}
