#include "vr/d3d9/r30_particle_upload_policy.hpp"
using namespace OutRunVR::R30ParticleUpload;
int main()
{
    // Run under Release/NDEBUG too: asserts would compile out entirely.
    if (!MayUseNativeUpAfterGpuAttempt(false, true, true)) return 1;
    // Never double-blend after attempted physical GPU work, including
    // a driver-reported failure after writing a subset of fragments.
    if (MayUseNativeUpAfterGpuAttempt(true, true, true)) return 2;
    if (MayUseNativeUpAfterGpuAttempt(true, true, false)) return 3;
    // Failed stream restoration is a failed frame, not an UP recovery.
    if (MayUseNativeUpAfterGpuAttempt(false, false, true)) return 4;
    if (MayUseNativeUpAfterGpuAttempt(false, true, false)) return 5;
    Gate particle{true,true,true,true,true,false,false,false,24,100};
    if (!Eligible(particle)) return 6;
    particle.exactWorldParticle = false;
    if (Eligible(particle)) return 7;
    particle.exactWorldParticle = true;
    particle.alphaBlend = false;
    if (Eligible(particle)) return 8;
    particle.alphaBlend = true;
    particle.stateBlockRecording = true;
    if (Eligible(particle)) return 9;
    particle.stateBlockRecording = false;
    particle.writesDepth = true;
    if (Eligible(particle)) return 10;
    particle.writesDepth = false;
    particle.optedIn = false;
    if (Eligible(particle)) return 11;
    particle.optedIn = true;
    particle.indexed = true;
    if (Eligible(particle)) return 12;
    return 0;
}
