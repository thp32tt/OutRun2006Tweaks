from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, got {count}")
    return text.replace(old, new, 1)

# 1) Shared enums / renderer diagnostic API. ABI sizes and layouts stay unchanged.
p = Path('src/vr_shared.hpp')
s = p.read_text(encoding='utf-8')
s = replace_once(s,
'''        StereoFailureDepthUnsynchronized = 15,\n        StereoFailureClearFailed = 16,\n''',
'''        StereoFailureDepthUnsynchronized = 15,\n        StereoFailureClearFailed = 16,\n        StereoFailureWorldClassificationFailed = 17,\n        StereoFailureStencilUnsynchronized = 18,\n''', 'failure enum')
s = replace_once(s,
'''    bool GetLastVerifiedWvp(float outConstants[16], std::uint32_t& generation,\n        std::uint32_t& poseSequence, std::uintptr_t& shaderIdentity,\n        std::uint64_t& shaderSerial);\n''',
'''    bool GetLastVerifiedWvp(float outConstants[16], std::uint32_t& generation,\n        std::uint32_t& poseSequence, std::uintptr_t& shaderIdentity,\n        std::uint64_t& shaderSerial);\n    std::uint64_t GetBeginSceneCallCount();\n''', 'renderer diagnostic API')
p.write_text(s, encoding='utf-8')

# 2) Expose BeginScene count for Present-frame diagnostics.
p = Path('src/vr_renderer_probe.cpp')
s = p.read_text(encoding='utf-8')
s = replace_once(s,
'''\tbool GetLatchedStereoFrame(LatchedStereoFrame& out)\n\t{\n\t\tout = LatchedStereo;\n\t\treturn out.valid && out.poseSequence != 0;\n\t}\n\n\tbool GetRendererBaseProjection(float outMatrix[16])\n''',
'''\tbool GetLatchedStereoFrame(LatchedStereoFrame& out)\n\t{\n\t\tout = LatchedStereo;\n\t\treturn out.valid && out.poseSequence != 0;\n\t}\n\n\tstd::uint64_t GetBeginSceneCallCount()\n\t{\n\t\treturn BeginSceneCalls;\n\t}\n\n\tbool GetRendererBaseProjection(float outMatrix[16])\n''', 'BeginScene API implementation')
p.write_text(s, encoding='utf-8')

# 3) Stereo integrity / telemetry hardening.
p = Path('src/vr_stereo.cpp')
s = p.read_text(encoding='utf-8')

s = replace_once(s,
'''\t\tbool RightDepthSynchronized = true;\n\t\tbool LastHostRenderEligible = false;\n\n\t\tULONGLONG LastSummaryMs = 0;\n''',
'''\t\tbool RightDepthSynchronized = true;\n\t\tbool RightStencilSynchronized = true;\n\t\tbool LastHostRenderEligible = false;\n\t\tbool FramePoseMismatchLogged = false;\n\n\t\tULONGLONG LastSummaryMs = 0;\n''', 'stencil/frame state')

s = replace_once(s,
'''\t\tstd::uint64_t MrtRejectedDraws = 0;\n\t\tstd::uint64_t RestoreFailures = 0;\n\t\tbool FirstStereoActiveLogged = false;\n''',
'''\t\tstd::uint64_t MrtRejectedDraws = 0;\n\t\tstd::uint64_t RestoreFailures = 0;\n\t\tstd::uint64_t WorldClassificationFailures = 0;\n\t\tstd::uint64_t OffscreenVerifiedWorldDraws = 0;\n\t\tstd::uint64_t PoseSequenceMismatchFrames = 0;\n\t\tstd::uint64_t MultiBeginScenePresents = 0;\n\t\tstd::uint64_t MaxBeginScenesPerPresent = 0;\n\t\tstd::uint64_t LastBeginSceneCountAtPresent = 0;\n\t\tstd::array<std::uint64_t, 32> FailureCounts{};\n\t\tbool FirstStereoActiveLogged = false;\n''', 'diagnostic counters')

s = replace_once(s,
'''\t\tbool FirstMrtRejectLogged = false;\n''',
'''\t\tbool FirstMrtRejectLogged = false;\n\t\tbool FirstOffscreenWorldLogged = false;\n\t\tbool FirstClassificationFailureLogged = false;\n''', 'diagnostic log flags')

