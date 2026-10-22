#include "../src/vr/d3d11/native_sm3_nop.hpp"
#include <cassert>

using outrun::vr::dx11::native_sm3_nop_admissible;

static_assert(native_sm3_nop_admissible(0u, 0u));
static_assert(!native_sm3_nop_admissible(0u, 1u));
static_assert(!native_sm3_nop_admissible(0x01000000u, 0u)); // length bits
static_assert(!native_sm3_nop_admissible(0x10000000u, 0u)); // predicate
static_assert(!native_sm3_nop_admissible(1u, 0u)); // MOV != NOP

int main() {
    assert(native_sm3_nop_admissible(0u, 0u));
    assert(!native_sm3_nop_admissible(0u, 2u));
    assert(!native_sm3_nop_admissible(0x80000000u, 0u));
}
