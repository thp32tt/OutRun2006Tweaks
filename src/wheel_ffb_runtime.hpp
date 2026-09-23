#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Read-only snapshots used by the F11 diagnostics/setup UI. Gameplay owns the
// mutable FFB engine state; the overlay only requests actions and displays it.
struct WheelFFBHeadroomSnapshot
{
    std::uint64_t samples = 0;
    float currentDemand = 0.0f;
    float peakDemand = 0.0f;
    float p95Demand = 0.0f;
    float p99Demand = 0.0f;
    float softKneePercent = 0.0f;
    float hardClipPercent = 0.0f;
    float suggestedOverall = 0.0f;
};

struct WheelFFBStatusSnapshot
{
    bool initialized = false;
    bool acquired = false;
    bool outputOwner = false;
    bool ffbStateValid = false;
    bool actuatorsOn = false;
    bool powerOn = false;
    bool powerOff = false;
    bool safetySwitchOn = false;
    bool safetySwitchOff = false;
    bool userSwitchOn = false;
    bool userSwitchOff = false;
    bool paused = false;
    bool deviceLost = false;
    bool constantEffect = false;
    bool springEffect = false;
    bool damperEffect = false;
    bool periodicEffects = false;
    bool constantCapsKnown = false;
    bool constantDynamic = false;
    bool polarDirectionDynamic = false;
    bool springCapsKnown = false;
    bool springDynamic = false;
    bool damperCapsKnown = false;
    bool damperDynamic = false;
    bool periodicCapsKnown = false;
    bool periodicDynamic = false;
    bool directionTested = false;
};

inline constexpr std::size_t WheelFFBGraphCapacity = 180;
struct WheelFFBGraphSnapshot
{
    std::size_t count = 0;
    std::array<float, WheelFFBGraphCapacity> rawStructural{};
    std::array<float, WheelFFBGraphCapacity> softLimited{};
    std::array<float, WheelFFBGraphCapacity> postSlew{};
    std::array<float, WheelFFBGraphCapacity> finalOutput{};
    std::array<float, WheelFFBGraphCapacity> xForceNormalized{};
    std::array<float, WheelFFBGraphCapacity> modernSat{};
    std::array<float, WheelFFBGraphCapacity> nativeSat{};
    std::array<float, WheelFFBGraphCapacity> nativeShare{};
    std::array<float, WheelFFBGraphCapacity> nativeTireNormalized{};
    std::array<float, WheelFFBGraphCapacity> nativeTireSat{};
    std::array<float, WheelFFBGraphCapacity> nativeTireShare{};
};


struct WheelFFBXForceAnalysisSnapshot
{
    std::uint64_t samples = 0;
    float corrSteer = 0.0f;
    float corrModernSat = 0.0f;
    float corrFrontSlip = 0.0f;
    float corrYawRate = 0.0f;
    float confidence = 0.0f;
    bool frozenSuspicious = false;
    float frozenSeconds = 0.0f;
    float p50Abs = 0.0f;
    float p90Abs = 0.0f;
    float p95Abs = 0.0f;
    float p99Abs = 0.0f;
    float maxAbs = 0.0f;
};

void WheelFFB_RequestDirectionTest(int direction);
void WheelFFB_RequestSettingsTransition();
void WheelFFB_ResetDirectionTest();
WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot();
WheelFFBStatusSnapshot WheelFFB_GetStatusSnapshot();
WheelFFBGraphSnapshot WheelFFB_GetGraphSnapshot();
WheelFFBXForceAnalysisSnapshot WheelFFB_GetXForceAnalysisSnapshot();
void WheelFFB_ResetHeadroomStats();