s = replace_once(s,
'''\t\t\tif (hostEligible && !LastHostRenderEligible && TrackedDepthStencil)\n\t\t\t{\n\t\t\t\t// The left/game depth may have advanced while OpenXR asked us not to\n\t\t\t\t// render. Require the next full duplicated Z clear before reusing the\n\t\t\t\t// right-eye depth surface.\n\t\t\t\tRightDepthSynchronized = false;\n\t\t\t}\n''',
'''\t\t\tif (hostEligible && !LastHostRenderEligible && TrackedDepthStencil)\n\t\t\t{\n\t\t\t\t// The left/game depth/stencil may have advanced while OpenXR asked us\n\t\t\t\t// not to render. Require duplicated full clears before reusing them.\n\t\t\t\tRightDepthSynchronized = false;\n\t\t\t\tD3DSURFACE_DESC d{};\n\t\t\t\tif (SUCCEEDED(TrackedDepthStencil->GetDesc(&d)) && FormatHasStencil(d.Format))\n\t\t\t\t\tRightStencilSynchronized = false;\n\t\t\t}\n''', 'resume sync state')

# Forward declaration because StereoWanted appears before FormatHasStencil implementation.
s = replace_once(s,
'''\t\tbool GameplayActive()\n''',
'''\t\tbool FormatHasStencil(D3DFORMAT format);\n\n\t\tbool GameplayActive()\n''', 'FormatHasStencil forward declaration')

s = replace_once(s,
'''\t\tvoid PoisonFrame(OutRunVR::StereoFailureReason reason){FrameStereoIncomplete=true;if(FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=reason;}\n\n\t\tstruct DrawStereoState\n''',
'''\t\tvoid PoisonFrame(OutRunVR::StereoFailureReason reason)\n\t\t{\n\t\t\tFrameStereoIncomplete = true;\n\t\t\tif (FrameFailureReason == OutRunVR::StereoFailureNone)\n\t\t\t{\n\t\t\t\tFrameFailureReason = reason;\n\t\t\t\tconst auto index = static_cast<std::size_t>(reason);\n\t\t\t\tif (index < FailureCounts.size()) ++FailureCounts[index];\n\t\t\t}\n\t\t}\n\n\t\tenum class EyeBuildResult\n\t\t{\n\t\t\tNonWorld,\n\t\t\tWorldStereo,\n\t\t\tFatalError,\n\t\t};\n\n\t\tstruct DrawStereoState\n''', 'PoisonFrame + tri-state enum')

