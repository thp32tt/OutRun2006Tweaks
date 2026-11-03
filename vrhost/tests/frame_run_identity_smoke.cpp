#include "vr/ipc/protocol.hpp"

#include <cstdint>

int main()
{
    OutRunVR::SharedRenderFrameRing ring{};
    OutRunVR::SharedRenderFrameState frame{};

    ring.clientPid = 1001;
    ring.reserved0 = 0xA5A50001u;
    frame.clientPid = 1001;
    frame.reserved[OutRunVR::RenderFrameRunGenerationIndex] = 0xA5A50001u;

    if (!OutRunVR::RenderFrameRunIdentityMatches(ring, frame)) return 1;

    frame.clientPid = 1002;
    if (OutRunVR::RenderFrameRunIdentityMatches(ring, frame)) return 2;
    frame.clientPid = 1001;

    frame.reserved[OutRunVR::RenderFrameRunGenerationIndex] = 0xA5A50002u;
    if (OutRunVR::RenderFrameRunIdentityMatches(ring, frame)) return 3;
    frame.reserved[OutRunVR::RenderFrameRunGenerationIndex] = 0xA5A50001u;

    ring.clientPid = 0;
    if (OutRunVR::RenderFrameRunIdentityMatches(ring, frame)) return 4;
    ring.clientPid = 1001;

    ring.reserved0 = 0;
    if (OutRunVR::RenderFrameRunIdentityMatches(ring, frame)) return 5;

    // Simulate a fast game restart: the old slot still has the previous
    // generation but the ring has been claimed by the new producer run.
    ring.reserved0 = 0xA5A50002u;
    if (OutRunVR::RenderFrameRunIdentityMatches(ring, frame)) return 6;

    frame.reserved[OutRunVR::RenderFrameRunGenerationIndex] = ring.reserved0;
    if (!OutRunVR::RenderFrameRunIdentityMatches(ring, frame)) return 7;

    return 0;
}
