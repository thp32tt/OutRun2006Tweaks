#pragma once
#include <cstdint>

// The original D3D9 shader-constant setter may invoke other game render
// hooks. The callback return is not a reliable source lifetime boundary:
// a nested game c64 write may supersede an outer upload. Only the SAME
// original C993 producer with unchanged GPU-source generation may publish
// its original WVP to the R84 binocular lens centre owner.
namespace OutRunVR::LensCentre
{
    struct UploadSourceStamp
    {
        std::uint64_t centreCall = 0;
        std::uint64_t pose = 0;
        std::uint64_t shaderEpoch = 0;
        std::uint64_t drawSerial = 0;
        std::uint64_t uploadGeneration = 0;
        std::uintptr_t shader = 0;
        bool exactDirectCentre = false;
    };

    constexpr bool SameSourceAfterNativeUpload(
        const UploadSourceStamp& before,
        const UploadSourceStamp& after) noexcept
    {
        return before.exactDirectCentre && after.exactDirectCentre &&
            before.centreCall != 0 && before.centreCall == after.centreCall &&
            before.pose != 0 && before.pose == after.pose &&
            before.shader != 0 && before.shader == after.shader &&
            before.shaderEpoch != 0 &&
            before.shaderEpoch == after.shaderEpoch &&
            before.drawSerial == after.drawSerial &&
            before.uploadGeneration != 0 &&
            before.uploadGeneration == after.uploadGeneration;
    }
}
