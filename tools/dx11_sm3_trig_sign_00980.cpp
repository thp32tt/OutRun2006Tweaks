#include "../src/vr/d3d11/native_sm3_trig_sign_opcode.hpp"
#include <cassert>
using namespace outrun::vr::dx11;
constexpr auto sc3v = native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::SineCosine, 3u, true);
constexpr auto sc3p = native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::SineCosine, 3u, false);
constexpr auto sc2v = native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::SineCosine, 2u, true);
constexpr auto sc2p = native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::SineCosine, 2u, false);
constexpr auto sgn3v = native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::Sign, 3u, true);
static_assert(sc3v.valid && sc3v.sourceCount == 1u &&
              !sc3v.scratchDestinations);
static_assert(sc3p.valid && sc3p.sourceCount == 1u);
static_assert(sc2v.valid && sc2v.sourceCount == 3u);
static_assert(sc2p.valid && sc2p.sourceCount == 3u);
static_assert(sgn3v.valid && sgn3v.sourceCount == 3u &&
              sgn3v.scratchDestinations);
static_assert(!native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::Sign, 3u, false).valid);
constexpr auto sgn2v = native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::Sign, 2u, true);
static_assert(sgn2v.valid && sgn2v.sourceCount == 3u &&
              sgn2v.scratchDestinations);
static_assert(!native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::SineCosine, 1u, true).valid);
static_assert(!native_sm3_trig_sign_operand_plan(
    NativeSm3TrigSignOpcode::SineCosine, 4u, false).valid);
int main() {
    assert(sgn3v.sourceCount == 3u);
    assert(sc3v.sourceCount != sc2v.sourceCount);
}
