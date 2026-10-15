#include "../../src/vr/d3d9/stereo_completion_gate.hpp"
#include <cassert>

// Portable changed-area regression: this is the admission used by both R30
// lower fallback and R33 top-level World/HUD paths. All failure permutations
// must reject publication; only two GPU submissions AND restored state pass.
int main()
{
    using OutRunVR::StereoCompletion::CanPublishStereoDraw;
    for (int left = 0; left < 2; ++left)
        for (int right = 0; right < 2; ++right)
            for (int restored = 0; restored < 2; ++restored)
                assert(CanPublishStereoDraw(left != 0, right != 0,
                    restored != 0) == (left && right && restored));
    return 0;
}
