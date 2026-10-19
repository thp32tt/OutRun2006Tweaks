#include "../src/vr/d3d11/native_sm3_predicate_flow.hpp"
#include <cassert>
#include <string>
int main() {
    using namespace outrun::vr::dx11;
    NativeSm3PredicateFlow flow;
    assert(!flow.ready());
    assert(flow.begin_if());
    flow.write();
    assert(flow.ready());
    assert(flow.end_if() && !flow.ready());
    assert(flow.begin_if());
    flow.write();
    assert(flow.otherwise() && !flow.ready());
    flow.write();
    assert(flow.end_if() && flow.ready());
    assert(flow.begin_repeat());
    assert(flow.begin_if());
    assert(flow.begin_repeat());
    assert(!flow.end_if());
    assert(flow.end_repeat());
    assert(flow.otherwise());
    assert(flow.end_if());
    assert(flow.end_repeat() && flow.ready() && flow.empty());
    NativeSm3PredicateFlow fresh;
    assert(fresh.begin_repeat());
    fresh.write();
    assert(fresh.end_repeat() && !fresh.ready());
    assert(!fresh.otherwise() && !fresh.end_if() && !fresh.end_repeat());
    std::string hlsl;
    assert(!append_native_sm3_setp(hlsl, ""));
    assert(append_native_sm3_setp(hlsl, "r283_t0.x >= r283_c[1].y"));
    assert(append_native_sm3_breakp(hlsl, false));
    assert(append_native_sm3_breakp(hlsl, true));
    assert(hlsl.find("r283_p0 = (r283_t0.x >= r283_c[1].y);") != std::string::npos);
    assert(hlsl.find("if (r283_p0) break;") != std::string::npos);
    assert(hlsl.find("if (!r283_p0) break;") != std::string::npos);
    return 0;
}