old_build_start = '''\t\tbool BuildEyeConstants(IDirect3DDevice9* device,\n\t\t\tconst OutRunVRRenderer::LatchedStereoFrame& stereo, DrawStereoState& state)\n\t\t{\n\t\t\tstd::uintptr_t shaderIdentity = 0;\n\t\t\tstd::uint64_t shaderSerial = 0;\n\t\t\tif (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))\n\t\t\t\treturn false;\n\n\t\t\tif (FAILED(device->GetVertexShaderConstantF(OutRunWvpRegister,\n\t\t\t\tstate.originalConstants, OutRunWvpRegisterCount)))\n\t\t\t\treturn false;\n\n\t\t\tfloat verifiedConstants[16]{};\n\t\t\tstd::uint32_t verifiedGeneration = 0;\n\t\t\tstd::uint32_t verifiedPoseSequence = 0;\n\t\t\tstd::uintptr_t verifiedShaderIdentity = 0;\n\t\t\tstd::uint64_t verifiedShaderSerial = 0;\n\t\t\tif (!OutRunVRRenderer::GetLastVerifiedWvp(verifiedConstants, verifiedGeneration,\n\t\t\t\tverifiedPoseSequence, verifiedShaderIdentity, verifiedShaderSerial))\n\t\t\t\treturn false;\n\t\t\tif (verifiedGeneration == 0 || verifiedPoseSequence != stereo.poseSequence ||\n\t\t\t\tverifiedShaderIdentity != shaderIdentity || verifiedShaderSerial != shaderSerial ||\n\t\t\t\t!FloatArrayNear(state.originalConstants, verifiedConstants, 16, VerifiedWvpEpsilon))\n\t\t\t\treturn false;\n\n\t\t\tD3DMATRIX projection{};\n\t\t\tD3DMATRIX invProjection{};\n\t\t\tif (!ReadProjection(projection) || !GetInverseProjection(projection, invProjection))\n\t\t\t\treturn false;\n'''
new_build_start = '''\t\tEyeBuildResult BuildEyeConstants(IDirect3DDevice9* device,\n\t\t\tconst OutRunVRRenderer::LatchedStereoFrame& stereo, DrawStereoState& state)\n\t\t{\n\t\t\tfloat verifiedConstants[16]{};\n\t\t\tstd::uint32_t verifiedGeneration = 0;\n\t\t\tstd::uint32_t verifiedPoseSequence = 0;\n\t\t\tstd::uintptr_t verifiedShaderIdentity = 0;\n\t\t\tstd::uint64_t verifiedShaderSerial = 0;\n\t\t\tif (!OutRunVRRenderer::GetLastVerifiedWvp(verifiedConstants, verifiedGeneration,\n\t\t\t\tverifiedPoseSequence, verifiedShaderIdentity, verifiedShaderSerial))\n\t\t\t\treturn EyeBuildResult::NonWorld;\n\n\t\t\tstd::uintptr_t shaderIdentity = 0;\n\t\t\tstd::uint64_t shaderSerial = 0;\n\t\t\tif (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))\n\t\t\t\treturn EyeBuildResult::FatalError;\n\t\t\tif (verifiedShaderIdentity != shaderIdentity || verifiedShaderSerial != shaderSerial)\n\t\t\t\treturn EyeBuildResult::NonWorld;\n\t\t\tif (verifiedGeneration == 0 || verifiedPoseSequence != stereo.poseSequence)\n\t\t\t\treturn EyeBuildResult::FatalError;\n\n\t\t\tif (FAILED(device->GetVertexShaderConstantF(OutRunWvpRegister,\n\t\t\t\tstate.originalConstants, OutRunWvpRegisterCount)))\n\t\t\t\treturn EyeBuildResult::FatalError;\n\t\t\tif (!FloatArrayNear(state.originalConstants, verifiedConstants, 16, VerifiedWvpEpsilon))\n\t\t\t\treturn EyeBuildResult::FatalError;\n\n\t\t\tD3DMATRIX projection{};\n\t\t\tD3DMATRIX invProjection{};\n\t\t\tif (!ReadProjection(projection) || !GetInverseProjection(projection, invProjection))\n\t\t\t\treturn EyeBuildResult::FatalError;\n'''
s = replace_once(s, old_build_start, new_build_start, 'BuildEyeConstants header')

s = replace_once(s,
'''\t\t\tif (!MatrixFinite(correctedWorldView))\n\t\t\t\treturn false;\n''',
'''\t\t\tif (!MatrixFinite(correctedWorldView))\n\t\t\t\treturn EyeBuildResult::FatalError;\n''', 'corrected WorldView failure')
s = replace_once(s,
'''\t\t\t\tif (!MatrixFinite(eyeWvp))\n\t\t\t\t\treturn false;\n''',
'''\t\t\t\tif (!MatrixFinite(eyeWvp))\n\t\t\t\t\treturn EyeBuildResult::FatalError;\n''', 'eye WVP failure')
s = replace_once(s,
'''\t\t\tstate.worldStereo = true;\n\t\t\tstate.poseSequence = stereo.poseSequence;\n\t\t\treturn true;\n\t\t}\n''',
'''\t\t\tstate.worldStereo = true;\n\t\t\tstate.poseSequence = stereo.poseSequence;\n\t\t\treturn EyeBuildResult::WorldStereo;\n\t\t}\n\n\t\tbool CurrentDrawMatchesVerifiedWorld(IDirect3DDevice9* device)\n\t\t{\n\t\t\tfloat verified[16]{};\n\t\t\tstd::uint32_t generation = 0, poseSequence = 0;\n\t\t\tstd::uintptr_t verifiedShader = 0, currentShader = 0;\n\t\t\tstd::uint64_t verifiedSerial = 0, currentSerial = 0;\n\t\t\tif (!OutRunVRRenderer::GetLastVerifiedWvp(verified, generation, poseSequence,\n\t\t\t\tverifiedShader, verifiedSerial) || generation == 0 || poseSequence == 0)\n\t\t\t\treturn false;\n\t\t\tif (!GetCurrentShaderEpoch(currentShader, currentSerial) ||\n\t\t\t\tcurrentShader != verifiedShader || currentSerial != verifiedSerial)\n\t\t\t\treturn false;\n\t\t\tfloat current[16]{};\n\t\t\treturn SUCCEEDED(device->GetVertexShaderConstantF(OutRunWvpRegister, current,\n\t\t\t\tOutRunWvpRegisterCount)) && FloatArrayNear(current, verified, 16, VerifiedWvpEpsilon);\n\t\t}\n''', 'BuildEyeConstants completion + offscreen marker')

