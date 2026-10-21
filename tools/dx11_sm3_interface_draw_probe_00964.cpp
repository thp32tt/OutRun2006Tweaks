// Cohesive live-game SM3 shader-interface and multi-stream Draw input test.
// Portable: no GPU, D3D9 game or Quest3 required.
#include "../src/vr/d3d11/live_game_sm3_interface_capacity.hpp"
#include "../src/vr/d3d11/live_game_sm3_stream_assembly.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <vector>

int main() {
    using namespace outrun::vr::dx11;
    using namespace outrun::vr::dx11::live_game_frame;
    if (!native_sm3_interface_decl_capacity(true, 16, 12) ||
        !native_sm3_interface_decl_capacity(false, 10, 0) ||
        native_sm3_interface_decl_capacity(true, 0, 12) ||
        native_sm3_interface_decl_capacity(true, 17, 12) ||
        native_sm3_interface_decl_capacity(true, 16, 13) ||
        native_sm3_interface_decl_capacity(false, 11, 0) ||
        native_sm3_interface_decl_capacity(false, 10, 1) ||
        !native_sm3_ia_element_capacity(32) ||
        native_sm3_ia_element_capacity(33)) return 1;

    // A 12-input game-owned SM3 shader spans two genuine D3D9 streams.
    // The native Draw sees a single correctly ordered FLOAT4 IA stream.
    std::array<float, 8> primary{};
    std::array<float, 4> secondary{};
    for (unsigned i = 0; i < 8; ++i) primary[i] = i + 0.25f;
    for (unsigned i = 0; i < 4; ++i) secondary[i] = i + 100.75f;
    std::array<GameSm3StreamView, 4> streams{};
    streams[0] = {reinterpret_cast<const std::uint8_t*>(primary.data()),
                  static_cast<std::uint32_t>(primary.size() * sizeof(float)), 1u};
    streams[1] = {reinterpret_cast<const std::uint8_t*>(secondary.data()),
                  static_cast<std::uint32_t>(secondary.size() * sizeof(float)), 1u};
    std::vector<GameSm3ElementRef> declaration;
    for (unsigned i = 0; i < 12; ++i)
        declaration.push_back({static_cast<std::uint8_t>(i >= 8u),
            static_cast<std::uint16_t>((i < 8u ? i : i - 8u) * sizeof(float)), 0u});
    std::vector<std::uint8_t> packed;
    if (!game_sm3_assemble_streams(declaration, streams, 1u, packed) ||
        packed.size() != 12u * 4u * sizeof(float)) return 2;
    for (unsigned i = 0; i < 12; ++i) {
        std::array<float, 4> v{};
        std::memcpy(v.data(), packed.data() + i * 16u, 16u);
        const float expected = i < 8 ? i + 0.25f : (i - 8) + 100.75f;
        if (v[0] != expected || v[1] != 0.0f ||
            v[2] != 0.0f || v[3] != 1.0f) return 3;
    }
    // A bogus 33-element IA source must not become a partially uploaded mesh.
    auto rejected = declaration;
    for (unsigned i = 12; i < 33; ++i) rejected.push_back(declaration[i % 12]);
    auto sentinel = packed;
    if (native_sm3_ia_element_capacity(rejected.size()) ||
        game_sm3_assemble_streams(rejected, streams, 1u, packed) ||
        packed != sentinel) return 4;
    // Missing secondary stream fails closed without partial GPU input.
    streams[1].data = nullptr;
    if (game_sm3_assemble_streams(declaration, streams, 1u, packed) ||
        packed != sentinel) return 5;
    return 0;
}
