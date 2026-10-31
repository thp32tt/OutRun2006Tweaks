#!/usr/bin/env python3
"""Live x64 host native->SBS->native pixels and fallback/source-route integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
host = (root/"vrhost/src/main.cpp").read_text()
helper = (root/"vrhost/src/runtime/native_stereo_source_route.hpp").read_text()
smoke = (root/"vrhost/tests/native_direct_eye_pair_smoke.cpp").read_text()
workflow = (root/".github/workflows/dx11-fast-structural.yml").read_text()

def wired(source, logic):
    direct = source.split("bool CommitDirectStereoSource(",1)[1].split(
        "void DiscardUnmatchedStereoSource()",1)[0]
    invalidator = source.split("void DiscardUnmatchedStereoSource()",1)[1].split(
        "bool DirectTransportReady()",1)[0]
    sbs = source.split("bool CommitStereoSource()",1)[1].split(
        "OutRunVrNativeEyePair::StereoSourceRoute StereoSource()",1)[0]
    projection = source.split("bool RenderProjection(",1)[1].split(
        "bool RenderMenuPlaneTo(",1)[0]
    chooser = source.split("OutRunVrNativeEyePair::StereoSourceRoute StereoSource()",1)[1].split(
        "bool RenderProjection(",1)[0]
    return (all(x in direct for x in (
        "stereoSourceValid_ = false;", "directFrameValid_=true")) and
        all(x in invalidator for x in (
            "directFrameValid_ = false;", "directTransportReady_ = false;",
            "stereoSourceValid_ = false;")) and
        "OutRunVrNativeEyePair::SameStereoFrameIdentity(before,after)" in source and
        "compositor.DiscardUnmatchedStereoSource();" in source and
        all(x in sbs for x in (
            "context_->CopyResource(stereoSource_, source_);",
            "directFrameValid_ = false;",
            "directTransportReady_ = false;",
            "stereoSourceValid_ = true;")) and
        sbs.index("context_->CopyResource(stereoSource_, source_);") <
        sbs.index("directFrameValid_ = false;") <
        sbs.index("stereoSourceValid_ = true;") and
        "ChooseStereoSource(" in chooser and
        "directSnapshotLeftSrv_ != nullptr" in chooser and
        "directSnapshotRightSrv_ != nullptr" in chooser and
        "stereoSourceSrv_ != nullptr" in chooser and
        "const auto sourceRoute = StereoSource();" in projection and
        "sourceRoute == OutRunVrNativeEyePair::StereoSourceRoute::DirectGpu" in projection and
        "sourceRoute == OutRunVrNativeEyePair::StereoSourceRoute::None" in projection and
        "RenderTo(projection_.rtvs[image][0]" in projection and
        "RenderTo(projection_.rtvs[image][1]" in projection)

assert wired(host,helper), "host must display the last successful direct/SBS frame"
# Mutate the target routine, not an unrelated earlier Reset() assignment.
def remove_from_routine(source, begin, end, token):
    prefix, tail = source.split(begin, 1)
    section, suffix = tail.split(end, 1)
    assert token in section, token
    return prefix + begin + section.replace(token, "/* removed */", 1) + end + suffix

for begin, end, token in (
    ("bool CommitDirectStereoSource(", "void DiscardUnmatchedStereoSource()",
     "stereoSourceValid_ = false;"),
    ("void DiscardUnmatchedStereoSource()", "bool DirectTransportReady()",
     "directFrameValid_ = false;"),
    ("void DiscardUnmatchedStereoSource()", "bool DirectTransportReady()",
     "directTransportReady_ = false;"),
    ("void DiscardUnmatchedStereoSource()", "bool DirectTransportReady()",
     "stereoSourceValid_ = false;"),
    ("else if(sourceReady||directFrame)", "const bool grace=",
     "compositor.DiscardUnmatchedStereoSource();"),
    ("const bool same=renderFrames.Read(after)", "if(sourceReady&&same)",
     "OutRunVrNativeEyePair::SameStereoFrameIdentity(before,after)"),
    ("bool CommitStereoSource()", "OutRunVrNativeEyePair::StereoSourceRoute StereoSource()",
     "directFrameValid_ = false;"),
    ("bool CommitStereoSource()", "OutRunVrNativeEyePair::StereoSourceRoute StereoSource()",
     "directTransportReady_ = false;"),
    ("bool RenderProjection(", "bool RenderMenuPlaneTo(",
     "const auto sourceRoute = StereoSource();"),
    ("bool RenderProjection(", "bool RenderMenuPlaneTo(",
     "sourceRoute == OutRunVrNativeEyePair::StereoSourceRoute::DirectGpu"),
):
    assert not wired(remove_from_routine(host, begin, end, token), helper), token
assert "StereoSourceRoute::Sbs" in helper
assert "StereoSourceRoute::None" in helper
assert "ChooseStereoSource(false,true,true,true,true)" in smoke
assert "ChooseStereoSource(true,true,true,false,true)" in smoke
assert "test_dx11_host_source_switch_00718.py" in workflow
assert "dx11_host_source_switch_probe_00718.cpp" in workflow
print("PASS 00718: host DirectGPU->SBS->DirectGPU native eye pixel route, fallback, OpenXR Draw")