# Depth/stencil helpers.
s = replace_once(s,
'''\t\tbool LeftDrawMayWriteDepth(IDirect3DDevice9* device)\n''',
'''\t\tbool SurfaceHasStencil(IDirect3DSurface9* surface)\n\t\t{\n\t\t\tif (!surface) return false;\n\t\t\tD3DSURFACE_DESC desc{};\n\t\t\treturn SUCCEEDED(surface->GetDesc(&desc)) && FormatHasStencil(desc.Format);\n\t\t}\n\n\t\tbool LeftDrawMayWriteDepth(IDirect3DDevice9* device)\n''', 'SurfaceHasStencil helper')

s = replace_once(s,
'''\t\tvoid InvalidateRightDepthIfLeftMayWrite(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (RightDepthSynchronized && LeftDrawMayWriteDepth(device))\n\t\t\t\tRightDepthSynchronized = false;\n\t\t}\n''',
'''\t\tbool LeftDrawMayWriteStencil(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (!device || !SurfaceHasStencil(TrackedDepthStencil)) return false;\n\t\t\tDWORD enabled = FALSE, writeMask = 0;\n\t\t\tif (FAILED(device->GetRenderState(D3DRS_STENCILENABLE, &enabled)) ||\n\t\t\t\tFAILED(device->GetRenderState(D3DRS_STENCILWRITEMASK, &writeMask))) return true;\n\t\t\tif (!enabled || writeMask == 0) return false;\n\t\t\tDWORD fail = D3DSTENCILOP_KEEP, zfail = D3DSTENCILOP_KEEP, pass = D3DSTENCILOP_KEEP;\n\t\t\tif (FAILED(device->GetRenderState(D3DRS_STENCILFAIL, &fail)) ||\n\t\t\t\tFAILED(device->GetRenderState(D3DRS_STENCILZFAIL, &zfail)) ||\n\t\t\t\tFAILED(device->GetRenderState(D3DRS_STENCILPASS, &pass))) return true;\n\t\t\tif (fail != D3DSTENCILOP_KEEP || zfail != D3DSTENCILOP_KEEP || pass != D3DSTENCILOP_KEEP) return true;\n\t\t\tDWORD twoSided = FALSE;\n\t\t\tif (FAILED(device->GetRenderState(D3DRS_TWOSIDEDSTENCILMODE, &twoSided))) return true;\n\t\t\tif (!twoSided) return false;\n\t\t\tDWORD cFail = D3DSTENCILOP_KEEP, cZFail = D3DSTENCILOP_KEEP, cPass = D3DSTENCILOP_KEEP;\n\t\t\tif (FAILED(device->GetRenderState(D3DRS_CCW_STENCILFAIL, &cFail)) ||\n\t\t\t\tFAILED(device->GetRenderState(D3DRS_CCW_STENCILZFAIL, &cZFail)) ||\n\t\t\t\tFAILED(device->GetRenderState(D3DRS_CCW_STENCILPASS, &cPass))) return true;\n\t\t\treturn cFail != D3DSTENCILOP_KEEP || cZFail != D3DSTENCILOP_KEEP || cPass != D3DSTENCILOP_KEEP;\n\t\t}\n\n\t\tvoid InvalidateRightDepthStencilIfLeftMayWrite(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (RightDepthSynchronized && LeftDrawMayWriteDepth(device)) RightDepthSynchronized = false;\n\t\t\tif (RightStencilSynchronized && LeftDrawMayWriteStencil(device)) RightStencilSynchronized = false;\n\t\t}\n''', 'stencil write tracking')
s = s.replace('InvalidateRightDepthIfLeftMayWrite(device)', 'InvalidateRightDepthStencilIfLeftMayWrite(device)')

