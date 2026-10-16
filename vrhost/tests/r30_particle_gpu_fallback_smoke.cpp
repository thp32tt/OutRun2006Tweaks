#include "vr/d3d9/r30_particle_upload_policy.hpp"
#include <cassert>
#include <cstdint>
using namespace OutRunVR::R30ParticleUpload;
int main()
{
    // Original CPU UP path stays available after a failed left-eye bind.
    assert(MayUseNativeUpAfterGpuAttempt(false, true, true));
    // Native Draw can partly submit on failure, so no double alpha replay.
    assert(!MayUseNativeUpAfterGpuAttempt(true, true, true));
    // Right-eye bind fails after successful left-eye raster: no mono replay.
    assert(!MayUseNativeUpAfterGpuAttempt(true, true, false));
    // An unknown/failed stream cleanup must not be followed by native Draw.
    assert(!MayUseNativeUpAfterGpuAttempt(false, false, true));
    assert(!MayUseNativeUpAfterGpuAttempt(false, true, false));
    Gate particle{true,true,true,true,true,false,false,false,24,100};
    assert(Eligible(particle));
    // No accidental opt-in of water/glass/opaque/unknown or recorded draws.
    particle.exactWorldParticle=false;
    assert(!Eligible(particle));
    particle.exactWorldParticle=true;
    particle.alphaBlend=false;
    assert(!Eligible(particle));
    particle.alphaBlend=true;
    particle.stateBlockRecording=true;
    assert(!Eligible(particle));
    particle.stateBlockRecording=false;
    particle.writesDepth=true;
    assert(!Eligible(particle));
    return 0;
}
