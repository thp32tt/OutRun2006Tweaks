#pragma once

#include <Windows.h>

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "plugin.hpp"
#include "game_addrs.hpp"

// Research-only reader for the canonical player-car physics workspace proven by
// the full OR2006C2C executable map. Nothing in this file feeds wheel output.
//
// Canonical EXE evidence:
//   GamePlCar_Ctrl -> FUN_00502c90 / FUN_004a8100
//   player workspace VA 0x0082E7F0 => RVA 0x0042E7F0
//   workspace+0x248..0x254 = four wheel pointers
//   wheel objects are inline at +0x258 with a 0xF4 stride
//   wheels 0/1 receive steering angle in FUN_00500700, proving front axle
//
// Left/right ordering and the final physical units/signs of force channels are
// deliberately NOT asserted yet. Capture labels therefore use front0/front1 and
// rear0/rear1 rather than FL/FR/RL/RR.

namespace Settings
{
    extern Setting<bool> WheelFFBNativePhysicsCapture60Hz;
}

static_assert(offsetof(EVWORK_CAR, field_1C4) == 0x1C4,
    "EVWORK_CAR::field_1C4 offset drifted");
static_assert(offsetof(EVWORK_CAR, field_1D0) == 0x1D0,
    "EVWORK_CAR::field_1D0 offset drifted");
static_assert(offsetof(EVWORK_CAR, field_1D4) == 0x1D4,
    "EVWORK_CAR::field_1D4 offset drifted");

namespace WheelNativePhysicsResearch
{
    inline constexpr std::uintptr_t PlayerWorkspaceRva = 0x0042E7F0u;
    inline constexpr std::size_t WheelPointerTableOffset = 0x248;
    inline constexpr std::size_t FirstWheelOffset = 0x258;
    inline constexpr std::size_t WheelStride = 0xF4;
    inline constexpr int WheelCount = 4;

    template <typename T>
    inline T read_value(const std::uint8_t* base, std::size_t offset)
    {
        T value{};
        std::memcpy(&value, base + offset, sizeof(value));
        return value;
    }

    struct WheelSample
    {
        float contactRaw08 = 0.0f;
        float compression18 = 0.0f;
        float previousCompression1C = 0.0f;
        float compressionRate20 = 0.0f;
        float suspensionReaction24 = 0.0f;
        float contactReference28 = 0.0f;
        float normalLoad34 = 0.0f;
        float referenceLoad38 = 0.0f;
        float tireLocalAC = 0.0f;
        float tireLocalB0 = 0.0f;
        float tireForceB4 = 0.0f;
        float tireForceB8 = 0.0f;
        float handicapForceBC = 0.0f;
        float gripCapacityC0 = 0.0f;
        float slipMetricE0 = 0.0f;
        float combinedScaleE4 = 0.0f;
        std::int16_t steerAngleEE = 0;
        std::int16_t forceAngleF0 = 0;
        bool finite = false;
    };

