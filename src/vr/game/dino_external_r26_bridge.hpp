#pragma once
// Only the final R26+HUD stereo TU owns this entry point. No R29/R84 APIs.
// Invoked from native player-car state hook, after full opt-in/gameplay gates.
#include <d3d9.h>
#include "dino_external_sidecar.hpp"
namespace OutRunVRStereo {
bool R26DinoSidecarTryDraw(IDirect3DDevice9* device,
    const D3DMATRIX& carWorld, const D3DMATRIX& gameView,
    const OutRunVR::DinoSidecar::Gate& gate,
    float worldScale, float depthScale, float vehicleScale) noexcept;
void R26DinoSidecarReleaseGpu() noexcept;
}
