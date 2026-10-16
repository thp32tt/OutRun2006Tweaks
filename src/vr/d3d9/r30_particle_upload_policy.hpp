#pragma once
#include <cstddef>
#include <cstdint>

// Pure eligibility contract for the *existing* DX9Ex R30 XYZRHW particle
// submitter. No material can be classified from ALPHABLENDENABLE alone.
namespace OutRunVR::R30ParticleUpload {
struct Gate {
    bool optedIn = false;
    bool exactWorldParticle = false;
    bool stereoWorld = false;
    bool reliableEffectState = false;
    bool alphaBlend = false;
    bool writesDepth = true;
    bool indexed = false;
    bool stateBlockRecording = false;
    std::uint32_t stride = 0;
    std::uint32_t vertices = 0;
};
constexpr std::uint32_t kCapacity = 4u * 1024u * 1024u;
constexpr std::uint32_t kMinPerEyeBytes = 1024u;
constexpr std::uint32_t kMaxPerEyeBytes = 1024u * 1024u;
constexpr bool Eligible(const Gate& g) noexcept {
    if (!g.optedIn || !g.exactWorldParticle || !g.stereoWorld ||
        !g.reliableEffectState || !g.alphaBlend || g.writesDepth ||
        g.indexed || g.stateBlockRecording ||
        g.stride < 16u || g.stride > 256u || g.vertices < 3u)
        return false;
    // Prevent overflow, tiny Draw overhead and GPU ring exhaustion.
    return g.vertices <= kMaxPerEyeBytes / g.stride &&
           g.vertices * g.stride >= kMinPerEyeBytes;
}
// A failed first-eye DynamicVB stream bind invokes no GPU DrawPrimitive.
// Once a physical eye draw has been attempted (even if its HRESULT failed),
// replaying native DrawPrimitiveUP could double-blend particles or leave the
// right eye partially published. Likewise, an un-restored stream is unsafe.
// Permit the original UP fallback ONLY for a proved pre-draw failure.
constexpr bool MayUseNativeUpAfterGpuAttempt(
    bool physicalDrawAttempted, bool streamRestored, bool gpuAttemptFailed) noexcept {
    return !physicalDrawAttempted && streamRestored && gpuAttemptFailed;
}
static_assert(MayUseNativeUpAfterGpuAttempt(false,true,true));
static_assert(!MayUseNativeUpAfterGpuAttempt(true,true,true));
static_assert(!MayUseNativeUpAfterGpuAttempt(false,false,true));
static_assert(!MayUseNativeUpAfterGpuAttempt(false,true,false));
static_assert(Eligible({true,true,true,true,true,false,false,false,24,100}));
static_assert(!Eligible({true,false,true,true,true,false,false,false,24,100}));
static_assert(!Eligible({true,true,true,true,true,true,false,false,24,100}));
static_assert(!Eligible({true,true,true,true,true,false,true,false,24,100}));
static_assert(!Eligible({true,true,true,false,true,false,false,false,24,100}));
static_assert(!Eligible({true,true,true,true,true,false,false,false,0,100}));
static_assert(!Eligible({true,true,true,true,true,false,false,false,24,1}));
} // namespace OutRunVR::R30ParticleUpload
