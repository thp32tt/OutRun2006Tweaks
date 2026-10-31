#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r30=(ROOT/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
hooks=(ROOT/"src/hooks_graphics.cpp").read_text(encoding="utf-8")
renderer=(ROOT/"src/vr/game/outrun_renderer.cpp").read_text(encoding="utf-8")
contract=(ROOT/"src/vr/game/projected_lens_inline_source.hpp").read_text(encoding="utf-8")
semantics=(ROOT/"src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")
def body(text,sig):
 s=text.index(sig); b=text.index("{",s); d=0
 for i in range(b,len(text)):
  d += 1 if text[i]=="{" else -1 if text[i]=="}" else 0
  if d==0:return text[s:i+1]
 raise AssertionError(sig)
classifier=body(r30,"R30ScreenSpaceKind R30ClassifyScreenSpacePass(")
builder=body(r30,"bool R30BuildScreenSpaceEyeConstants(")
dispatch=body(r30,"HRESULT R30TryScreenSpaceFovDraw(")
exact=body(r30,"bool R30GetExactInlineProjectedLensRawWvp(")
axis=body(r30,"bool R30GetExactOpaqueAxisLensLiveWvp(")
assert "if (semanticProjectedScreen)" in classifier
assert "if (exactOpaqueAxisLensPmt)" in classifier
assert classifier.index("if (semanticProjectedScreen)") < classifier.index("if (exactOpaqueAxisLensPmt)")
assert "ExactProjectedLensAxisPmtActive()" in classifier
assert "if (semanticProjectedScreen || semanticSceneEffect)" not in classifier
tail=builder[builder.index("if (screenKind == R30ScreenSpaceKind::ProjectedScreenEffect2D)"):]
for t in ("GetLatchedHeadInverse(","const D3DMATRIX identityEye = IdentityMatrix();",
          "for (int eye = 0; eye < 2; ++eye)","ProjectionFromFov(",
          "stereo.eyeFov[eye]","BuildProjectedSunRay(",
          "identityEye, eyeProjection, projected,",
          "std::memcpy(eyeConstants[eye], &projectedT,","VR R85 FLARE RAY:"):
 assert t in tail,t
assert "R30GetExactInlineProjectedLensRawWvp(" in builder
assert "R30GetExactOpaqueAxisLensLiveWvp(" in builder
# Exact physical 405890 PMT ownership is stronger than historical inline
# wrapper provenance, so it must be attempted first.
assert builder.index("R30GetExactOpaqueAxisLensLiveWvp(") < builder.index("R30GetExactInlineProjectedLensRawWvp(") < builder.index("R44GetOwnedRawOverlayWvp(original)")
for t in ("CurrentLensAxisOpaquePmt",
          "ExactProjectedLensAxisPmtActive()","GetVertexShaderConstantF(",
          "EXACT_405890_PMT_NATIVE_C64_PRE_EYE"):
 assert t in axis,t
assert "GetCurrentShaderEpoch(" not in axis
assert "IsProjectedLensPmtObject" in axis
for obj in ("0x570002u","0x570006u","0x57000Fu","0x570010u",
            "0x57000Eu","0x570003u","0x570004u","0x570005u",
            "0x570007u","0x570008u","0x57000Au","0x570009u",
            "0x57000Bu","0x57000Cu","0x57000Du"):
 assert obj in semantics,obj
assert "IsProjectedLensPmtObject" in semantics
assert "CurrentLensDeferredPhysical" not in axis
assert "QueueRenderActive()" not in axis
assert "405890 has already loaded this exact entry's matrix" in axis
assert "activeLensSource.objectId == 0x570008u" not in tail
assert "activeLensSource.callsite == 2u" not in tail
assert "activeLensSource.ordinal == 2u" not in tail
axis_pmt_scope=body(hooks,"static void __cdecl TraceLensOpaquePmtEntry(")
axis_flush_scope=body(hooks,"static void TraceLensOpaqueFlush(")
assert axis_pmt_scope.index("ScopedLensAxisOpaquePmtOwner") < axis_pmt_scope.index("!Settings::VREnabled || !Settings::VRTelemetry")
assert "IsProjectedLensPmtObject(entry[14])" in axis_pmt_scope
assert "ScopedRenderSemantic exactSceneProjectedScope" in axis_flush_scope
assert "RenderScope::ProjectedScreenEffect2D" in axis_flush_scope
assert axis_flush_scope.index("ScopedRenderSemantic exactSceneProjectedScope") < axis_flush_scope.index("Module::fn_ptr<LensOpaqueFlushFn>(0x52C0)();")
assert axis_flush_scope.index("ScopedLensAxisOpaqueFlushOwner") < axis_flush_scope.index("const bool trace = Settings::VREnabled && Settings::VRTelemetry")
assert "deferred.objectId == 0x570008u" in axis_flush_scope
assert "deferred.ordinal == 1u" in axis_flush_scope
assert "exactProjectedLensCameraSynced" in tail
assert "GetLastProjectedLensRawWvp(out, raw)" in exact
for t in ("CurrentInlinePmt","OwnsRawWvp(","GetCurrentLatchedPoseEpoch()",
          "SAME_SOURCE_INLINE_PMT_NATIVE_C64"):
 assert t in exact,t
assert "R30GetExactC993SunDiscLiveWvp(" not in r30
assert "GetVertexShaderConstantF(" not in exact
for t in ("0x570002u","0x570006u","!IsExactInlineC993Object(0x57000Fu)",
          "!IsExactInlineC993Object(0x570010u)","currentSourceSerial == raw.sourceSerial",
          "currentObject == pmt.objectId","currentPoseEpoch == raw.poseEpoch",
          "currentShader == raw.shader","currentShaderEpoch == raw.shaderEpoch"):
 assert t in contract,t
# Exact PMT ownership must exist before the telemetry-only diagnostic early return.
pmt=body(hooks,"static void __cdecl TraceLensOpaquePmtEntry(")
assert pmt.index("ScopedInlinePmt") < pmt.index("!Settings::VREnabled || !Settings::VRTelemetry")
flush=body(hooks,"static void TraceLensOpaqueFlush(")
assert "ScopedInlineFlush" in flush
assert flush.index("ScopedInlineFlush") < flush.index("const bool trace =")
for t in ("ProjectedLensRawWvp.Reset();","VR LENS PROJECTED RAW WVP CAPTURE",
          "GetLastProjectedLensRawWvp(","CurrentInlinePmt",
          "CanPublishCompleteOriginalCentreWvp(\n\t\t\t\t\t\t\ttrue, nativeGameWvp)"):
 assert t in renderer,t
assert dispatch.count("const HRESULT leftHr = actualDraw();")==1
assert dispatch.count("rightHr = actualDraw();")==1
print("PASS R26 complete sun-family exact 405890 PMT ownership; D44B/D79B c64 stays raw until one R85 angular-ray eye transform")
