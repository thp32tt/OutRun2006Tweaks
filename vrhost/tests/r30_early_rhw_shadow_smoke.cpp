#include "vr/d3d9/r30_early_rhw_shadow.hpp"

#include <cstdio>
#include <cstdint>

// A Release/NDEBUG build must not erase regression checks.
#define CHECK(condition) do { if (!(condition)) { \
    std::fprintf(stderr, "R30 early RHW shadow check failed at line %d\\n", __LINE__); \
    return 1; \
} } while (false)

int main()
{
    using namespace OutRunVR::R30EarlyRhwShadow;
    constexpr std::uint32_t positionMask = 0x400eu; // D3DFVF_POSITION_MASK
    constexpr std::uint32_t xyzrhw = 0x0004u; // D3DFVF_XYZRHW
    constexpr std::uint32_t xyz = 0x0002u; // D3DFVF_XYZ
    constexpr std::uint32_t tex1 = 0x0100u; // D3DFVF_TEX1
    static_assert(ExplicitXyzrhwFvf(xyzrhw, positionMask, xyzrhw));
    static_assert(ExplicitXyzrhwFvf(xyzrhw | tex1, positionMask, xyzrhw));
    static_assert(!ExplicitXyzrhwFvf(xyz, positionMask, xyzrhw));
    static_assert(!ExplicitXyzrhwFvf(0u, positionMask, xyzrhw));
    static_assert(!ExplicitXyzrhwFvf(0x4002u, positionMask, xyzrhw));

    // Created exact RHW FVF => write before first Draw is eligible.
    bool firstDrawArmed = false;
    const bool exactRhw = ExplicitXyzrhwFvf(
        xyzrhw | tex1, positionMask, xyzrhw);
    CHECK(ObserveVertexLock(firstDrawArmed, exactRhw, false, true, true));

    // Before the first Draw, unrelated 3D buffers and declarations stay
    // unobserved. No extra world memcpy work, no stale unknown shadow.
    CHECK(!ObserveVertexLock(false, false, false, true, true));
    CHECK(!ObserveVertexLock(false, false, false, true, true));
    CHECK(!ObserveVertexLock(false, true, true, true, true));
    CHECK(!ObserveVertexLock(false, true, false, false, true));
    CHECK(!ObserveVertexLock(false, true, false, true, false));

    // After the first eligible Draw, the established lazy path still works
    // for previously unrecognized buffers, unless overlay/Lock invalid.
    CHECK(ObserveVertexLock(true, false, false, true, true));
    CHECK(!ObserveVertexLock(true, false, true, true, true));
    CHECK(!ObserveVertexLock(true, false, false, false, true));
    CHECK(!ObserveVertexLock(true, false, false, true, false));
    return 0;
}
