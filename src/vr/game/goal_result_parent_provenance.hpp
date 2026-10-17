#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// The 19 canonical OutRun 2006 result-text E8 CALLs target sub_4B9200.
// Their return addresses are source proof for the GOAL 0-99% text; unlike
// the old rva+5 midhooks, inspecting the call stack never modifies game code.
// A missing/unwindable frame MUST fail closed to the existing glyph owner.
namespace OutRunVR::GoalResult
{
    constexpr std::array<std::uintptr_t, 19> OriginalB9200CallReturns{{
        0x973AFu + 5u, 0x97422u + 5u, 0x974D0u + 5u, 0x97544u + 5u,
        0x97664u + 5u, 0x97675u + 5u, 0x9769Eu + 5u, 0x976B2u + 5u,
        0x976F4u + 5u, 0x9784Fu + 5u, 0x9787Du + 5u, 0x9788Eu + 5u,
        0x978B4u + 5u, 0x978C8u + 5u, 0x978ECu + 5u, 0x97C31u + 5u,
        0x97C57u + 5u, 0x97E47u + 5u, 0x97E6Du + 5u
    }};

    constexpr bool IsOriginalB9200ParentReturn(
        std::uintptr_t gameImageBase, std::uintptr_t returnAddress) noexcept
    {
        if (!gameImageBase || returnAddress <= gameImageBase)
            return false;
        const auto relative = returnAddress - gameImageBase;
        for (const auto knownReturn : OriginalB9200CallReturns)
            if (relative == knownReturn)
                return true;
        return false;
    }

    // Only unowned, original B9200 direct D3DX draws may carry the result
    // source across native texture-batch submission. Fail closed otherwise.
    constexpr bool CanBindDirectB9200D3DXDraw(
        bool vrEnabled, bool inGoal, bool queueActive,
        bool noCompetingProducer, bool exactParentOnStack) noexcept
    {
        return vrEnabled && inGoal && !queueActive &&
            noCompetingProducer && exactParentOnStack;
    }

    constexpr bool CheckParentReturnProvenance() noexcept
    {
        constexpr std::uintptr_t base = 0x400000u;
        for (const auto exact : OriginalB9200CallReturns)
        {
            if (!IsOriginalB9200ParentReturn(base, base + exact) ||
                IsOriginalB9200ParentReturn(base, base + exact - 1u) ||
                IsOriginalB9200ParentReturn(base, base + exact + 1u))
                return false;
        }
        return !IsOriginalB9200ParentReturn(0, base + OriginalB9200CallReturns[0]) &&
            !IsOriginalB9200ParentReturn(base, base) &&
            !IsOriginalB9200ParentReturn(base, base - 1u) &&
            !IsOriginalB9200ParentReturn(base, base + 0x989ADu + 5u) &&
            !IsOriginalB9200ParentReturn(base, base + 0xBEA5Au + 5u) &&
            !IsOriginalB9200ParentReturn(base, base + 0x2C808u + 5u);
    }
    static_assert(CheckParentReturnProvenance(),
        "GOAL source accepts exactly nineteen E8 parent returns, no adjacent instruction");
}
