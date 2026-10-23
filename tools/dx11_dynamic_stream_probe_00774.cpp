#include "../src/vr/d3d11/native_game_dynamic_stream.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
using outrun::vr::dx11::live_game_frame::game_native_copy_dynamic_stream;
int main() {
    std::array<std::uint8_t, 32> gpu{};
    std::array<std::uint8_t, 12> menu{};
    std::array<std::uint8_t, 12> race{};
    for (std::size_t i = 0; i < menu.size(); ++i) {
        menu[i] = static_cast<std::uint8_t>(i + 1u);
        race[i] = static_cast<std::uint8_t>(90u + i);
    }
    if (!game_native_copy_dynamic_stream(gpu.data(), gpu.size(),
                                          menu.data(), menu.size())) return 1;
    for (std::size_t i = 0; i < menu.size(); ++i)
        if (gpu[i] != menu[i]) return 2;
    // Consecutive menu->race frames must supply the new live source bytes.
    if (!game_native_copy_dynamic_stream(gpu.data(), gpu.size(),
                                          race.data(), race.size())) return 3;
    for (std::size_t i = 0; i < race.size(); ++i)
        if (gpu[i] != race[i]) return 4;
    const auto before = gpu;
    if (game_native_copy_dynamic_stream(gpu.data(), 4u, menu.data(), menu.size()) ||
        game_native_copy_dynamic_stream(nullptr, gpu.size(), menu.data(), menu.size()) ||
        game_native_copy_dynamic_stream(gpu.data(), gpu.size(), nullptr, menu.size()) ||
        game_native_copy_dynamic_stream(gpu.data(), gpu.size(), menu.data(), 0u) ||
        gpu != before) return 5;
    std::puts("PASS: live Draw/Indexed GPU stream copy and transactional rejection");
    return 0;
}