    inline WheelSample sample_wheel(const std::uint8_t* wheel)
    {
        WheelSample out{};
        out.contactRaw08 = read_value<float>(wheel, 0x08);
        out.compression18 = read_value<float>(wheel, 0x18);
        out.previousCompression1C = read_value<float>(wheel, 0x1C);
        out.compressionRate20 = read_value<float>(wheel, 0x20);
        out.suspensionReaction24 = read_value<float>(wheel, 0x24);
        out.contactReference28 = read_value<float>(wheel, 0x28);
        out.normalLoad34 = read_value<float>(wheel, 0x34);
        out.referenceLoad38 = read_value<float>(wheel, 0x38);
        out.tireLocalAC = read_value<float>(wheel, 0xAC);
        out.tireLocalB0 = read_value<float>(wheel, 0xB0);
        out.tireForceB4 = read_value<float>(wheel, 0xB4);
        out.tireForceB8 = read_value<float>(wheel, 0xB8);
        out.handicapForceBC = read_value<float>(wheel, 0xBC);
        out.gripCapacityC0 = read_value<float>(wheel, 0xC0);
        out.slipMetricE0 = read_value<float>(wheel, 0xE0);
        out.combinedScaleE4 = read_value<float>(wheel, 0xE4);
        out.steerAngleEE = read_value<std::int16_t>(wheel, 0xEE);
        out.forceAngleF0 = read_value<std::int16_t>(wheel, 0xF0);

        out.finite =
            std::isfinite(out.contactRaw08) &&
            std::isfinite(out.compression18) &&
            std::isfinite(out.previousCompression1C) &&
            std::isfinite(out.compressionRate20) &&
            std::isfinite(out.suspensionReaction24) &&
            std::isfinite(out.contactReference28) &&
            std::isfinite(out.normalLoad34) &&
            std::isfinite(out.referenceLoad38) &&
            std::isfinite(out.tireLocalAC) &&
            std::isfinite(out.tireLocalB0) &&
            std::isfinite(out.tireForceB4) &&
            std::isfinite(out.tireForceB8) &&
            std::isfinite(out.handicapForceBC) &&
            std::isfinite(out.gripCapacityC0) &&
            std::isfinite(out.slipMetricE0) &&
            std::isfinite(out.combinedScaleE4);
        return out;
    }

