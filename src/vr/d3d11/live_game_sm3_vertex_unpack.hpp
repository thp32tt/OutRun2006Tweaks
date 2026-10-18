#pragma once
// Exact, portable D3D9 programmable declaration conversion for native D3D11.
// D3D9 declaration TYPE numeric values (d3d9types.h); no D3D9 device reads,
// GPU mutation or lifetime dependencies. Unsupported encodings stay fail-closed.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>

namespace outrun::vr::dx11::live_game_frame {
[[nodiscard]] constexpr std::uint32_t game_sm3_decl_width(std::uint32_t type) noexcept {
    switch (type) {
    case 0u: return 4u;   // FLOAT1
    case 1u: return 8u;   // FLOAT2
    case 2u: return 12u;  // FLOAT3
    case 3u: return 16u;  // FLOAT4
    case 4u: case 5u: case 6u: case 8u: case 9u: case 11u:
    case 15u: return 4u;  // D3DCOLOR, UBYTE4, SHORT2, UBYTE4N,
                          // SHORT2N, USHORT2N, FLOAT16_2
    case 7u: case 10u: case 12u: case 16u: return 8u;
    default: return 0u;  // UDEC3/DEC3N need distinct signed packing rules
    }
}

[[nodiscard]] inline float game_sm3_half_to_float(std::uint16_t h) noexcept {
    const std::uint32_t exponent = (h >> 10u) & 31u;
    const std::uint32_t mantissa = h & 1023u;
    if (exponent == 0u) {
        const float subnormal = std::ldexp(static_cast<float>(mantissa), -24);
        return (h & 0x8000u) ? -subnormal : subnormal;
    }
    const std::uint32_t bits = ((h & 0x8000u) ? 0x80000000u : 0u) |
        (exponent == 31u ? 0x7f800000u : (exponent + 112u) << 23u) |
        (mantissa << 13u);
    float result = 0.0f;
    std::memcpy(&result, &bits, sizeof(result));
    return result;
}

// D3D9 passes vertex components to float SM3 shader registers. Repack mixed
// FLOAT / D3DCOLOR / integer / normalized / half declarations as explicit
// FLOAT4 values so D3D11 input signatures never reinterpret integer bits,
// B8G8R8A8 vertex formats, or missing default z/w components.
[[nodiscard]] inline bool game_sm3_unpack_attribute(
    std::uint32_t type, const std::uint8_t* src,
    std::array<float, 4>& out) noexcept {
    if (!src || !game_sm3_decl_width(type)) return false;
    out = {0.0f, 0.0f, 0.0f, 1.0f};
    switch (type) {
    case 0u: case 1u: case 2u: case 3u: {
        const std::uint32_t components = type + 1u;
        std::memcpy(out.data(), src, components * sizeof(float));
        return true;
    }
    case 4u: // D3DCOLOR lives in BGRA byte order; SM3 COLOR reads RGBA.
        out = {src[2] / 255.0f, src[1] / 255.0f,
               src[0] / 255.0f, src[3] / 255.0f};
        return true;
    case 5u: case 8u: // UBYTE4 (unnormalized) / UBYTE4N
        for (unsigned i = 0; i < 4u; ++i)
            out[i] = type == 5u ? static_cast<float>(src[i]) :
                                 src[i] / 255.0f;
        return true;
    case 6u: case 7u: case 9u: case 10u: case 11u: case 12u: {
        const bool short2 = type == 6u || type == 9u || type == 11u;
        const bool normalized = type >= 9u;
        const bool unsignedShort = type == 11u || type == 12u;
        const unsigned count = short2 ? 2u : 4u;
        for (unsigned i = 0u; i < count; ++i) {
            std::uint16_t bits = 0u;
            std::memcpy(&bits, src + i * sizeof(bits), sizeof(bits));
            std::int16_t signedValue = 0;
            std::memcpy(&signedValue, &bits, sizeof(bits));
            if (unsignedShort) out[i] = bits / 65535.0f;
            else if (normalized)
                out[i] = (std::max)(-1.0f, signedValue / 32767.0f);
            else out[i] = static_cast<float>(signedValue);
        }
        return true;
    }
    case 15u: case 16u: { // FLOAT16_2 / FLOAT16_4
        const unsigned count = type == 15u ? 2u : 4u;
        for (unsigned i = 0u; i < count; ++i) {
            std::uint16_t half = 0u;
            std::memcpy(&half, src + i * sizeof(half), sizeof(half));
            out[i] = game_sm3_half_to_float(half);
        }
        return true;
    }
    default: return false;
    }
}
static_assert(game_sm3_decl_width(0u) == 4u &&
              game_sm3_decl_width(3u) == 16u &&
              game_sm3_decl_width(4u) == 4u &&
              game_sm3_decl_width(10u) == 8u &&
              game_sm3_decl_width(16u) == 8u &&
              game_sm3_decl_width(13u) == 0u &&
              game_sm3_decl_width(17u) == 0u);
} // namespace outrun::vr::dx11::live_game_frame
