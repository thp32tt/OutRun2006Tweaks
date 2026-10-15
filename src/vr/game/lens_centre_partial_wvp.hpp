#pragma once
#include <cstdint>

// Original C993 may submit c64..c67 in several successful game uploads.
// Never combine matrices across the exact producer call, latched pose,
// shader binding/epoch, or D3D9 game device. Stereo-internal uploads and
// unrelated/queued draws are excluded by the caller.
namespace OutRunVR::LensCentre
{
    struct PartialWvpUpload
    {
        float raw[16]{};
        std::uint8_t covered = 0;
        std::uint64_t call = 0, pose = 0, shaderEpoch = 0;
        std::uintptr_t shader = 0, device = 0;

        constexpr void Reset() noexcept
        {
            covered = 0;
            call = pose = shaderEpoch = 0;
            shader = device = 0;
        }

        constexpr bool Append(std::uint32_t start, std::uint32_t count,
            const float* values, std::uint64_t currentCall,
            std::uint64_t currentPose, std::uintptr_t currentShader,
            std::uint64_t currentShaderEpoch, std::uintptr_t currentDevice,
            bool exactDirectCentre) noexcept
        {
            // Subtraction avoids overflowing start+count for bad D3D9 args.
            if (!exactDirectCentre || !values || !count ||
                start >= 68 || (start < 64 && count <= 64 - start) ||
                !currentCall || !currentPose || !currentShader ||
                !currentShaderEpoch || !currentDevice)
            {
                Reset();
                return false;
            }
            if (covered && (call != currentCall || pose != currentPose ||
                shader != currentShader || shaderEpoch != currentShaderEpoch ||
                device != currentDevice))
                Reset();
            if (!covered)
            {
                call = currentCall;
                pose = currentPose;
                shader = currentShader;
                shaderEpoch = currentShaderEpoch;
                device = currentDevice;
            }
            for (std::uint32_t reg = 64; reg != 68; ++reg)
            {
                if (reg < start || reg - start >= count)
                    continue;
                const std::uint32_t source = (reg - start) * 4;
                const std::uint32_t target = (reg - 64) * 4;
                for (std::uint32_t column = 0; column != 4; ++column)
                    raw[target + column] = values[source + column];
                covered = static_cast<std::uint8_t>(
                    covered | (1u << (reg - 64)));
            }
            return covered == 0x0Fu;
        }
    };

    constexpr bool SplitUploadCompletesOwnedWvp() noexcept
    {
        PartialWvpUpload stage{};
        constexpr float a[8]{1,2,3,4,5,6,7,8};
        constexpr float b[8]{9,10,11,12,13,14,15,16};
        return !stage.Append(64,2,a,3,7,0x10,2,0x30,true) &&
            stage.Append(66,2,b,3,7,0x10,2,0x30,true) &&
            stage.raw[0] == 1 && stage.raw[7] == 8 &&
            stage.raw[8] == 9 && stage.raw[15] == 16;
    }
    constexpr bool RejectsMixedAndFailedUploads() noexcept
    {
        PartialWvpUpload stage{};
        constexpr float a[8]{1,2,3,4,5,6,7,8};
        constexpr float b[8]{9,10,11,12,13,14,15,16};
        stage.Append(64,2,a,3,7,0x10,2,0x30,true);
        if (stage.Append(66,2,b,4,7,0x10,2,0x30,true) ||
            stage.covered != 0x0Cu)
            return false;
        if (stage.Append(64,2,a,4,8,0x10,2,0x30,true) ||
            stage.covered != 0x03u)
            return false;
        if (stage.Append(66,2,b,4,8,0x20,2,0x30,true) ||
            stage.covered != 0x0Cu)
            return false;
        if (stage.Append(64,2,a,4,8,0x20,3,0x30,true) ||
            stage.covered != 0x03u)
            return false;
        if (stage.Append(66,2,b,4,8,0x20,3,0x40,true) ||
            stage.covered != 0x0Cu)
            return false;
        if (stage.Append(64,2,a,4,8,0x20,3,0x40,false) ||
            stage.covered != 0)
            return false;
        stage.Append(64,2,a,4,8,0x20,3,0x40,true);
        stage.Reset(); // Failed D3D9 upload or aborted scene.
        return !stage.Append(66,2,b,4,8,0x20,3,0x40,true) &&
            stage.covered == 0x0Cu;
    }
    static_assert(SplitUploadCompletesOwnedWvp());
    static_assert(RejectsMixedAndFailedUploads());
}
