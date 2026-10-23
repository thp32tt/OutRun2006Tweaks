#include "native_sm3_subroutine_expansion.hpp"
#include <cassert>
#include <cstdint>
#include <vector>

using outrun::vr::dx11::native_sm3_expand_subroutines;

struct Instruction {
    std::uint32_t opcode{};
    std::uint32_t instructionToken{};
    std::vector<std::uint32_t> operandTokens{};
    unsigned payload{};
};
constexpr std::uint32_t draw = 1u, call = 2u, callnz = 3u, label = 4u;
constexpr std::uint32_t ret = 5u, ifop = 7u, endifop = 8u, def = 9u;
Instruction emit(unsigned value) { return {draw, draw, {}, value}; }
Instruction marker(unsigned op, unsigned id) {
    return {op, op, {0x80000000u | id}, 0u};
}
Instruction guarded(unsigned id, unsigned boolReg) {
    return {callnz, callnz, {0x80000000u | id, 0x80000100u | boolReg}, 0u};
}
Instruction done() { return {ret, ret, {}, 0u}; }
bool lower(const std::vector<Instruction>& in, std::vector<Instruction>& out) {
    return native_sm3_expand_subroutines(
        in, call, callnz, label, ret, ifop, endifop,
        [](std::uint32_t token, unsigned& id) {
            if ((token & 0x80000000u) == 0u ||
                (token & 0x7ffff800u) != 0u) return false;
            id = token & 0x7ffu;
            return true;
        },
        [](std::uint32_t token) {
            return (token & 0xfffffff0u) == 0x80000100u;
        },
        [](std::uint32_t op) { return op != def; }, out);
}
int main() {
    std::vector<Instruction> out;
    // Both source-derived dynamic b# and shader-local DEFB take this path;
    // downstream live SM3 IF still decides whether to issue the body.
    const std::vector<Instruction> game{
        emit(10), guarded(1, 3), emit(40), done(),
        marker(label, 1), emit(20), marker(call, 2), emit(25), done(),
        marker(label, 2), emit(30), done()
    };
    assert(lower(game, out));
    assert(out.size() == 7u);
    assert(out[0].payload == 10u);
    assert(out[1].opcode == ifop && out[1].instructionToken == ((1u << 24u) | ifop));
    assert(out[1].operandTokens.size() == 1u &&
           out[1].operandTokens[0] == 0x80000103u);
    assert(out[2].payload == 20u && out[3].payload == 30u &&
           out[4].payload == 25u);
    assert(out[5].opcode == endifop &&
           out[5].instructionToken == endifop &&
           out[5].operandTokens.empty());
    assert(out[6].payload == 40u);

    // A conditional nested inside another subroutine emits its own IF
    // without turning the false branch into an unconditional GPU write.
    auto nested = game;
    nested[6] = guarded(2, 4);
    assert(lower(nested, out) && out.size() == 9u);
    assert(out[3].opcode == ifop && out[3].operandTokens[0] == 0x80000104u);
    assert(out[5].opcode == endifop && out[7].opcode == endifop);
    // Same label can be called twice with distinct independent b# inputs.
    auto repeated = game;
    repeated.insert(repeated.begin() + 2, guarded(2, 1));
    assert(lower(repeated, out) && out.size() == 10u);
    assert(out[6].opcode == ifop && out[6].operandTokens[0] == 0x80000101u);

    auto bad = game;
    bad[1].operandTokens.pop_back();
    assert(!lower(bad, out) && out.empty());
    bad = game;
    bad[1].operandTokens[1] = 0x80000120u;
    assert(!lower(bad, out) && out.empty());
    bad = game;
    bad[1].operandTokens[0] = 0x80000007u;
    assert(!lower(bad, out) && out.empty());
    bad = game;
    bad[1].instructionToken |= 0x10000000u; // predicated/invalid CALLNZ
    assert(!lower(bad, out) && out.empty());
    bad = game;
    bad[6] = guarded(1, 1); // recursive cycle
    assert(!lower(bad, out) && out.empty());
    bad = game;
    bad[5].opcode = def; // illegal DEFB/DEF in subroutine body
    assert(!lower(bad, out) && out.empty());
    // Neither malformed boolean reads nor graph size overflow can enable
    // a native GPU Draw; retain original D3D9Ex submission.
    bad = game;
    bad.insert(bad.begin() + 1, 510u, emit(99));
    assert(!lower(bad, out) && out.empty());
    return 0;
}