s = replace_once(s,
'''\t\t\tReleaseCom(TrackedDepthStencil);\n\t\t\tBackBufferDesc = {};\n''',
'''\t\t\tReleaseCom(TrackedDepthStencil);\n\t\t\tRightDepthSynchronized = true;\n\t\t\tRightStencilSynchronized = true;\n\t\t\tBackBufferDesc = {};\n''', 'resource release sync reset')

s = replace_once(s,
'''\t\t\tReleaseCom(RightEyeDepth);\n\t\t\tRightDepthSynchronized = TrackedDepthStencil == nullptr;\n\t\t\tif (!TrackedDepthStencil)\n\t\t\t\treturn true;\n\n\t\t\tD3DSURFACE_DESC depthDesc{};\n\t\t\tif (FAILED(TrackedDepthStencil->GetDesc(&depthDesc)))\n\t\t\t\treturn false;\n''',
'''\t\t\tReleaseCom(RightEyeDepth);\n\t\t\tRightDepthSynchronized = TrackedDepthStencil == nullptr;\n\t\t\tRightStencilSynchronized = true;\n\t\t\tif (!TrackedDepthStencil)\n\t\t\t\treturn true;\n\n\t\t\tD3DSURFACE_DESC depthDesc{};\n\t\t\tif (FAILED(TrackedDepthStencil->GetDesc(&depthDesc)))\n\t\t\t\treturn false;\n\t\t\tRightStencilSynchronized = !FormatHasStencil(depthDesc.Format);\n''', 'right depth creation sync')

s = replace_once(s,
'''\t\t\tif(TrackedDepthStencil&&!RightDepthSynchronized){PoisonFrame(OutRunVR::StereoFailureDepthUnsynchronized);return false;}\n\t\t\tOutRunVRRenderer::LatchedStereoFrame stereo{};if(!OutRunVRRenderer::GetLatchedStereoFrame(stereo)){PoisonFrame(OutRunVR::StereoFailureMissingLatchedPose);return false;}\n\t\t\tdraw.stereoFrame=stereo;BuildEyeConstants(device,stereo,draw);return true;\n''',
'''\t\t\tif(TrackedDepthStencil&&!RightDepthSynchronized){PoisonFrame(OutRunVR::StereoFailureDepthUnsynchronized);return false;}\n\t\t\tif(TrackedDepthStencil&&!RightStencilSynchronized){PoisonFrame(OutRunVR::StereoFailureStencilUnsynchronized);return false;}\n\t\t\tOutRunVRRenderer::LatchedStereoFrame stereo{};if(!OutRunVRRenderer::GetLatchedStereoFrame(stereo)){PoisonFrame(OutRunVR::StereoFailureMissingLatchedPose);return false;}\n\t\t\tdraw.stereoFrame=stereo;\n\t\t\tconst EyeBuildResult classification=BuildEyeConstants(device,stereo,draw);\n\t\t\tif(classification==EyeBuildResult::FatalError){++WorldClassificationFailures;PoisonFrame(OutRunVR::StereoFailureWorldClassificationFailed);if(!FirstClassificationFailureLogged){FirstClassificationFailureLogged=true;spdlog::warn("VR stereo: verified world draw could not be classified/transformed safely; frame forced to mono fallback");}return false;}\n\t\t\treturn true;\n''', 'PrepareDuplicatedDraw tri-state')

