#pragma once

#include <d3d9.h>
#include <cstdint>

namespace OutRunVRDxvkMultiview
{
    struct Telemetry
    {
        std::uint64_t armAttempts{};
        std::uint64_t armSuccess{};
        std::uint64_t armRejected{};
        std::uint64_t drawSuccess{};
        std::uint64_t drawFailure{};
        std::uint64_t cancels{};
        std::uint64_t interfaceMisses{};
        std::uint64_t protocolMismatches{};
        std::uint64_t capabilityMisses{};
        std::uint64_t targetCreates{};
        std::uint64_t targetCreateFailures{};
        std::uint64_t targetBinds{};
        std::uint64_t targetFlushes{};
        std::uint64_t shaderPatchAttempts{};
        std::uint64_t shaderPatchSuccess{};
        std::uint64_t shaderPatchFailures{};
        std::uint64_t providerDraws{};
        std::uint64_t twoPassArrayDraws{};
    };

    // True when the bridge itself is changing D3D9 state. The surrounding
    // OutRun hooks must not treat those calls as game-authored state changes.
    bool IsInternalProviderCall() noexcept;

    bool IsProviderAvailable(IDirect3DDevice9* device) noexcept;

    // Creates a two-layer color/depth target using dxvk-openRBRVR. The logical
    // left/right surfaces remain the existing OutRun eye surfaces; rendering
    // occurs in the layered target until FlushFrameTargets is called.
    bool EnsureFrameTargets(
        IDirect3DDevice9* device,
        IDirect3DSurface9* leftColorTarget,
        IDirect3DSurface9* rightColorTarget,
        IDirect3DSurface9* leftDepthTarget,
        IDirect3DSurface9* rightDepthTarget) noexcept;

    bool HasFrameTargets() noexcept;

    // Bind layer 0, layer 1, or OpenRbrDxvk::AllLayers. These calls preserve
    // the logical target identity tracked by the game hooks.
    bool BindColorLayer(
        IDirect3DDevice9* device,
        std::uint32_t layer) noexcept;
    bool BindDepthLayer(
        IDirect3DDevice9* device,
        std::uint32_t layer) noexcept;
    bool BindEyeLayer(
        IDirect3DDevice9* device,
        std::uint32_t layer) noexcept;

    // Copy the layered color image back into the conventional left/right
    // surfaces. copyDepth is only used outside BeginScene (normally Present).
    bool FlushFrameTargets(
        IDirect3DDevice9* device,
        bool copyDepth) noexcept;

    bool IsLogicalLeftColor(IDirect3DSurface9* surface) noexcept;
    bool IsLogicalLeftDepth(IDirect3DSurface9* surface) noexcept;

    // Converts the current verified programmable world shader into a cached
    // SPIR-V multiview variant. One following D3D9 draw then renders both
    // layers, with c64-c67 selected by BuiltIn ViewIndex.
    bool TryArmWorldDraw(
        IDirect3DDevice9* device,
        IDirect3DSurface9* rightColorTarget,
        IDirect3DSurface9* rightDepthTarget,
        const float* leftWvp,
        const float* rightWvp,
        std::uint64_t poseSequence,
        std::uint64_t drawToken,
        std::uint32_t eligibilityFlags) noexcept;

    void FinishArmedDraw(bool drawSucceeded) noexcept;

    // Used when the validated renderer executes a fallback two-pass draw into
    // the same layered target. It is telemetry only; no provider state change.
    void NoteTwoPassArrayDraw() noexcept;

    void InvalidateFrameTargets() noexcept;
    void InvalidateDevice() noexcept;
    Telemetry GetTelemetry() noexcept;
}
