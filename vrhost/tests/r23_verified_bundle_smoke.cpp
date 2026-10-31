#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "runtime/r23_verified_bundle.hpp"
#include "runtime/native_stereo_source_route.hpp"

#include <cassert>

int main()
{
    using namespace OutRunVrR23VerifiedBundle;

    Invalidate();
    Snapshot snapshot{};
    assert(Read(snapshot));
    assert(!IsFresh(snapshot));

    OutRunVR::SharedRenderFrameState frame{};
    frame.magic = OutRunVR::RenderFrameMagic;
    frame.protocolVersion = OutRunVR::RenderFrameProtocolVersion;
    frame.structSize = sizeof(frame);
    frame.state = OutRunVR::StereoSbsActive;
    frame.frameId = 42;
    frame.sourcePoseSequence = 77;
    frame.presentQpc = 123456;

    Publish(frame, SourceKind::DirectGpu, 0);
    assert(ReadFresh(snapshot));
    assert(snapshot.kind == SourceKind::DirectGpu);
    assert(snapshot.frameId == 42);
    assert(snapshot.poseSequence == 77);
    assert(snapshot.presentQpc == 123456);
    assert(Matches(frame, SourceKind::DirectGpu));
    assert(!Matches(frame, SourceKind::ClassicSbs));

    // Identity fields inside the copied Frame.v2 must agree with the atomic
    // bundle identity. A mixed texture/pose publication must fail freshness.
    snapshot.frame.frameId = 43;
    assert(!IsFresh(snapshot, snapshot.publishedAtMs));

    assert(Read(snapshot));
    assert(IsFresh(snapshot, snapshot.publishedAtMs));
    assert(!IsFresh(snapshot,
        snapshot.publishedAtMs + MaxPresentationAgeMs + 1));

    // GPU staging must observe one immutable game frame / eye-pose pair.
    auto candidate=frame;
    candidate.flags=OutRunVR::RenderFrameDirectGpuTransport;
    candidate.clientPid=514;
    candidate.reserved[OutRunVR::RenderFrameDirectLeftHandleIndex]=11;
    candidate.reserved[OutRunVR::RenderFrameDirectRightHandleIndex]=12;
    candidate.reserved[OutRunVR::RenderFrameDirectGenerationIndex]=7;
    candidate.reserved[OutRunVR::RenderFrameDirectSlotIndex]=2;
    candidate.eye[0].orientation[3]=1.f;
    candidate.eye[1].orientation[3]=1.f;
    candidate.eye[0].fov.angleLeft=-0.7f;
    auto concurrent=candidate;
    assert(OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    ++concurrent.sequence; // A settled seqlock sequence is not frame identity.
    assert(OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent.eye[1].position[0]=0.032f;
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent=candidate;
    concurrent.eye[0].fov.angleLeft=-0.8f;
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent=candidate;
    ++concurrent.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent=candidate;
    ++concurrent.reserved[OutRunVR::RenderFrameDirectSlotIndex];
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent=candidate;
    ++concurrent.reserved[OutRunVR::RenderFrameDirectRightHandleIndex];
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent=candidate;
    ++concurrent.clientPid;
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent=candidate;
    ++concurrent.frameId;
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));
    concurrent=candidate;
    concurrent.flags=0; // GPU -> SBS cannot keep old native-eye handles.
    assert(!OutRunVrNativeEyePair::SameStereoFrameIdentity(candidate,concurrent));

    Invalidate();
    assert(!ReadFresh(snapshot));
    return 0;
}
