#include "../src/vr/d3d11/native_sm3_repeat_flow.hpp"
#include <array>
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    std::array<int, 64> vs{}, ps{};
    vs[2u * 4u] = 7;
    ps[5u * 4u] = 16;
    assert(native_sm3_live_repeat_payload_valid(vs, 1u << 2u));
    assert(native_sm3_live_repeat_payload_valid(ps, 1u << 5u));
    assert(native_sm3_live_repeat_payload_valid(vs, 0u));
    assert(!native_sm3_live_repeat_payload_valid(vs, 1u << 1u));
    vs[2u * 4u] = -1;
    assert(!native_sm3_live_repeat_payload_valid(vs, 1u << 2u));
    vs[2u * 4u] = 17;
    assert(!native_sm3_live_repeat_payload_valid(vs, 1u << 2u));
    std::string hlsl;
    assert(append_native_sm3_live_repeat_begin(hlsl, 2u, 4u));
    assert(hlsl.find("r283_i[2].x") != std::string::npos);
    assert(hlsl.find("r283_repeat_4") != std::string::npos);
    const std::string original = hlsl;
    assert(!append_native_sm3_live_repeat_begin(hlsl, 16u, 5u));
    assert(!append_native_sm3_live_repeat_begin(hlsl, 2u, 512u));
    assert(hlsl == original);
    assert(append_native_sm3_repeat_begin(hlsl, 3u, 5u));
    assert(hlsl.find(" < 3;") != std::string::npos);
    NativeSm3StructuredFlow::Temps temps{};
    NativeSm3StructuredFlow::Outputs outputs{};
    temps[0] = 0x0fu;
    NativeSm3StructuredFlow flow;
    assert(flow.begin_live_repeat(temps, outputs));
    temps[1] = 0x0fu;
    assert(flow.record_break());
    assert(flow.end_repeat(temps, outputs));
    assert(temps[0] == 0x0fu && temps[1] == 0u);
    assert(flow.empty());
    NativeSm3StructuredFlow excessive;
    assert(excessive.begin_live_repeat(temps, outputs));
    assert(!excessive.begin_live_repeat(temps, outputs));
}
