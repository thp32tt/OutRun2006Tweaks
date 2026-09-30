#pragma once

#include <d3d9.h>
#include <cstdint>

namespace OutRunVR::Render
{
    struct EyeTailCache
    {
        bool valid = false;
        std::uint32_t poseSequence = 0;
        float worldScale = 0.0f;
        D3DMATRIX projection{};
        D3DMATRIX inverseProjection{};
        D3DMATRIX eyeTail[2]{};
    };
}
