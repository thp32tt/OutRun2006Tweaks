#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include "native_sm3_address_codegen.hpp"
using namespace outrun::vr::dx11;
static std::uint32_t bits(float value) {
    std::uint32_t out = 0;
    std::memcpy(&out, &value, sizeof(out));
    return out;
}
int main() {
    unsigned addr = 777u, index = 777u;
    assert(native_sm3_static_mova_address(bits(4.0f), 0u, addr) && addr == 4u);
    assert(native_sm3_static_address_const_index(219u, addr, 224u, index) &&
           index == 223u);
    assert(!native_sm3_static_address_const_index(220u, addr, 224u, index));
    assert(native_sm3_static_address_const_index(220u, addr, 256u, index) &&
           index == 224u);
    assert(native_sm3_static_mova_address(bits(-3.0f), 1u, addr) && addr == 3u);
    assert(native_sm3_static_mova_address(bits(255.0f), 0u, addr) && addr == 255u);
    assert(!native_sm3_static_address_const_index(1u, addr, 256u, index));
    assert(!native_sm3_static_mova_address(bits(2.5f), 0u, addr));
    assert(!native_sm3_static_mova_address(bits(-2.0f), 0u, addr));
    assert(!native_sm3_static_mova_address(bits(256.0f), 0u, addr));
    assert(!native_sm3_static_mova_address(bits(3.0f), 2u, addr));
    assert(!native_sm3_static_mova_address(bits(std::numeric_limits<float>::infinity()),0u,addr));
    assert(!native_sm3_static_mova_address(bits(std::numeric_limits<float>::quiet_NaN()),0u,addr));
    assert(!native_sm3_static_address_const_index(0u, 0u, 0u, index));
    assert(!native_sm3_static_address_const_index(0u, 0u, 257u, index));
    return 0;
}
