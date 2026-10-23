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
constexpr std::uint32_t draw = 1, call = 2, callnz = 3, label = 4, ret = 5, def = 6;
Instruction emit(unsigned value) { return {draw, draw, {}, value}; }
Instruction marker(std::uint32_t op, unsigned id) {
    return {op, op, {0x80000000u | id}, 0u};
}
Instruction done() { return {ret, ret, {}, 0u}; }
bool lower(const std::vector<Instruction>& in, std::vector<Instruction>& out) {
    return native_sm3_expand_subroutines(
        in, call, callnz, label, ret,
        [](std::uint32_t token, unsigned& id) {
            if ((token & 0x80000000u) == 0u || (token & 0x7ffff800u) != 0u)
                return false;
            id = token & 0x7ffu;
            return true;
        },
        [](std::uint32_t op) { return op != def; }, out);
}
int main() {
    std::vector<Instruction> out;
    assert(lower({emit(1), emit(2)}, out));
    assert(out.size() == 2u && out[0].payload == 1u);
    const std::vector<Instruction> nested{
        emit(10), marker(call, 1), emit(40), done(),
        marker(label, 1), emit(20), marker(call, 2), done(),
        marker(label, 2), emit(30), done()};
    assert(lower(nested, out));
    assert(out.size() == 4u);
    assert(out[0].payload == 10u && out[1].payload == 20u &&
           out[2].payload == 30u && out[3].payload == 40u);
    // A second CALL executes the body twice; no synthetic persistent state.
    auto repeated = nested;
    repeated.insert(repeated.begin() + 3, marker(call, 2));
    assert(lower(repeated, out) && out.size() == 5u &&
           out[3].payload == 30u);
    auto bad = nested;
    bad[1] = marker(callnz, 1);
    assert(!lower(bad, out));
    bad = nested;
    bad[1] = marker(call, 3); // no such label
    assert(!lower(bad, out));
    bad = nested;
    bad[6] = marker(call, 1); // recursion/cycle
    assert(!lower(bad, out));
    bad = nested;
    bad[8] = marker(label, 1); // duplicate label
    assert(!lower(bad, out));
    bad = nested;
    bad[3] = emit(99); // no top-level RET
    assert(!lower(bad, out));
    bad = nested;
    bad[1].operandTokens = {0}; // malformed register token
    assert(!lower(bad, out));
    bad = nested;
    bad[5] = {def, def, {}, 0u}; // no unscoped DEF in inline body
    assert(!lower(bad, out));
    bad = nested;
    bad[10] = emit(50); // missing subroutine RET
    assert(!lower(bad, out));
    return 0;
}
