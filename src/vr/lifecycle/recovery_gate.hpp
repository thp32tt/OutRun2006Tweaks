#pragma once

#include "../runtime_eligibility.hpp"

namespace OutRunVR::Lifecycle
{
    inline void SetRecoverySafetyBlock(bool blocked) noexcept
    {
        RuntimeEligibility::SetExternalSafetyBlock(blocked);
    }
}
