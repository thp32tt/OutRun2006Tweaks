#!/usr/bin/env python3
"""R26+HUD stereo-only DirectGPU TEST source safety contract (not HMD proof)."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
r9 = (root/"src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
r13 = (root/"src/vr/d3d9/stereo_renderer_r13.cpp").read_text(encoding="utf-8")
r20 = (root/"src/vr/d3d9/stereo_renderer_r20.cpp").read_text(encoding="utf-8")
r7 = (root/"src/vr/d3d9/stereo_renderer_r7.inc").read_text(encoding="utf-8")
def section(s, first, last):
    assert s.count(first)==1, first
    return s.split(first,1)[1].split(last,1)[0]
guard = section(r9, "bool R9NoMonoForActiveVr() noexcept", "std::uint64_t R9MonoBackupDraws")
assert "Settings::VRDirectGpuOnly" in guard
assert "Settings::VRHmdlessDebugMode == 0" in guard
assert "HostDirectTransportReady()" in guard
assert "StereoWanted()" in guard
clear = section(r9,"HRESULT __stdcall ClearDestR9(","template <typename ActualDraw, typename LegacyDraw>")
draw = section(r9,"HRESULT R9ExecuteDraw(","HRESULT __stdcall DrawPrimitiveDestR9(")
present = section(r9,"HRESULT __stdcall PresentDestR9(","HRESULT __stdcall ResetDestR9(")
# Original 2D and offscreen still use the original single-execution branches.
assert clear.index("if (!wanted || !mainTarget)") < clear.index("if (R9NoMonoForActiveVr())")
assert draw.index("if (!wanted || !mainTarget)") < draw.index("if (R9NoMonoForActiveVr())")
# No independent mono clear/draw or allocation on VR-only branch.
sc = clear.split("if (R9NoMonoForActiveVr())",1)[1].split("// A later R30/",1)[0]
sd = draw.split("if (R9NoMonoForActiveVr())",1)[1].split("else if (R9MonoBackupGap)",1)[0]
assert "R9ClearCallbackHook.stdcall" in sc
assert "R9MonoSeeded = false;" in sc
assert "R9MonoBackupGap = true;" in sc
assert "R9EnsureMonoResources" not in sc
assert "R9ReplayMonoClear" not in sc
assert "R9ReplayMonoDraw" not in sd
assert "R9EnsureMonoResources" not in sd
assert "R9MonoSeeded = false;" in sd
assert "++R9StereoOnlySavedDraws;" in sd
assert "hr = legacyDraw();" in draw
assert "if (FrameStereoIncomplete)" in draw
# R20 replaces mono RT/depth dependency with verified right-eye baseline.
depth = section(r20,"void R20ObserveFullDepthSeed(","void R20CancelInitialSeed(")
seed = section(r20,"bool R20BuildCompleteColorBaseline(","DWORD WINAPI R20InstallThread(")
assert "(!R9NoMonoForActiveVr() && (!R9MonoDepth || R9MonoBackupGap))" in depth
assert "R9NoMonoForActiveVr() ? RightEyeDepth != nullptr : R9MonoDepth != nullptr" in depth
assert "BackBuffer, nullptr, RightEyeSurface" in seed
assert "R9NoMonoForActiveVr()" in seed
assert "R9MonoSeeded = !R9NoMonoForActiveVr();" in seed
assert "R9MonoBackupGap = R9NoMonoForActiveVr();" in seed
assert "R20DepthHistorySafeForInitialSeed(device)" in seed
assert "R20CancelInitialSeed(device)" in seed
# Unsafe MRT/query drawing executes on the real target once and poisons stereo.
safety = section(r13,"HRESULT R13DrawMonoShadowOnce(","R13EffectSnapshot R13CaptureDrawTimeEffect(")
assert "if (R9NoMonoForActiveVr())" in safety
assert "FrameStereoIncomplete = true;" in safety
assert "return actualDraw();" in safety
assert safety.index("if (R9NoMonoForActiveVr())") < safety.index("R9BindMonoTarget(")
# Failed/incomplete frames never become active VR frame packets. After a
# completed verified direct frame, keep its previous transport state.
assert "const bool frameEligible = stereoRequested && FrameHadWorldStereo" in present
assert "!FrameRightDrawFailed && !FrameStereoIncomplete" in present
assert "A producer publication is NOT proof of host acceptance." in present
assert "const bool holdLastGood =" in present
assert "stereoRequested && directOnly && R9NoMonoForActiveVr();" in present
assert "R9LastCompletedDirectVrFrame" not in r9
assert "if (!holdLastGood && (!directOnly || !stereoRequested || directTransport))" in present
assert "if (holdLastGood)" in present
assert "PublishStereoState(fallback, false" in present
host=(root/"vrhost/src/main.cpp").read_text(encoding="utf-8")
assert "matchedStereoDirect || GetTickCount64()-lastStereoMatchMs<=StereoGraceMs" in host
assert "context_->CopyResource(directPendingLeft_, directLeft_[slot]);" in host
assert "context_->CopyResource(directPendingRight_, directRight_[slot]);" in host
assert "matchedStereoValid=false" in host
assert "matchedStereoDirect=false" in host
assert "bool PreparePendingDirectStereoSource(" in host
assert "bool AcceptPendingDirectStereoSource()" in host
assert "void DiscardPendingDirectStereoSource()" in host
assert "sourceReady=compositor.PreparePendingDirectStereoSource(before);" in host
assert "compositor.AcceptPendingDirectStereoSource()" in host
assert "compositor.DiscardPendingDirectStereoSource();" in host
# CopyResource may already be queued when CreateQuery fails; never recycle
# those candidate allocations without a fence.
candidate=host.split("bool PreparePendingDirectStereoSource(",1)[1].split("bool AcceptPendingDirectStereoSource()",1)[0]
queryFailure=candidate.split("if (FAILED(device_->CreateQuery(&query, &fence)) || !fence)",1)[1].split("context_->End(fence)",1)[0]
assert "ReleaseCom(directPendingLeft_);" in queryFailure
assert "ReleaseCom(directPendingRight_);" in queryFailure
assert "directTransportReady_ = false;" in queryFailure
assert "directFrameValid_ = false;" not in candidate

assert "directFrameValid_=false;" not in host.split("bool PrepareDirectStereoSource(",1)[1].split("bool PreparePendingDirectStereoSource(",1)[0]
assert "if (R9FrameMonoPolicyLatched)" in guard
assert "R9FrameMonoPolicyLatched = true;" in clear
assert "R9FrameMonoPolicyLatched = false;" in present
assert "R9FrameMonoPolicyLatched = false;" in r13
assert "before.state==OutRunVR::StereoDisabled && before.frameId==0" in host
assert "DirectTransportFrameReadyAfterPresent" in r7
assert "stereoOnlySavedDraw={}" in r9
assert "stereoOnlySavedClear={}" in r9
assert "lastGoodHeld={}" in r9
assert "now - R9GapProbeLastMs < 10000" in r9
assert "R9MonoElisionArmed" not in r9
print("PASS R9: DirectGPU VR is two-eye only; original 2D/offscreen paths preserved")
print("PASS R20: right-eye color/depth baseline replaces mono bootstrap dependency")
print("PASS R13: side-effecting unsafe draw executes once, incomplete stereo dropped")
print("PASS Present: last-good VR frame held, host-private left/right snapshots retained")
print("PASS OpenXR: staged stereo pair accepted only after GPU+metadata proofs; SBS 250ms preserved")
print("HMD_RUNTIME=UNTESTED; visual safety and GPU improvement require Quest validation")
