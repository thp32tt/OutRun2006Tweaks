#include <cassert>
#include <cstring>
#include <initializer_list>
#include "native_sm3_interface_channels.hpp"
using namespace outrun::vr::dx11;
int main() {
    for (const unsigned usage : {1u, 2u, 3u, 5u, 6u, 7u, 10u}) {
        const char* label = native_sm3_interface_semantic(usage, true, false, 0u);
        assert(label && std::strlen(label) > 0);
    }
    assert(std::strcmp(native_sm3_interface_semantic(1u, true, false, 2u), "BLENDWEIGHT") == 0);
    assert(std::strcmp(native_sm3_interface_semantic(6u, true, false, 0u), "TANGENT") == 0);
    assert(std::strcmp(native_sm3_interface_semantic(7u, true, false, 0u), "BINORMAL") == 0);
    assert(std::strcmp(native_sm3_interface_semantic(0u, true, true, 0u), "SV_Position") == 0);
    assert(native_sm3_interface_semantic(0u, true, true, 1u) == nullptr);
    assert(native_sm3_interface_semantic(6u, false, false, 0u) == nullptr);
    assert(native_sm3_interface_semantic(1u, true, true, 0u) == nullptr);
    assert(native_sm3_interface_semantic(5u, false, false, 3u) != nullptr);
    assert(native_sm3_interface_semantic(10u, false, false, 0u) != nullptr);
    assert(native_sm3_interface_semantic(9u, true, false, 0u) == nullptr);
    assert(native_sm3_interface_semantic(5u, true, false, 16u) == nullptr);
    assert(native_sm3_declared_components_cover(0x3u, 0x1u));
    assert(native_sm3_declared_components_cover(0x3u, 0x3u));
    assert(!native_sm3_declared_components_cover(0x3u, 0x4u));
    assert(!native_sm3_declared_components_cover(0x3u, 0x7u));
    assert(!native_sm3_declared_components_cover(0u, 0x1u));
    assert(!native_sm3_declared_components_cover(0x3u, 0x10u));
    assert(native_sm3_declared_output_complete(0x3u, 0x3u));
    assert(native_sm3_declared_output_complete(0xfu, 0xfu));
    assert(!native_sm3_declared_output_complete(0x3u, 0x1u));
    assert(!native_sm3_declared_output_complete(0x3u, 0xfu));
    return 0;
}
