from pathlib import Path


def r1(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return text.replace(old, new, 1)

# Renderer marker lifetime: invalidate any overlapping game c64..c67 write,
# but never invalidate on stereo module's internal per-register writes.
p = Path('src/vr_renderer_probe.cpp')
s = p.read_text(encoding='utf-8')
s = r1(s,
'''\t\tbool UploadContainsOutRunWvp(UINT startRegister, UINT vector4fCount)\n\t\t{\n\t\t\tif (vector4fCount == 0 || vector4fCount > 256 || startRegister > OutRunWvpRegister)\n\t\t\t\treturn false;\n\t\t\tconst UINT offset = OutRunWvpRegister - startRegister;\n\t\t\treturn vector4fCount >= offset + OutRunWvpRegisterCount;\n\t\t}\n''',
'''\t\tbool UploadContainsOutRunWvp(UINT startRegister, UINT vector4fCount)\n\t\t{\n\t\t\tif (vector4fCount == 0 || vector4fCount > 256 || startRegister > OutRunWvpRegister)\n\t\t\t\treturn false;\n\t\t\tconst UINT offset = OutRunWvpRegister - startRegister;\n\t\t\treturn vector4fCount >= offset + OutRunWvpRegisterCount;\n\t\t}\n\n\t\tbool UploadTouchesOutRunWvp(UINT startRegister, UINT vector4fCount)\n\t\t{\n\t\t\tif (vector4fCount == 0 || vector4fCount > 256) return false;\n\t\t\tconst std::uint64_t first = startRegister;\n\t\t\tconst std::uint64_t lastExclusive = first + vector4fCount;\n\t\t\treturn first < OutRunWvpRegister + OutRunWvpRegisterCount &&\n\t\t\t\tlastExclusive > OutRunWvpRegister;\n\t\t}\n''', 'touch helper')

s = r1(s,
'''\t\t\tif (!IsGameDevice(device) || !constantData ||\n\t\t\t\t!UploadContainsOutRunWvp(startRegister, vector4fCount))\n\t\t\t{\n\t\t\t\treturn SetVertexShaderConstantFHook.stdcall<HRESULT>(\n\t\t\t\t\tdevice, startRegister, constantData, vector4fCount);\n\t\t\t}\n\n\t\t\t// Any game c64..c67 upload supersedes the previous world marker. Only an\n\t\t\t// independently verified and successfully uploaded OutRun WVP below can\n\t\t\t// arm stereo geometry again.\n\t\t\tInvalidateVerifiedWvp();\n\n\t\t\tfloat patchedData[256 * 4];\n''',
'''\t\t\tif (!IsGameDevice(device) || !constantData || OutRunVRStereo::IsInternalStereoPassActive())\n\t\t\t{\n\t\t\t\treturn SetVertexShaderConstantFHook.stdcall<HRESULT>(\n\t\t\t\t\tdevice, startRegister, constantData, vector4fCount);\n\t\t\t}\n\t\t\tif (!UploadTouchesOutRunWvp(startRegister, vector4fCount))\n\t\t\t{\n\t\t\t\treturn SetVertexShaderConstantFHook.stdcall<HRESULT>(\n\t\t\t\t\tdevice, startRegister, constantData, vector4fCount);\n\t\t\t}\n\n\t\t\t// Any GAME write touching c64..c67 supersedes the previous marker, even\n\t\t\t// if it updates only one register. Stereo's own per-register writes are\n\t\t\t// protected by InternalStereoPass above and must not disarm the marker.\n\t\t\tInvalidateVerifiedWvp();\n\t\t\tif (!UploadContainsOutRunWvp(startRegister, vector4fCount))\n\t\t\t{\n\t\t\t\treturn SetVertexShaderConstantFHook.stdcall<HRESULT>(\n\t\t\t\t\tdevice, startRegister, constantData, vector4fCount);\n\t\t\t}\n\n\t\t\tfloat patchedData[256 * 4];\n''', 'partial c64 invalidation')
p.write_text(s, encoding='utf-8')

p = Path('src/vr_stereo.cpp')
s = p.read_text(encoding='utf-8')
s = r1(s, '\t\tbool InternalStereoPass = false;\n', '\t\tthread_local bool InternalStereoPass = false;\n', 'thread-local internal pass')
s = s.replace('bool LastHostRenderEligible = false;', 'bool LastStereoWanted = false;')
s = s.replace('LastHostRenderEligible = false;', 'LastStereoWanted = false;')

old = '''\t\tbool StereoWanted()\n\t\t{\n\t\t\tconst bool hostEligible = HostRenderEligible();\n\t\t\tif (hostEligible && !LastHostRenderEligible && TrackedDepthStencil)\n\t\t\t{\n\t\t\t\t// The left/game depth/stencil may have advanced while OpenXR asked us\n\t\t\t\t// not to render. Require duplicated full clears before reusing them.\n\t\t\t\tRightDepthSynchronized = false;\n\t\t\t\tD3DSURFACE_DESC d{};\n\t\t\t\tif (SUCCEEDED(TrackedDepthStencil->GetDesc(&d)) && FormatHasStencil(d.Format))\n\t\t\t\t\tRightStencilSynchronized = false;\n\t\t\t}\n\t\t\tLastHostRenderEligible = hostEligible;\n\t\t\tif (!Settings::VRStereo || !GameplayActive() || !hostEligible)\n\t\t\t\treturn false;\n\t\t\treturn Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent;\n\t\t}\n'''
new = '''\t\tbool StereoWanted()\n\t\t{\n\t\t\tconst bool hostEligible = HostRenderEligible();\n\t\t\tconst bool wanted = Settings::VRStereo && GameplayActive() && hostEligible &&\n\t\t\t\t(Settings::VREnabled || Settings::VRAutoEnableWhenHostPresent);\n\t\t\tif (wanted && !LastStereoWanted && TrackedDepthStencil)\n\t\t\t{\n\t\t\t\t// Any interval with stereo transport disabled can let the left/game\n\t\t\t\t// depth/stencil advance alone. Re-establish synchronization lazily.\n\t\t\t\tRightDepthSynchronized = false;\n\t\t\t\tD3DSURFACE_DESC d{};\n\t\t\t\tif (SUCCEEDED(TrackedDepthStencil->GetDesc(&d)) && FormatHasStencil(d.Format))\n\t\t\t\t\tRightStencilSynchronized = false;\n\t\t\t}\n\t\t\tLastStereoWanted = wanted;\n\t\t\treturn wanted;\n\t\t}\n'''
s = r1(s, old, new, 'StereoWanted transition')

# Fixed-function/no-current-shader is a normal non-world case, not a fatal classifier error.
s = r1(s,
'''\t\t\tif (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))\n\t\t\t\treturn EyeBuildResult::FatalError;\n''',
'''\t\t\tif (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))\n\t\t\t\treturn EyeBuildResult::NonWorld;\n''', 'fixed-function classifier')

# Lazy depth/stencil gating: an unsynchronized buffer only matters when its test is active.
s = r1(s,
'''\t\tbool LeftDrawMayWriteDepth(IDirect3DDevice9* device)\n''',
'''\t\tbool DepthTestActive(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (!device || !TrackedDepthStencil) return false;\n\t\t\tDWORD enabled = D3DZB_TRUE;\n\t\t\tif (FAILED(device->GetRenderState(D3DRS_ZENABLE, &enabled))) return true;\n\t\t\treturn enabled != D3DZB_FALSE;\n\t\t}\n\n\t\tbool StencilTestActive(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (!device || !SurfaceHasStencil(TrackedDepthStencil)) return false;\n\t\t\tDWORD enabled = FALSE;\n\t\t\tif (FAILED(device->GetRenderState(D3DRS_STENCILENABLE, &enabled))) return true;\n\t\t\treturn enabled != FALSE;\n\t\t}\n\n\t\tbool LeftDrawMayWriteDepth(IDirect3DDevice9* device)\n''', 'active test helpers')

s = r1(s,
'''\t\t\tif(TrackedDepthStencil&&!RightDepthSynchronized){PoisonFrame(OutRunVR::StereoFailureDepthUnsynchronized);return false;}\n\t\t\tif(TrackedDepthStencil&&!RightStencilSynchronized){PoisonFrame(OutRunVR::StereoFailureStencilUnsynchronized);return false;}\n''',
'''\t\t\tif(TrackedDepthStencil&&!RightDepthSynchronized&&DepthTestActive(device)){PoisonFrame(OutRunVR::StereoFailureDepthUnsynchronized);return false;}\n\t\t\tif(TrackedDepthStencil&&!RightStencilSynchronized&&StencilTestActive(device)){PoisonFrame(OutRunVR::StereoFailureStencilUnsynchronized);return false;}\n''', 'lazy depth/stencil gate')

# Stereo's own left-eye c64 writes must not invalidate renderer-probe's marker.
s = r1(s,
'''\t\t\tif(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.eyeConstants[0])){const bool rolledBack=SetWvpOneRegisterAtATime(device,draw.originalConstants);PoisonFrame(OutRunVR::StereoFailureLeftWvpUploadFailed);if(!rolledBack)NoteRestoreFailure("left-eye c64 rollback");return drawCall();}\n''',
'''\t\t\tif(draw.worldStereo)\n\t\t\t{\n\t\t\t\tbool leftWvpOk=false;\n\t\t\t\t{ InternalPassScope guard; leftWvpOk=SetWvpOneRegisterAtATime(device,draw.eyeConstants[0]); }\n\t\t\t\tif(!leftWvpOk){bool rolledBack=false;{ InternalPassScope guard; rolledBack=SetWvpOneRegisterAtATime(device,draw.originalConstants); }InvalidateRightDepthStencilIfLeftMayWrite(device);PoisonFrame(OutRunVR::StereoFailureLeftWvpUploadFailed);if(!rolledBack)NoteRestoreFailure("left-eye c64 rollback");return drawCall();}\n\t\t\t}\n''', 'left WVP guarded upload')

s = r1(s,
'''\t\t\tif(FAILED(leftHr)){InvalidateRightDepthStencilIfLeftMayWrite(device);PoisonFrame(OutRunVR::StereoFailureLeftDrawFailed);if(draw.worldStereo&&!SetWvpOneRegisterAtATime(device,draw.originalConstants))NoteRestoreFailure("left draw c64");return leftHr;}\n''',
'''\t\t\tif(FAILED(leftHr)){InvalidateRightDepthStencilIfLeftMayWrite(device);PoisonFrame(OutRunVR::StereoFailureLeftDrawFailed);if(draw.worldStereo){bool restored=false;{ InternalPassScope guard; restored=SetWvpOneRegisterAtATime(device,draw.originalConstants); }if(!restored)NoteRestoreFailure("left draw c64");}return leftHr;}\n''', 'left failure guarded restore')

s = r1(s,
'''\t\t\tD3DVIEWPORT9 savedViewport{};\n\t\t\tif(FAILED(device->GetViewport(&savedViewport))){PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return drawCall();}\n''',
'''\t\t\tD3DVIEWPORT9 savedViewport{};\n\t\t\tif(FAILED(device->GetViewport(&savedViewport))){InvalidateRightDepthStencilIfLeftMayWrite(device);PoisonFrame(OutRunVR::StereoFailureViewportUnavailable);return drawCall();}\n''', 'viewport abort sync')

# Only count BeginScene multiplicity for gameplay Presents.
s = r1(s,
'''const std::uint64_t beginNow=OutRunVRRenderer::GetBeginSceneCallCount();const std::uint64_t beginDelta=beginNow>=LastBeginSceneCountAtPresent?beginNow-LastBeginSceneCountAtPresent:0;LastBeginSceneCountAtPresent=beginNow;if(beginDelta>1)++MultiBeginScenePresents;MaxBeginScenesPerPresent=std::max(MaxBeginScenesPerPresent,beginDelta);const bool stereoRequested=StereoWanted();''',
'''const std::uint64_t beginNow=OutRunVRRenderer::GetBeginSceneCallCount();const std::uint64_t beginDelta=beginNow>=LastBeginSceneCountAtPresent?beginNow-LastBeginSceneCountAtPresent:0;LastBeginSceneCountAtPresent=beginNow;if(GameplayActive()){if(beginDelta>1)++MultiBeginScenePresents;MaxBeginScenesPerPresent=std::max(MaxBeginScenesPerPresent,beginDelta);}const bool stereoRequested=StereoWanted();''', 'gameplay BeginScene stats')

# Count Present failure in the same first-reason histogram.
s = r1(s,
'''else{if(FAILED(hr)&&FrameFailureReason==OutRunVR::StereoFailureNone)FrameFailureReason=OutRunVR::StereoFailurePresentFailed;const std::uint32_t fallback=''',
'''else{if(FAILED(hr)&&FrameFailureReason==OutRunVR::StereoFailureNone)PoisonFrame(OutRunVR::StereoFailurePresentFailed);const std::uint32_t fallback=''', 'Present failure histogram')

# Expand the one-shot test summary with all high-value failure categories.
s = r1(s,
'''failures[pose={},res={},mrt={},viewport={},classify={},depth={},stencil={},clear={}]",\n''',
'''failures[pose={},res={},mrt={},viewport={},classify={},depth={},stencil={},clear={},rightState={},rightWvp={},rightDraw={},restore={},compose={},present={},depthState={},poseMismatch={}]",\n''', 'summary format')
s = r1(s,
'''\t\t\t\tFailureCounts[OutRunVR::StereoFailureWorldClassificationFailed], FailureCounts[OutRunVR::StereoFailureDepthUnsynchronized],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureStencilUnsynchronized], FailureCounts[OutRunVR::StereoFailureClearFailed]);\n''',
'''\t\t\t\tFailureCounts[OutRunVR::StereoFailureWorldClassificationFailed], FailureCounts[OutRunVR::StereoFailureDepthUnsynchronized],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureStencilUnsynchronized], FailureCounts[OutRunVR::StereoFailureClearFailed],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureRightStateFailed], FailureCounts[OutRunVR::StereoFailureRightWvpUploadFailed],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureRightDrawFailed], FailureCounts[OutRunVR::StereoFailureRestoreFailed],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureComposeFailed], FailureCounts[OutRunVR::StereoFailurePresentFailed],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureDepthStateChanged], FailureCounts[OutRunVR::StereoFailurePoseSequenceMismatch]);\n''', 'summary arguments')

p.write_text(s, encoding='utf-8')
print('VR review20 follow-up patch applied')
