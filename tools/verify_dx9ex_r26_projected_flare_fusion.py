#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
def body(sig):
 s=text.index(sig); b=text.index("{",s); d=0
 for i in range(b,len(text)):
  d += 1 if text[i]=="{" else -1 if text[i]=="}" else 0
  if d==0:return text[s:i+1]
 raise AssertionError(sig)
classifier=body("R30ScreenSpaceKind R30ClassifyScreenSpacePass(")
builder=body("bool R30BuildScreenSpaceEyeConstants(")
dispatch=body("HRESULT R30TryScreenSpaceFovDraw(")
assert "if (semanticProjectedScreen)" in classifier
assert "if (semanticProjectedScreen || semanticSceneEffect)" not in classifier
tail=builder[builder.index("if (screenKind == R30ScreenSpaceKind::ProjectedScreenEffect2D)"):]
for t in ("GetLatchedHeadInverse(","const D3DMATRIX identityEye = IdentityMatrix();","for (int eye = 0; eye < 2; ++eye)","ProjectionFromFov(","stereo.eyeFov[eye]","BuildProjectedSunRay(","identityEye, eyeProjection, projected,","std::memcpy(eyeConstants[eye], &projectedT,","VR R85 FLARE RAY:"): assert t in tail,t
assert "std::memcpy(eyeConstants[0], &stockT" not in tail
assert "std::memcpy(eyeConstants[1], &stockT" not in tail
assert "VR R69 FLARE FUSION" not in tail
assert "R30GetExactC993SunDiscLiveWvp(" in text
lenslive=body("bool R30GetExactC993SunDiscLiveWvp(")
for t in (
 "SunDiscObject = 0x570002u",
 "call.callsite != 1",
 "flush.origin != LensOpaqueFlushOrigin::Inline405360",
 "flush.sourceSerial != call.sourceSerial",
 "flush.sequence != call.lastC993Sequence",
 "pmt.flushSerial != flush.serial",
 "pmt.objectId != SunDiscObject",
 "pmt.pass != 1",
 "liveShaderIdentity != cachedShader",
 "GetVertexShaderConstantF(",
 "EXACT_CURRENT_C993_PMT_LIVE_REGISTER",
): assert t in lenslive,t
assert "!R30GetExactC993SunDiscLiveWvp(device, original)" in builder
assert dispatch.count("const HRESULT leftHr = actualDraw();")==1
assert dispatch.count("rightHr = actualDraw();")==1
print("PASS R26 flare angular ray uses separate asymmetric L/R FOV; physical draw count unchanged")
