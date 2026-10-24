// Real game ps_3_0 TEXKILL source -> native D3D11 pixel discard.
// Microsoft texkill-ps consumes TEMP.xyz; W is not required.
#include "native_sm3_fragment_codegen.hpp"
#include <cassert>
#include <string>
using namespace outrun::vr::dx11;
int main() {
    static_assert(native_sm3_texkill_ready(0u, 0x07u));
    static_assert(native_sm3_texkill_ready(31u, 0x0fu));
    static_assert(!native_sm3_texkill_ready(0u, 0x03u));
    static_assert(!native_sm3_texkill_ready(0u, 0x05u));
    static_assert(!native_sm3_texkill_ready(0u, 0x06u));
    static_assert(!native_sm3_texkill_ready(0u, 0x00u));
    static_assert(!native_sm3_texkill_ready(32u, 0x0fu));
    std::string hlsl;
    assert(append_native_sm3_texkill(hlsl, 7u, 0x07u, 33u));
    assert(hlsl == "    clip(r283_t7.xyz);\n");
    assert(hlsl.find(".w") == std::string::npos);
    const std::string exact = hlsl;
    assert(!append_native_sm3_texkill(hlsl, 7u, 0x03u, 34u));
    assert(!append_native_sm3_texkill(hlsl, 32u, 0x0fu, 35u));
    assert(!append_native_sm3_texkill(hlsl, 7u, 0x07u, 512u));
    assert(hlsl == exact);
}
