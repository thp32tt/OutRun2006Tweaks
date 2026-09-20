#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>

#include <atomic>
#include <cstring>

#include <spdlog/spdlog.h>

#include "plugin.hpp"
#include "vr/core/render_backend.hpp"
#include "vr/d3d9/dxvk_interop.hpp"
#include "vr/d3d9/dxvk_multiview_bridge.hpp"
#include "vr/d3d9/dxvk_probe.hpp"

namespace Settings
{
    extern Setting<int> VRRenderBackend;
}

namespace OutRunVRDxvkMultiview
{
    namespace
    {
        IDirect3DDevice9* CachedDevice = nullptr;
        ID3D9OutRunVRInterop* CachedInterop = nullptr;
        bool InterfaceAttempted = false;
        bool Armed = false;

        std::atomic<std::uint64_t> ArmAttempts{0};
        std::atomic<std::uint64_t> ArmSuccess{0};
        std::atomic<std::uint64_t> ArmRejected{0};
        std::atomic<std::uint64_t> DrawSuccess{0};
        std::atomic<std::uint64_t> DrawFailure{0};
        std::atomic<std::uint64_t> Cancels{0};
        std::atomic<std::uint64_t> InterfaceMisses{0};
        std::atomic<std::uint64_t> ProtocolMismatches{0};
        std::atomic<std::uint64_t> CapabilityMisses{0};

        bool FirstEnabledLogged = false;
        bool FirstRejectLogged = false;
        bool FirstMissingLogged = false;

        void ReleaseCachedInterop() noexcept
        {
            if (CachedInterop)
            {
                CachedInterop->Release();
                CachedInterop = nullptr;
            }
            CachedDevice = nullptr;
            InterfaceAttempted = false;
            Armed = false;
        }

        bool BackendAllowsCustomDxvk() noexcept
        {
            const auto requested = OutRunVR::RenderBackendFromSetting(
                Settings::VRRenderBackend.get());
            if (requested == OutRunVR::RenderBackend::D3D9TwoPass ||
                requested == OutRunVR::RenderBackend::Dx12)
                return false;

            // Explicit DXVK may probe before the background diagnostic thread
            // finishes. Auto only promotes when DXVK was actually identified.
            return requested == OutRunVR::RenderBackend::Dxvk ||
                OutRunVRDxvkProbe::IsDxvkDetected();
        }

        ID3D9OutRunVRInterop* ResolveInterop(
            IDirect3DDevice9* device) noexcept
        {
            if (!device)
                return nullptr;

            if (CachedDevice != device)
                ReleaseCachedInterop();
            if (CachedInterop)
                return CachedInterop;
            if (InterfaceAttempted)
                return nullptr;

            InterfaceAttempted = true;
            CachedDevice = device;

            ID3D9OutRunVRInterop* interop = nullptr;
            const HRESULT hr = device->QueryInterface(
                __uuidof(ID3D9OutRunVRInterop),
                reinterpret_cast<void**>(&interop));
            if (FAILED(hr) || !interop)
            {
                ++InterfaceMisses;
                if (!FirstMissingLogged)
                {
                    FirstMissingLogged = true;
                    spdlog::info(
                        "VR DXVK MULTIVIEW: custom interop unavailable (hr=0x{:08X}); all draws stay on validated two-pass fallback",
                        static_cast<unsigned>(hr));
                }
                return nullptr;
            }

            std::uint32_t version = 0;
            const HRESULT versionHr = interop->GetProtocolVersion(&version);
            if (FAILED(versionHr) ||
                version != OutRunVR::DxvkInterop::ProtocolVersion)
            {
                ++ProtocolMismatches;
                spdlog::error(
                    "VR DXVK MULTIVIEW: protocol mismatch expected={} provider={} hr=0x{:08X}; custom path disabled",
                    OutRunVR::DxvkInterop::ProtocolVersion,
                    version,
                    static_cast<unsigned>(versionHr));
                interop->Release();
                return nullptr;
            }

            std::uint32_t capabilities = 0;
            const HRESULT capsHr = interop->GetCapabilities(&capabilities);
            constexpr std::uint32_t requiredCaps =
                OutRunVR::DxvkInterop::CapabilityWorldMultiview |
                OutRunVR::DxvkInterop::CapabilityExternalRightTargets;
            if (FAILED(capsHr) ||
                (capabilities & requiredCaps) != requiredCaps)
            {
                ++CapabilityMisses;
                if (!FirstMissingLogged)
                {
                    FirstMissingLogged = true;
                    spdlog::info(
                        "VR DXVK MULTIVIEW: provider protocol is present but capability flags=0x{:08X} do not include required=0x{:08X}; per-draw custom calls disabled and two-pass fallback stays active",
                        capabilities, requiredCaps);
                }
                interop->Release();
                return nullptr;
            }

            CachedInterop = interop;
            if (!FirstEnabledLogged)
            {
                FirstEnabledLogged = true;
                spdlog::info(
                    "VR DXVK MULTIVIEW: protocol v{} capabilities=0x{:08X} negotiated; verified stable world draws may use one-D3D9-draw multiview",
                    version, capabilities);
            }
            return CachedInterop;
        }
    }

