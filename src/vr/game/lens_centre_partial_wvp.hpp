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
        std::uint64_t call = 0, pose = 0, shaderEpoch = 0, drawSerial = 0;
        std::uintptr_t shader = 0, device = 0;

        constexpr void Reset() noexcept
        {
            covered = 0;
            call = pose = shaderEpoch = drawSerial = 0;
            shader = device = 0;
        }

        constexpr bool Append(std::uint32_t start, std::uint32_t count,
            const float* values, std::uint64_t currentCall,
            std::uint64_t currentPose, std::uintptr_t currentShader,
            std::uint64_t currentShaderEpoch, std::uintptr_t currentDevice,
            std::uint64_t currentDrawSerial, bool exactDirectCentre) noexcept
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
            // A split matrix is a single GPU submission's evidence, not
            // merely one producer-call/shader/pose lifetime. Nested C993
            // draws can change c64 between otherwise identical uploads.
            // Overlapping rows are also an ambiguous new matrix: do not
            // combine them with untouched rows from an earlier upload.
            std::uint8_t incoming = 0;
            for (std::uint32_t reg = 64; reg != 68; ++reg)
                if (reg >= start && reg - start < count)
                    incoming = static_cast<std::uint8_t>(
                        incoming | (1u << (reg - 64)));
            if (covered && (call != currentCall || pose != currentPose ||
                shader != currentShader || shaderEpoch != currentShaderEpoch ||
                device != currentDevice || drawSerial != currentDrawSerial ||
                (covered & incoming) != 0))
                Reset();
            if (!covered)
            {
                call = currentCall;
                pose = currentPose;
                shader = currentShader;
                shaderEpoch = currentShaderEpoch;
                device = currentDevice;
                drawSerial = currentDrawSerial;
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
        return !stage.Append(64,2,a,3,7,0x10,2,0x30,7,true) &&
            stage.Append(66,2,b,3,7,0x10,2,0x30,7,true) &&
            stage.raw[0] == 1 && stage.raw[7] == 8 &&
            stage.raw[8] == 9 && stage.raw[15] == 16;
    }
    constexpr bool RejectsMixedAndFailedUploads() noexcept
    {
        PartialWvpUpload stage{};
        constexpr float a[8]{1,2,3,4,5,6,7,8};
        constexpr float b[8]{9,10,11,12,13,14,15,16};
        stage.Append(64,2,a,3,7,0x10,2,0x30,7,true);
        if (stage.Append(66,2,b,4,7,0x10,2,0x30,7,true) ||
            stage.covered != 0x0Cu)
            return false;
        if (stage.Append(64,2,a,4,8,0x10,2,0x30,7,true) ||
            stage.covered != 0x03u)
            return false;
        if (stage.Append(66,2,b,4,8,0x20,2,0x30,7,true) ||
            stage.covered != 0x0Cu)
            return false;
        if (stage.Append(64,2,a,4,8,0x20,3,0x30,7,true) ||
            stage.covered != 0x03u)
            return false;
        if (stage.Append(66,2,b,4,8,0x20,3,0x40,7,true) ||
            stage.covered != 0x0Cu)
            return false;
        if (stage.Append(64,2,a,4,8,0x20,3,0x40,7,false) ||
            stage.covered != 0)
            return false;
        stage.Append(64,2,a,4,8,0x20,3,0x40,7,true);
        stage.Reset(); // Failed D3D9 upload or aborted scene.
        return !stage.Append(66,2,b,4,8,0x20,3,0x40,7,true) &&
            stage.covered == 0x0Cu;
    }
    // A new actual Draw with the same shader/pose/producer is NOT the same
    // source matrix. Likewise, rewrites of already-covered partial rows
    // start a new assembly rather than lending untouched stale rows.
    constexpr bool RejectsCrossDrawAndOverlappingPartialWvp() noexcept
    {
        PartialWvpUpload stage{};
        constexpr float a[8]{1,2,3,4,5,6,7,8};
        constexpr float b[8]{9,10,11,12,13,14,15,16};
        if (stage.Append(64,2,a,3,7,0x10,2,0x30,20,true))
            return false;
        if (stage.Append(66,2,b,3,7,0x10,2,0x30,21,true) ||
            stage.covered != 0x0Cu || stage.drawSerial != 21)
            return false;
        if (!stage.Append(64,2,a,3,7,0x10,2,0x30,21,true))
            return false; // all four rows originated AFTER the last Draw
        stage.Reset();
        if (stage.Append(64,2,a,3,7,0x10,2,0x30,22,true))
            return false;
        if (stage.Append(65,2,b,3,7,0x10,2,0x30,22,true) ||
            stage.covered != 0x06u)
            return false; // overlapping row 65 invalidated old row 64
        if (stage.Append(67,1,b+4,3,7,0x10,2,0x30,22,true) ||
            stage.covered != 0x0Eu)
            return false;
        constexpr float finalRow[4]{17,18,19,20};
        return stage.Append(64,1,finalRow,3,7,0x10,2,0x30,22,true) &&
            stage.raw[0] == 17 && stage.raw[4] == 9 &&
            stage.raw[8] == 13 && stage.raw[12] == 13;
    }
    static_assert(RejectsCrossDrawAndOverlappingPartialWvp());
    static_assert(SplitUploadCompletesOwnedWvp());
    static_assert(RejectsMixedAndFailedUploads());
}
