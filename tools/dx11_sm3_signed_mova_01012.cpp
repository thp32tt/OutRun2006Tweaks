// Game VS 3.0 DEF -> signed/rounded MOVA -> live D3D11 VS constant index.
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>
#include "native_sm3_constant_codegen.hpp"
using namespace outrun::vr::dx11;
static std::uint32_t bits(float v) {
    std::uint32_t b = 0u;
    std::memcpy(&b, &v, sizeof(b));
    return b;
}
int main() {
    int signedAddress = 111;
    unsigned index = 777u;
    assert(native_sm3_static_mova_address(bits(2.6f), 0u, signedAddress) &&
           signedAddress == 3);
    assert(native_sm3_static_mova_address(bits(-2.6f), 0u, signedAddress) &&
           signedAddress == -3);
    assert(native_sm3_static_address_const_index(7u, signedAddress, 256u, index) &&
           index == 4u);
    assert(!native_sm3_static_address_const_index(2u, signedAddress, 256u, index));
    assert(native_sm3_static_mova_address(bits(-254.4f), 0u, signedAddress) &&
           signedAddress == -254);
    assert(native_sm3_static_address_const_index(255u, signedAddress, 256u, index) &&
           index == 1u);
    assert(native_sm3_static_mova_address(bits(-3.4f), 1u, signedAddress) &&
           signedAddress == 3);
    assert(native_sm3_static_address_const_index(220u, signedAddress, 224u, index) &&
           index == 223u);
    assert(!native_sm3_static_address_const_index(221u, signedAddress, 224u, index));
    // Tie behavior, non-finite data, unsupported modifiers and out-of-bank
    // results never produce an artificial native game pixel.
    assert(!native_sm3_static_mova_address(bits(2.5f), 0u, signedAddress));
    assert(!native_sm3_static_mova_address(bits(-2.5f), 0u, signedAddress));
    assert(!native_sm3_static_mova_address(bits(256.0f), 0u, signedAddress));
    assert(!native_sm3_static_mova_address(bits(-256.0f), 0u, signedAddress));
    assert(!native_sm3_static_mova_address(bits(1.0f), 3u, signedAddress));
    assert(!native_sm3_static_mova_address(
        bits(std::numeric_limits<float>::quiet_NaN()), 0u, signedAddress));
    // Matrix c[base+a0+i] must use the signed offset for EVERY row.
    std::array<bool, 256> localDef{};
    std::array<std::uint16_t, 16> limits{};
    std::array<std::string, 4> rows{};
    bool live = false;
    assert(native_sm3_relative_matrix_references(
        255u, 3u, 256u, true, -3, false, 0, 0, 0,
        localDef, limits, rows, live));
    assert(live && rows[0] == "r283_c[252]" &&
           rows[1] == "r283_c[253]" && rows[2] == "r283_c[254]");
    localDef[253] = true;
    assert(native_sm3_relative_matrix_references(
        255u, 3u, 256u, true, -3, false, 0, 0, 0,
        localDef, limits, rows, live));
    assert(rows[1] == "r283_def253");
    assert(!native_sm3_relative_matrix_references(
        1u, 3u, 256u, true, -3, false, 0, 0, 0,
        localDef, limits, rows, live));
    assert(!native_sm3_relative_matrix_references(
        255u, 4u, 256u, true, -1, false, 0, 0, 0,
        localDef, limits, rows, live));
    return 0;
}
