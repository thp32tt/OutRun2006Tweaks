#!/usr/bin/env python3
"""EXT16-010 v0.03 launch/host parity and active eye/RT/depth route gate.
Source-only: no HMD, p95 or frame-rate claims.
"""
import hashlib
from pathlib import Path
BASELINE="2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7"
PROTECTED_BLOBS={
  "Start-OutRun.cmd": "4e6206eed8bc7062a73471b04de412240ef94b62",
  "Start-OutRun-VR.cmd": "506cae7420f7ee36373cf2dcfd9a0addd5b918f1",
  "vrhost/src/main.cpp": "57aa8b3fe3ec1b057b4493a4a29073e5eb0a36c7",
  "vrhost/src/runtime/vr_runtime.hpp": "b26080f5b749de907ee1ea154f2142de205f8eda",
  "vrhost/src/runtime/menu_projection_pair.hpp": "36b8881a59b6bd28ff4bbbc8da0fcaa3f67be387",
  "vrhost/src/runtime/menu_content_aspect.hpp": "bd3b1885816cc7b1bcd2ff48357c09c956893732",
  "vrhost/src/runtime/projection_pair_pipeline.hpp": "fd1e821d86ea84a7ce31d594d910d81259230c58",
  "vrhost/src/runtime/openxr_api_compat.hpp": "9a75f514bea093c6af8d2eba0cf4a8a4e2130e6d",
  "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp": "0028a41b16d070b19102b749ead6cd39747c035b",
  "src/vr/ui/menu_letterbox_geometry.hpp": "9b8119eb4dcaa7ef6f2b0d12a5432b3d7d55f369"
}
R7="src/vr/d3d9/stereo_renderer_r7.inc"
HOOK="src/hooks_graphics.cpp"
FENCE="src/vr/game/external_car_atomic_precommit.hpp"
EYE="src/vr/game/external_car_eye_transform_proof.hpp"
MARKERS={
R7:(
"frame.presentationMode=GameplayActive()?OutRunVR::PresentationGameplay:OutRunVR::PresentationTheater;",
"rightHr=SetRenderTargetHook.stdcall<HRESULT>(device,0u,RightEyeSurface);",
"rightHr=SetDepthStencilSurfaceHook.stdcall<HRESULT>(device,RightEyeDepth);",
"rightHr=device->SetViewport(&savedViewport);",
"SetExternalPbrEyeConstants(device,draw,0)",
"SetExternalPbrEyeConstants(device,draw,1)",
"DistinctFiniteExternalEyeTransforms(",
"CanCompleteExternalStereoDraw(",
"MaySubmitExternalCarLiveEye()",
),
HOOK:("PlayerCallbackHook.ccall<void>(player);",
"static_assert(!OutRunVR::DinoSidecar::MaySkipRetailPlayerWrapper());"),
FENCE:("inline constexpr bool RuntimeExternalCarAtomicStageReady() noexcept {\n    return false;",),
EYE:("separationSq>separationSqMin","cameraCentre(leftView)-cameraCentre(rightView)"),
}
def canonical_text(data):
 # Windows Git checkout may write CRLF; Git object bytes are LF.
 return data.replace(b"\r\n",b"\n")
def blob_sha(data):
 data=canonical_text(data)
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def check(files, protected=PROTECTED_BLOBS):
 errors=[]
 for path,expected in protected.items():
  if path not in files or blob_sha(files[path])!=expected:errors.append("PROTECTED_DRIFT:"+path)
 for path,needles in MARKERS.items():
  s=canonical_text(files.get(path,b"")).decode("utf-8",errors="replace")
  for needle in needles:
   if needle not in s:errors.append("ROUTE_DRIFT:"+path+":"+needle)
 return errors
def test_negative():
 example={name:("baseline:"+name).encode() for name in PROTECTED_BLOBS}
 protected={p:blob_sha(v) for p,v in example.items()}
 for path,markers in MARKERS.items():example[path]="\n".join(markers).encode()
 assert not check(example,protected)
 windows={p:v.replace(b"\n",b"\r\n") for p,v in example.items()}
 assert not check(windows,protected), "Windows CRLF checkout rejected"
 def reject(path,old,new):
  altered=dict(example)
  assert old in altered[path]
  altered[path]=altered[path].replace(old,new)
  assert check(altered,protected),(path,old)
 reject(R7,b"0u,RightEyeSurface",b"0u,BackBuffer")
 reject(R7,b"device,RightEyeDepth",b"device,TrackedDepthStencil")
 reject(R7,b"SetExternalPbrEyeConstants(device,draw,1)",b"SetExternalPbrEyeConstants(device,draw,0)")
 reject(R7,b"PresentationGameplay:OutRunVR::PresentationTheater",b"PresentationTheater:OutRunVR::PresentationTheater")
 reject("Start-OutRun.cmd",b"baseline",b"modified")
 malformed=dict(windows)
 malformed["Start-OutRun.cmd"]=malformed["Start-OutRun.cmd"].replace(b"baseline",b"modified")
 assert check(malformed,protected), "Real Windows CRLF mutation escaped"
 reject("vrhost/src/main.cpp",b"baseline",b"modified")
 reject("vrhost/src/runtime/openxr_api_compat.hpp",b"baseline",b"modified")
 reject("vrhost/src/runtime/projection_pair_pipeline.hpp",b"baseline",b"modified")
 reject("vrhost/src/runtime/menu_projection_pair.hpp",b"baseline",b"modified")
 reject(HOOK,b"PlayerCallbackHook.ccall<void>(player);",b"// skipped")
 reject(FENCE,b"return false;",b"return true;")
 reject(EYE,b"cameraCentre(leftView)-cameraCentre(rightView)",b"leftProjection[8]!=rightProjection[8]")
 print("EXT16_010_PARITY_NEGATIVE_12_PASS")
if __name__=="__main__":
 import argparse
 a=argparse.ArgumentParser()
 a.add_argument("--self-test",action="store_true")
 a.add_argument("--root",type=Path,default=Path("."))
 cfg=a.parse_args()
 if cfg.self_test:test_negative()
 names=set(PROTECTED_BLOBS)|set(MARKERS)
 files={name:(cfg.root/name).read_bytes() for name in names}
 errors=check(files)
 for e in errors:print("EXT16_010_FAIL",e)
 if errors:raise SystemExit(1)
 print("EXT16_010_V003_SOURCE_PARITY_PASS",BASELINE)
 print("HMD_FPS_P95_UNTESTED")