    inline bool pointer_table_matches(const std::uint8_t* workspace)
    {
        if (!workspace)
            return false;

        for (int i = 0; i < WheelCount; ++i)
        {
            const std::uint32_t stored = read_value<std::uint32_t>(
                workspace, WheelPointerTableOffset + static_cast<std::size_t>(i) * 4);
            const auto expectedPtr =
                workspace + FirstWheelOffset + static_cast<std::size_t>(i) * WheelStride;
            const std::uint32_t expected =
                static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(expectedPtr));
            if (stored != expected)
                return false;
        }
        return true;
    }

    inline void capture_after_physics(EVWORK_CAR* car)
    {
        static std::uint64_t captureTick = 0;
        static DWORD lastInvalidLogTick = 0;

        if (!Settings::WheelFFBNativePhysicsCapture60Hz)
        {
            captureTick = 0;
            lastInvalidLogTick = 0;
            return;
        }

        if (!car || !Game::current_mode || *Game::current_mode != STATE_GAME)
            return;

        const auto* workspace = reinterpret_cast<const std::uint8_t*>(
            Module::exe_ptr(PlayerWorkspaceRva));
        if (!pointer_table_matches(workspace))
        {
            const DWORD now = GetTickCount();
            if (lastInvalidLogTick == 0 ||
                static_cast<DWORD>(now - lastInvalidLogTick) >= 1000u)
            {
                lastInvalidLogTick = now;
                spdlog::warn(
                    "WheelFFB NATIVE_PHYSICS workspace pointer table is not initialized/matching; capture skipped");
            }
            return;
        }

        std::array<WheelSample, WheelCount> w{};
        for (int i = 0; i < WheelCount; ++i)
        {
            const auto* wheel =
                workspace + FirstWheelOffset + static_cast<std::size_t>(i) * WheelStride;
            w[static_cast<std::size_t>(i)] = sample_wheel(wheel);
        }

        const float frontNormal = w[0].normalLoad34 + w[1].normalLoad34;
        const float frontNormalDiff = w[0].normalLoad34 - w[1].normalLoad34;
        const float frontForceB4 = w[0].tireForceB4 + w[1].tireForceB4;
        const float frontForceB8 = w[0].tireForceB8 + w[1].tireForceB8;
        const std::int16_t heading2E = car->field_2C[1];
        const std::int16_t angularD34 =
            read_value<std::int16_t>(reinterpret_cast<const std::uint8_t*>(car), 0xD34);

        const bool finite =
            w[0].finite && w[1].finite && w[2].finite && w[3].finite &&
            std::isfinite(car->field_1C4) &&
            std::isfinite(car->field_1D0) &&
            std::isfinite(car->field_1D4) &&
            std::isfinite(frontNormal) &&
            std::isfinite(frontNormalDiff) &&
            std::isfinite(frontForceB4) &&
            std::isfinite(frontForceB8);

        ++captureTick;
        spdlog::info(
            "WheelFFB NATIVE_PHYSICS tick={} t={} speed={} dSpeed={} prevDSpeed={} heading2E={} angularD34={} frontNormal={} frontNormalDiff={} frontB4={} frontB8={} finite={} "
            "front0[c08={} c18={} pc1c={} rate20={} susp24={} ref28={} n34={} nr38={} ac={} b0={} b4={} b8={} bc={} c0={} e0={} e4={} steerEE={} forceF0={}] "
            "front1[c08={} c18={} pc1c={} rate20={} susp24={} ref28={} n34={} nr38={} ac={} b0={} b4={} b8={} bc={} c0={} e0={} e4={} steerEE={} forceF0={}] "
            "rear0[c08={} c18={} pc1c={} rate20={} susp24={} ref28={} n34={} nr38={} ac={} b0={} b4={} b8={} bc={} c0={} e0={} e4={} steerEE={} forceF0={}] "
            "rear1[c08={} c18={} pc1c={} rate20={} susp24={} ref28={} n34={} nr38={} ac={} b0={} b4={} b8={} bc={} c0={} e0={} e4={} steerEE={} forceF0={}]",
            captureTick, GetTickCount(),
            car->field_1C4, car->field_1D0, car->field_1D4,
            heading2E, angularD34,
            frontNormal, frontNormalDiff, frontForceB4, frontForceB8, finite,
            w[0].contactRaw08, w[0].compression18, w[0].previousCompression1C,
            w[0].compressionRate20, w[0].suspensionReaction24, w[0].contactReference28,
            w[0].normalLoad34, w[0].referenceLoad38, w[0].tireLocalAC, w[0].tireLocalB0,
            w[0].tireForceB4, w[0].tireForceB8, w[0].handicapForceBC, w[0].gripCapacityC0,
            w[0].slipMetricE0, w[0].combinedScaleE4, w[0].steerAngleEE, w[0].forceAngleF0,
            w[1].contactRaw08, w[1].compression18, w[1].previousCompression1C,
            w[1].compressionRate20, w[1].suspensionReaction24, w[1].contactReference28,
            w[1].normalLoad34, w[1].referenceLoad38, w[1].tireLocalAC, w[1].tireLocalB0,
            w[1].tireForceB4, w[1].tireForceB8, w[1].handicapForceBC, w[1].gripCapacityC0,
            w[1].slipMetricE0, w[1].combinedScaleE4, w[1].steerAngleEE, w[1].forceAngleF0,
            w[2].contactRaw08, w[2].compression18, w[2].previousCompression1C,
            w[2].compressionRate20, w[2].suspensionReaction24, w[2].contactReference28,
            w[2].normalLoad34, w[2].referenceLoad38, w[2].tireLocalAC, w[2].tireLocalB0,
            w[2].tireForceB4, w[2].tireForceB8, w[2].handicapForceBC, w[2].gripCapacityC0,
            w[2].slipMetricE0, w[2].combinedScaleE4, w[2].steerAngleEE, w[2].forceAngleF0,
            w[3].contactRaw08, w[3].compression18, w[3].previousCompression1C,
            w[3].compressionRate20, w[3].suspensionReaction24, w[3].contactReference28,
            w[3].normalLoad34, w[3].referenceLoad38, w[3].tireLocalAC, w[3].tireLocalB0,
            w[3].tireForceB4, w[3].tireForceB8, w[3].handicapForceBC, w[3].gripCapacityC0,
            w[3].slipMetricE0, w[3].combinedScaleE4, w[3].steerAngleEE, w[3].forceAngleF0);
    }
}
