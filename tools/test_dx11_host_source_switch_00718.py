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
        "bool DirectTransportReady()",1)[0]
    sbs = source.split("bool CommitStereoSource()",1)[1].split(
        "OutRunVrNativeEyePair::StereoSourceRoute StereoSource()",1)[0]
    projection = source.split("bool RenderProjection(",1)[1].split(
        "bool RenderMenuPlaneTo(",1)[0]
    chooser = source.split("OutRunVrNativeEyePair::StereoSourceRoute StereoSource()",1)[1].split(
        "bool RenderProjection(",1)[0]
    return (all(x in direct for x in (
        "stereoSourceValid_ = false;", "directFrameValid_=true")) and
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
        "ctx->Draw" not in projection and
        "context_->Draw" in projection)

assert wired(host,helper), "host must display the last successful direct/SBS frame"
for token in ("stereoSourceValid_ = false;", "directFrameValid_ = false;",
              "directTransportReady_ = false;",
              "const auto sourceRoute = StereoSource();",
              "sourceRoute == OutRunVrNativeEyePair::StereoSourceRoute::DirectGpu"):
    assert not wired(host.replace(token, "/* removed */",1),helper), token
assert "StereoSourceRoute::Sbs" in helper
assert "StereoSourceRoute::None" in helper
assert "ChooseStereoSource(false,true,true,true,true)" in smoke
assert "ChooseStereoSource(true,true,true,false,true)" in smoke
assert "test_dx11_host_source_switch_00718.py" in workflow
assert "dx11_host_source_switch_probe_00718.cpp" in workflow
print("PASS 00718: host DirectGPU->SBS->DirectGPU native eye pixel route, fallback, OpenXR Draw")
