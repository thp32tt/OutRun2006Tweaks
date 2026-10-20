#include <array>
#include <cassert>
#include <cstdint>
#include <string>
#include "native_sm3_repeat_flow.hpp"
using namespace outrun::vr::dx11;
int main() {
    unsigned count = 0;
    int first = 0, step = 0;
    assert(native_sm3_static_loop_parameters({4u, 5u, 2u, 0u}, count, first, step));
    assert(count == 4u && first == 5 && step == 2);
    assert(native_sm3_static_loop_parameters({3u, 8u, static_cast<std::uint32_t>(-2), 0u}, count, first, step));
    assert(first == 8 && step == -2);
    assert(!native_sm3_static_loop_parameters({17u, 0u, 1u, 0u}, count, first, step));
    assert(!native_sm3_static_loop_parameters({4u, 0u, static_cast<std::uint32_t>(-1), 0u}, count, first, step));
    assert(!native_sm3_static_loop_parameters({2u, 254u, 2u, 0u}, count, first, step));
    assert(!native_sm3_static_loop_parameters({2u, 0u, 1u, 1u}, count, first, step));
    std::array<int, 64> payload{};
    payload[0] = 3; payload[1] = 2; payload[2] = 4;
    assert(native_sm3_live_loop_payload_valid(payload, 1u));
    payload[1] = 255; assert(!native_sm3_live_loop_payload_valid(payload, 1u));
    payload[1] = 2; payload[3] = 1;
    assert(!native_sm3_live_loop_payload_valid(payload, 1u));
    payload[3] = 0; payload[0] = 0;
    assert(!native_sm3_live_loop_payload_valid(payload, 1u));
    assert(native_sm3_live_loop_payload_valid(payload, 0u));
    NativeSm3StructuredFlow flow;
    NativeSm3StructuredFlow::Temps temps{};
    NativeSm3StructuredFlow::Outputs outputs{};
    assert(flow.begin_loop(3u, temps, outputs, false));
    temps[1] = 15u;
    assert(flow.end_loop(temps, outputs));
    assert(temps[1] == 15u);
    assert(flow.begin_loop(3u, temps, outputs, false));
    temps[2] = 15u;
    assert(flow.record_break());
    assert(flow.end_loop(temps, outputs));
    assert(temps[2] == 0u);
    assert(flow.begin_loop(16u, temps, outputs, true));
    temps[3] = 15u;
    assert(flow.end_loop(temps, outputs));
    assert(temps[3] == 0u && flow.empty());
    assert(!flow.record_break());
    std::string hlsl;
    assert(append_native_sm3_loop_begin(hlsl, 1u, 3u, 2, -1, false, 0u));
    assert(hlsl.find("r283_aL = 2") != std::string::npos);
    assert(hlsl.find("r283_loop_1") != std::string::npos);
    assert(append_native_sm3_loop_begin(hlsl, 2u, 16u, 0, 1, true, 5u));
    assert(hlsl.find("r283_i[5].x") != std::string::npos);
    assert(hlsl.find("r283_i[5].y") != std::string::npos);
    assert(hlsl.find("r283_i[5].z") != std::string::npos);
    assert(!append_native_sm3_loop_begin(hlsl, 1u, 17u, 0, 1, false, 0u));
    assert(!append_native_sm3_loop_begin(hlsl, 1u, 16u, 0, 1, true, 16u));
    return 0;
}