    bool TryArmWorldDraw(
        IDirect3DDevice9* device,
        IDirect3DSurface9* rightColorTarget,
        IDirect3DSurface9* rightDepthTarget,
        const float* leftWvp,
        const float* rightWvp,
        std::uint64_t poseSequence,
        std::uint64_t drawToken) noexcept
    {
        if (!BackendAllowsCustomDxvk() || !device || !rightColorTarget ||
            !leftWvp || !rightWvp || poseSequence == 0)
            return false;

        if (CachedDevice == device && InterfaceAttempted && !CachedInterop)
            return false;

        ++ArmAttempts;
        ID3D9OutRunVRInterop* interop = ResolveInterop(device);
        if (!interop)
            return false;

        OutRunVR::DxvkInterop::FrameStateV1 frame{};
        frame.size = sizeof(frame);
        frame.version = OutRunVR::DxvkInterop::ProtocolVersion;
        frame.poseSequence = poseSequence;
        frame.frameId = drawToken;
        frame.flags = OutRunVR::DxvkInterop::StereoEnabled |
            OutRunVR::DxvkInterop::MirrorLeftEye |
            OutRunVR::DxvkInterop::AllowInternalArrayTarget;
        if (FAILED(interop->SetFrameState(&frame)))
        {
            ++ArmRejected;
            return false;
        }

        OutRunVR::DxvkInterop::DrawStateV1 draw{};
        draw.size = sizeof(draw);
        draw.version = OutRunVR::DxvkInterop::ProtocolVersion;
        draw.poseSequence = poseSequence;
        draw.drawToken = drawToken;
        std::memcpy(draw.leftWvp, leftWvp, sizeof(draw.leftWvp));
        std::memcpy(draw.rightWvp, rightWvp, sizeof(draw.rightWvp));

        const HRESULT hr = interop->ArmStereoDraw(
            &draw,
            static_cast<IUnknown*>(rightColorTarget),
            static_cast<IUnknown*>(rightDepthTarget));
        if (hr != S_OK)
        {
            ++ArmRejected;
            if (!FirstRejectLogged)
            {
                FirstRejectLogged = true;
                spdlog::warn(
                    "VR DXVK MULTIVIEW: provider rejected verified draw (hr=0x{:08X}); two-pass fallback remains active",
                    static_cast<unsigned>(hr));
            }
            return false;
        }

        Armed = true;
        ++ArmSuccess;
        return true;
    }

    void FinishArmedDraw(bool drawSucceeded) noexcept
    {
        if (!Armed)
            return;

        if (drawSucceeded)
            ++DrawSuccess;
        else
        {
            ++DrawFailure;
            if (CachedInterop)
            {
                CachedInterop->CancelStereoDraw();
                ++Cancels;
            }
        }
        Armed = false;
    }

    void InvalidateDevice() noexcept
    {
        if (Armed && CachedInterop)
        {
            CachedInterop->CancelStereoDraw();
            ++Cancels;
        }
        ReleaseCachedInterop();
    }

    Telemetry GetTelemetry() noexcept
    {
        Telemetry out{};
        out.armAttempts = ArmAttempts.load(std::memory_order_acquire);
        out.armSuccess = ArmSuccess.load(std::memory_order_acquire);
        out.armRejected = ArmRejected.load(std::memory_order_acquire);
        out.drawSuccess = DrawSuccess.load(std::memory_order_acquire);
        out.drawFailure = DrawFailure.load(std::memory_order_acquire);
        out.cancels = Cancels.load(std::memory_order_acquire);
        out.interfaceMisses = InterfaceMisses.load(std::memory_order_acquire);
        out.protocolMismatches =
            ProtocolMismatches.load(std::memory_order_acquire);
        out.capabilityMisses =
            CapabilityMisses.load(std::memory_order_acquire);
        return out;
    }
}
