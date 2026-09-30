#pragma once

#include <d3d9.h>
#include "screen_space_kind.hpp"
#include "../renderer.hpp"

namespace OutRunVRStereo
{
    OutRunVR::Render::ScreenSpaceKind
    ClassifyScreenSpacePass(IDirect3DDevice9* device) noexcept;

    bool BuildScreenSpaceEyeConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        OutRunVR::Render::ScreenSpaceKind kind,
        float original[16], float eyeConstants[2][16],
        float eyeScale[2], float eyeOffset[2]) noexcept;

    void NoteScreenSpaceFovDraw() noexcept;
}
