#pragma once
#include <cstdint>
#include "projection_pair_pipeline.hpp"

// This plan is valid only when the R23 LOCAL-fixed menu draws both eyes
// consecutively from the same UV, HDR settings and shared clip matrix.
// The legacy per-eye head-projected menu path has different clip matrices
// and intentionally never opts into this plan.
namespace OutRunVrMenuPair
{
    struct EyePlan
    {
        bool reuseUniformsAndPipeline = false;
    };

    inline EyePlan PlanSecondEye(
        bool leftDrawSucceeded, bool sameUvHdrAndClip, bool uninterrupted,
        unsigned firstEye, unsigned secondEye,
        std::uint32_t firstWidth, std::uint32_t firstHeight,
        std::uint32_t secondWidth, std::uint32_t secondHeight) noexcept
    {
        return {
            sameUvHdrAndClip && uninterrupted &&
            OutRunVrProjectionPair::CanReuseCommonPipeline(
                leftDrawSucceeded, firstEye, secondEye,
                firstWidth, firstHeight, secondWidth, secondHeight)
        };
    }
}
