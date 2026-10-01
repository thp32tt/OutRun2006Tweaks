#pragma once

#include "../runtime_eligibility.hpp"

namespace OutRunVRRenderer
{
    void InvalidateRendererStateAfterExternalRestore() noexcept;
    void InvalidateRawWvpGeneration() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    RendererInstallState() noexcept;
}
