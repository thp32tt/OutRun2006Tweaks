#pragma once
// Per-car source diagnostics: a large HQ OVC may spend hundreds of native
// callbacks in CPU/GPU preparation. Eight early warmup samples must NOT
// consume the only reports of the first actual stereo success or fault.
#include <cstdint>
#include "dino_external_original_car_gate.hpp"

namespace OutRunVR::DinoSidecar {
struct ExternalCarTraceBudget final {
    std::uint64_t attempts=0;
    unsigned completeReports=0;
    unsigned partialReports=0;
    unsigned failedReports=0;

    bool ShouldLog(OriginalCarRoute route,bool terminalFailed,
                   bool verbose) noexcept {
        const std::uint64_t sample=++attempts;
        bool milestone=false;
        if(route==OriginalCarRoute::ExternalComplete &&
           completeReports<4u) {
            ++completeReports;
            milestone=true;
        }
        if(route==OriginalCarRoute::ExternalPartial &&
           partialReports<4u) {
            ++partialReports;
            milestone=true;
        }
        if(terminalFailed && failedReports<4u) {
            ++failedReports;
            milestone=true;
        }
        // Preserve explicit verbose tracing while making the default
        // diagnostic flag bounded even during a persistent partial frame.
        return sample<=8u || milestone ||
               (verbose && (((sample&(sample-1u))==0u) ||
                             route==OriginalCarRoute::ExternalPartial));
    }
};
} // namespace OutRunVR::DinoSidecar
