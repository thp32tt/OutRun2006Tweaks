#pragma once

#include <d3d9.h>

namespace OutRunVRStereo
{
    bool StableStereoBase(IDirect3DDevice9* device) noexcept;
    bool FragileEffectCached(
        IDirect3DDevice9* device, bool& fragile) noexcept;
    void NoteStableTwoEyeDraw() noexcept;
}
