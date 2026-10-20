#include "../src/vr/d3d11/native_sm3_constant_codegen.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <string>
int main() {
    using namespace outrun::vr::dx11;
    std::string condition;
    assert(native_sm3_bool_reference(0u, false, condition));
    assert(condition == "(r283_live_b[0].x != 0u)");
    assert(native_sm3_bool_reference(15u, true, condition));
    assert(condition == "r283_b15");
    assert(!native_sm3_bool_reference(16u, false, condition));
    std::string header;
    append_native_sm3_live_bool_declaration(header);
    assert(header.find("register(b2)") != std::string::npos);
    assert(header.find("uint4 r283_live_b[16]") != std::string::npos);
    std::array<std::uint32_t, 16> values{};
    values[0] = 1;
    values[3] = 0xffffffffu;
    values[15] = 42;
    const auto payload = native_sm3_live_bool_payload(values);
    assert(payload.size() == 64u);
    assert(payload[0] == 1 && payload[4] == 0);
    assert(payload[12] == 1 && payload[60] == 1);
    for (unsigned i = 0; i < 16u; ++i) {
        assert(payload[i * 4u] == (values[i] != 0u ? 1u : 0u));
        assert(payload[i * 4u + 1u] == 0u);
        assert(payload[i * 4u + 2u] == 0u);
        assert(payload[i * 4u + 3u] == 0u);
    }
}