s = replace_once(s,
'''\t\t\tif (StereoWanted() && !TargetIsBackBuffer())\n\t\t\t{\n\t\t\t\tInvalidateRightDepthStencilIfLeftMayWrite(device);\n\t\t\t\treturn drawCall();\n\t\t\t}\n''',
'''\t\t\tif (StereoWanted() && !TargetIsBackBuffer())\n\t\t\t{\n\t\t\t\tif (CurrentDrawMatchesVerifiedWorld(device))\n\t\t\t\t{\n\t\t\t\t\t++OffscreenVerifiedWorldDraws;\n\t\t\t\t\tif (!FirstOffscreenWorldLogged)\n\t\t\t\t\t{\n\t\t\t\t\t\tFirstOffscreenWorldLogged = true;\n\t\t\t\t\t\tspdlog::warn("VR stereo: verified world geometry rendered to an offscreen RT; pass remains single-eye and is telemetry-only until its role is identified");\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\tInvalidateRightDepthStencilIfLeftMayWrite(device);\n\t\t\t\treturn drawCall();\n\t\t\t}\n''', 'offscreen world telemetry')

s = replace_once(s,
'''\t\t\t\telse if(FrameStereoPoseSequence!=draw.poseSequence){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);spdlog::warn("VR stereo: multiple host pose sequences reached one Present; frame forced to mono fallback");}\n''',
'''\t\t\t\telse if(FrameStereoPoseSequence!=draw.poseSequence){FrameRightDrawFailed=true;PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);if(!FramePoseMismatchLogged){FramePoseMismatchLogged=true;++PoseSequenceMismatchFrames;spdlog::warn("VR stereo: multiple host pose sequences reached one Present; frame forced to mono fallback");}}\n''', 'pose mismatch telemetry')

# Clear: offscreen and left-only Z/stencil divergence.
s = replace_once(s,
'''\t\t\t\tif (SUCCEEDED(hr) && (flags & D3DCLEAR_ZBUFFER) != 0 && TrackedDepthStencil)\n\t\t\t\t\tRightDepthSynchronized = false;\n''',
'''\t\t\t\tif (SUCCEEDED(hr) && TrackedDepthStencil)\n\t\t\t\t{\n\t\t\t\t\tif ((flags & D3DCLEAR_ZBUFFER) != 0) RightDepthSynchronized = false;\n\t\t\t\t\tif ((flags & D3DCLEAR_STENCIL) != 0 && SurfaceHasStencil(TrackedDepthStencil)) RightStencilSynchronized = false;\n\t\t\t\t}\n''', 'offscreen clear sync')
s = replace_once(s,
'''\t\t\tif(!duplicate||FAILED(leftHr)){if(candidate&&FAILED(leftHr))PoisonFrame(OutRunVR::StereoFailureClearFailed);if(SUCCEEDED(leftHr)&&candidate&&(flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;return leftHr;}\n''',
'''\t\t\tif(!duplicate||FAILED(leftHr)){if(candidate&&FAILED(leftHr))PoisonFrame(OutRunVR::StereoFailureClearFailed);if(SUCCEEDED(leftHr)&&candidate){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;if((flags&D3DCLEAR_STENCIL)!=0&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=false;}return leftHr;}\n''', 'left-only clear sync')
s = replace_once(s,
'''\t\t\tD3DVIEWPORT9 savedViewport{};if(FAILED(device->GetViewport(&savedViewport))){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return leftHr;}\n''',
'''\t\t\tD3DVIEWPORT9 savedViewport{};if(FAILED(device->GetViewport(&savedViewport))){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;if((flags&D3DCLEAR_STENCIL)!=0&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=false;PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return leftHr;}\n''', 'viewport clear sync')
s = replace_once(s,
'''\t\t\tif(FAILED(rightHr)){FrameRightDrawFailed=true;if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;PoisonFrame(OutRunVR::StereoFailureClearFailed);}else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0 &&\n\t\t\t\tViewportCoversStereoBackbuffer(device)) RightDepthSynchronized = true;if(!restoreOk){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;NoteRestoreFailure("right-eye clear");}return leftHr;\n''',
'''\t\t\tif(FAILED(rightHr)){FrameRightDrawFailed=true;if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;if((flags&D3DCLEAR_STENCIL)!=0&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=false;PoisonFrame(OutRunVR::StereoFailureClearFailed);}else if(count==0&&ViewportCoversStereoBackbuffer(device)){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=true;if((flags&D3DCLEAR_STENCIL)!=0&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=true;}if(!restoreOk){if((flags&D3DCLEAR_ZBUFFER)!=0)RightDepthSynchronized=false;if((flags&D3DCLEAR_STENCIL)!=0&&SurfaceHasStencil(TrackedDepthStencil))RightStencilSynchronized=false;NoteRestoreFailure("right-eye clear");}return leftHr;\n''', 'duplicated clear sync')

