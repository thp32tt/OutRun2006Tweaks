#pragma once
#include <cstdint>

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

void WheelFFB_RequestDirectionTest(int direction);
void WheelFFB_RequestSettingsTransition();
WheelFFBHeadroomSnapshot WheelFFB_GetHeadroomSnapshot();
void WheelFFB_ResetHeadroomStats();
