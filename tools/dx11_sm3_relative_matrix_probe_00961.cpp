#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include "native_sm3_constant_codegen.hpp"
using namespace outrun::vr::dx11;
int main() {
    std::array<bool,256> defined{};
    std::array<std::uint16_t,16> limits{};
    std::array<std::string,4> rows{};
    bool live = true;
    defined[13] = true;
    // Static shader DEF/MOVA a0.x=3 references c13..c16.
    assert(native_sm3_relative_matrix_references(
        10,4,256,true,3,false,0,0,0,defined,limits,rows,live));
    assert(rows[0] == "r283_def13" && rows[1] == "r283_c[14]" && live);
    defined[13] = false;
    assert(!native_sm3_relative_matrix_references(
        220,4,224,true,1,false,0,0,0,defined,limits,rows,live));
    // Ordinary static LOOP can move the full block, including negative aL.
    assert(native_sm3_relative_matrix_references(
        8,3,224,false,-1,false,-2,1,0,defined,limits,rows,live));
    assert(rows[0] == "r283_c[8 + r283_aL]" &&
           rows[2] == "r283_c[10 + r283_aL]" && live);
    defined[10] = true;
    auto previous = rows;
    assert(!native_sm3_relative_matrix_references(
        8,3,224,false,-1,false,-2,1,0,defined,limits,rows,live));
    assert(rows == previous);
    defined[10] = false;
    // Per-Draw dynamic LOOP: 4 rows starting at c220 leaves only aL=0.
    assert(native_sm3_relative_matrix_references(
        220,4,224,false,-1,true,0,15,2,defined,limits,rows,live));
    assert(limits[2] == 1 && rows[3] == "r283_c[223 + r283_aL]");
    assert(native_sm3_relative_matrix_references(
        218,3,224,false,-1,true,0,15,2,defined,limits,rows,live));
    assert(limits[2] == 1); // stricter pre-existing bound never widens
    defined[223] = true;
    assert(!native_sm3_relative_matrix_references(
        220,4,224,false,-1,true,0,15,2,defined,limits,rows,live));
    assert(limits[2] == 1);
    defined[223] = false;
    assert(!native_sm3_relative_matrix_references(
        220,4,224,false,-1,true,0,15,16,defined,limits,rows,live));
    assert(!native_sm3_relative_matrix_references(
        254,4,256,false,-1,true,0,15,2,defined,limits,rows,live));
    assert(!native_sm3_relative_matrix_references(
        8,3,224,false,-1,false,-9,0,0,defined,limits,rows,live));
    // An all-shader-owned static matrix is never marked as live c-buffer.
    defined[13] = true; defined[14] = true;
    assert(native_sm3_relative_matrix_references(
        13,2,256,true,0,false,0,0,0,defined,limits,rows,live));
    assert(!live && rows[0] == "r283_def13" && rows[1] == "r283_def14");
    return 0;
}