# Summary: include the diagnostics that make the one-shot runtime test useful.
s = replace_once(s,
'''\t\t\tspdlog::info("VR stereo: draws={} world={} ui/effect={} composeOk={} composeFail={} rightFail={} mrtReject={} restoreFail={} poseSeq={}",\n\t\t\t\tDuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws,\n\t\t\t\tStereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed ? 1 : 0,\n\t\t\t\tMrtRejectedDraws, RestoreFailures, FrameStereoPoseSequence);\n''',
'''\t\t\tspdlog::info("VR stereo: draws={} world={} ui/effect={} offscreenWorld={} classifyFail={} composeOk={} composeFail={} rightFail={} mrtReject={} restoreFail={} poseMismatchFrames={} multiBeginPresent={} maxBeginPerPresent={} poseSeq={} failures[pose={},res={},mrt={},viewport={},classify={},depth={},stencil={},clear={}]",\n\t\t\t\tDuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws, OffscreenVerifiedWorldDraws,\n\t\t\t\tWorldClassificationFailures, StereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed ? 1 : 0,\n\t\t\t\tMrtRejectedDraws, RestoreFailures, PoseSequenceMismatchFrames, MultiBeginScenePresents,\n\t\t\t\tMaxBeginScenesPerPresent, FrameStereoPoseSequence,\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureMissingLatchedPose], FailureCounts[OutRunVR::StereoFailureResourceUnavailable],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureMrtActive], FailureCounts[OutRunVR::StereoFailureViewportUnavailable],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureWorldClassificationFailed], FailureCounts[OutRunVR::StereoFailureDepthUnsynchronized],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureStencilUnsynchronized], FailureCounts[OutRunVR::StereoFailureClearFailed]);\n''', 'summary telemetry')

# Present-frame BeginScene accounting and reset of per-frame mismatch latch.
s = replace_once(s,
'''\t\t\tif(!IsGameDevice(device))return PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);const bool stereoRequested=StereoWanted();bool composedStereo=false;std::uint32_t pendingPoseSequence=0;\n''',
'''\t\t\tif(!IsGameDevice(device))return PresentHook.stdcall<HRESULT>(device,sourceRect,destRect,destWindowOverride,dirtyRegion);const std::uint64_t beginNow=OutRunVRRenderer::GetBeginSceneCallCount();const std::uint64_t beginDelta=beginNow>=LastBeginSceneCountAtPresent?beginNow-LastBeginSceneCountAtPresent:0;LastBeginSceneCountAtPresent=beginNow;if(beginDelta>1)++MultiBeginScenePresents;MaxBeginScenesPerPresent=std::max(MaxBeginScenesPerPresent,beginDelta);const bool stereoRequested=StereoWanted();bool composedStereo=false;std::uint32_t pendingPoseSequence=0;\n''', 'Present BeginScene diagnostics')
s = replace_once(s,
'''\t\t\tFrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;\n''',
'''\t\t\tFrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FramePoseMismatchLogged=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;\n''', 'Present state reset')

s = replace_once(s,
'''\t\t\tLastHostRenderEligible = false;\n\t\t\tFrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoMetadata={};PublishStereoState''',
'''\t\t\tLastHostRenderEligible = false;\n\t\t\tRightStencilSynchronized = true;\n\t\t\tFramePoseMismatchLogged = false;\n\t\t\tLastBeginSceneCountAtPresent = OutRunVRRenderer::GetBeginSceneCallCount();\n\t\t\tFrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoMetadata={};PublishStereoState''', 'Reset diagnostics')

s = replace_once(s,
'''\t\t\tInitializeAuxRenderTargetState(device);\n\t\t\tEnsureSharedState();\n''',
'''\t\t\tInitializeAuxRenderTargetState(device);\n\t\t\tLastBeginSceneCountAtPresent = OutRunVRRenderer::GetBeginSceneCallCount();\n\t\t\tEnsureSharedState();\n''', 'hook install diagnostics')

p.write_text(s, encoding='utf-8')

print('VR 20-pass review patch applied successfully')
