#pragma once

#include <d3d9.h>
#include <cstdint>

namespace OutRunVR::State
{
    struct DepthTargetSnapshot
    {
        IDirect3DSurface9* identity = nullptr;
        D3DSURFACE_DESC desc{};
        bool known = false;
        std::uint64_t generation = 0;
    };
}

namespace OutRunVRStereo
{
    OutRunVR::State::DepthTargetSnapshot
    MainDepthTargetSnapshot() noexcept;

    void NoteMainDepthContentWrite() noexcept;
    bool IsMainDepthDeferred() noexcept;
    bool CurrentDepthCanMirror() noexcept;
}
