#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <Unknwn.h>

#include <cstddef>
#include <cstdint>

// OutRun-specific extension implemented only by the custom DXVK fork.
// Stock DXVK does not expose this IID, so QueryInterface failing is the normal
// compatibility-mode result and must always fall back to the existing renderer.
namespace OutRunVR::DxvkInterop
{
    inline constexpr std::uint32_t ProtocolVersion = 1;

    enum CapabilityFlags : std::uint32_t
    {
        CapabilityNone = 0,
        CapabilityWorldMultiview = 1u << 0,
        CapabilityExternalRightTargets = 1u << 1,
    };

    enum DrawEligibilityFlags : std::uint32_t
    {
        DrawPrimitive = 1u << 0,
        DrawIndexedPrimitive = 1u << 1,
        DrawPrimitiveUP = 1u << 2,
        DrawIndexedPrimitiveUP = 1u << 3,
    };

    enum StereoFlags : std::uint32_t
    {
        StereoEnabled = 1u << 0,
        MirrorLeftEye = 1u << 1,
        AllowInternalArrayTarget = 1u << 2,
    };

#pragma pack(push, 8)
    struct FrameStateV1
    {
        std::uint32_t size = sizeof(FrameStateV1);
        std::uint32_t version = ProtocolVersion;
        std::uint64_t poseSequence{};
        std::uint64_t frameId{};
        std::uint32_t flags{};
        std::uint32_t reserved{};
    };

    struct DrawStateV1
    {
        std::uint32_t size = sizeof(DrawStateV1);
        std::uint32_t version = ProtocolVersion;
        std::uint64_t poseSequence{};
        std::uint64_t drawToken{};
        float leftWvp[16]{};
        float rightWvp[16]{};
        std::uint32_t eligibilityFlags{};
        std::uint32_t reserved{};
    };

    struct CountersV1
    {
        std::uint32_t size = sizeof(CountersV1);
        std::uint32_t version = ProtocolVersion;
        std::uint64_t armedDraws{};
        std::uint64_t multiviewDraws{};
        std::uint64_t rejectedDraws{};
        std::uint64_t fallbackDraws{};
    };
#pragma pack(pop)

    static_assert(sizeof(FrameStateV1) == 32);
    static_assert(sizeof(DrawStateV1) == 160);
    static_assert(sizeof(CountersV1) == 40);
    static_assert(offsetof(FrameStateV1, poseSequence) == 8);
    static_assert(offsetof(DrawStateV1, leftWvp) == 24);
    static_assert(offsetof(DrawStateV1, rightWvp) == 88);
}

// {B16D40B8-1A79-4E11-9D47-7A50C1F56E62}
MIDL_INTERFACE("b16d40b8-1a79-4e11-9d47-7a50c1f56e62")
ID3D9OutRunVRInterop : public IUnknown
{
public:
    virtual HRESULT STDMETHODCALLTYPE GetProtocolVersion(
        std::uint32_t* version) = 0;

    virtual HRESULT STDMETHODCALLTYPE GetCapabilities(
        std::uint32_t* flags) = 0;

    virtual HRESULT STDMETHODCALLTYPE SetFrameState(
        const OutRunVR::DxvkInterop::FrameStateV1* state) = 0;

    // Arms exactly one following D3D9 draw. The DXVK fork must consume or
    // reject the state atomically and clear it after that draw.
    virtual HRESULT STDMETHODCALLTYPE ArmStereoDraw(
        const OutRunVR::DxvkInterop::DrawStateV1* state,
        IUnknown* rightColorTarget,
        IUnknown* rightDepthTarget) = 0;

    virtual HRESULT STDMETHODCALLTYPE CancelStereoDraw() = 0;

    virtual HRESULT STDMETHODCALLTYPE GetCounters(
        OutRunVR::DxvkInterop::CountersV1* counters) = 0;
};
