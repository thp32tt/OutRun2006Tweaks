#include "../src/vr/d3d11/native_sm3_conditional_flow.hpp"
#include <cassert>

int main() {
    using outrun::vr::dx11::NativeSm3ConditionalFlow;
    using outrun::vr::dx11::native_sm3_ifc_comparison;
    for (unsigned i = 1u; i <= 6u; ++i)
        assert(native_sm3_ifc_comparison(i) != nullptr);
    assert(native_sm3_ifc_comparison(0u) == nullptr);
    assert(native_sm3_ifc_comparison(7u) == nullptr);

    NativeSm3ConditionalFlow flow;
    NativeSm3ConditionalFlow::Temps t{};
    NativeSm3ConditionalFlow::Outputs o{};
    t[0] = 1u;
    assert(!flow.otherwise(t, o) && !flow.end(t, o));
    assert(flow.begin(t, o));
    t[0] = 3u;  // x existed, y written only in then-arm
    o[0] = 15u;
    assert(flow.otherwise(t, o));
    assert(t[0] == 1u && o[0] == 0u);
    assert(!flow.otherwise(t, o));
    t[0] = 5u;  // x existed, z written only in else-arm
    o[0] = 15u;
    assert(flow.end(t, o));
    assert(flow.empty() && t[0] == 1u && o[0] == 15u);
    assert(flow.begin(t, o));
    t[1] = 15u;
    o[1] = 15u;
    assert(flow.end(t, o));
    assert(t[1] == 0u && o[1] == 0u);
    assert(flow.begin(t, o));
    assert(flow.begin(t, o));
    t[2] = 15u;
    assert(flow.otherwise(t, o));
    t[2] = 7u;
    assert(flow.end(t, o));
    assert(t[2] == 7u);
    assert(flow.end(t, o));
    assert(t[2] == 0u);
    assert(flow.empty());
    for (unsigned i = 0u; i < 8u; ++i) assert(flow.begin(t, o));
    assert(!flow.begin(t, o));
    for (unsigned i = 0u; i < 8u; ++i) assert(flow.end(t, o));
    return 0;
}
