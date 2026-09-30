#pragma once

#include "../runtime_eligibility.hpp"

namespace OutRunVRRenderer
{
    void InvalidateRendererStateAfterExternalRestore() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    RendererInstallState() noexcept;
}
