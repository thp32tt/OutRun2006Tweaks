#pragma once

// R30 submits the original game's left draw before private right-eye work.
// A failed D3D9 PROJECTION/stream/index restore means the game may no longer
// have its original bindings, even if the native draw returned D3D_OK.
// Do not report a successful physical transaction or retry its alpha draw.
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
    }
}
