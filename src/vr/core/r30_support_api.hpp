#pragma once
// Behavior-neutral R30/lower-owner services consumed by R31.
//
// R31 is being prepared for independent translation-unit compilation. These
// calls preserve the current lower-chain behavior while preventing R31 from
// reaching private R30/R29/R23/R22/R9 state through a textual .cpp include.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <Windows.h>
#include <d3d9.h>
#include <cstdint>

#include "../runtime_eligibility.hpp"
#include "../ipc/protocol.hpp"

namespace OutRunVRStereo
{
    OutRunVR::RuntimeEligibility::InstallState R30InstallStatus() noexcept;

    bool R30SupportTelemetryEnabled() noexcept;
    bool R30SupportIsGameDevice(IDirect3DDevice9* device) noexcept;
    bool R30SupportInternalStereoPassActive() noexcept;
    std::uint64_t R30SupportPresentEpoch() noexcept;
    bool R30SupportTargetIsBackBuffer() noexcept;
    bool R30SupportAnyAuxRenderTargetActive() noexcept;
    bool R30SupportTryGetTrackedViewport(D3DVIEWPORT9& viewport) noexcept;

    void R30SupportInvalidateEffectStateCache() noexcept;
    void R30SupportInvalidateTrackedRasterShadow() noexcept;
    void R30SupportInvalidateLiveStateSample() noexcept;
    float R30SupportWorldScale() noexcept;

    D3DMATRIX R30SupportMatrixFromQuaternionTranslation(
        const float orientation[4], const float position[3],
        float positionScale) noexcept;
    D3DMATRIX R30SupportInverseRigid(const D3DMATRIX& matrix) noexcept;
    D3DMATRIX R30SupportProjectionFromFov(
        const D3DMATRIX& base, const OutRunVR::SharedFov& fov) noexcept;
    D3DMATRIX R30SupportMultiplyMatrix(
        const D3DMATRIX& a, const D3DMATRIX& b) noexcept;
    D3DMATRIX R30SupportTransposeMatrix(const D3DMATRIX& matrix) noexcept;
    bool R30SupportMatrixFinite(const D3DMATRIX& matrix) noexcept;
    bool R30SupportGetInverseProjection(
        const D3DMATRIX& projection, D3DMATRIX& inverse) noexcept;

    bool R30SupportValidateVerifiedWvp(
        IDirect3DDevice9* device, const float verified[16],
        float live[16]) noexcept;
    bool R30SupportGetVerifiedProjection(
        float outProjection[16], std::uint32_t& generation,
        std::uint32_t& poseSequence) noexcept;
    void R30SupportResynchronizeShaderEpoch(
        IDirect3DDevice9* device) noexcept;
    void R30SupportInvalidateRendererStateAfterExternalRestore() noexcept;
    OutRunVR::RuntimeEligibility::InstallState
    R30SupportRendererInstallStatus() noexcept;
    bool R30SupportPrimeTrackedRasterShadow(
        IDirect3DDevice9* device) noexcept;
}
