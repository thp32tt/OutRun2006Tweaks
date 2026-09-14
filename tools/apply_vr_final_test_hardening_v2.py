from pathlib import Path
import re


def sub_once(text, pattern, replacement, label, flags=0):
    out, n = re.subn(pattern, replacement, text, count=1, flags=flags)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 match, got {n}")
    return out

root = Path('.')

# Shared protocol: ABI layout unchanged; only enum/interface declarations grow.
p = root / 'src/vr_shared.hpp'
s = p.read_text(encoding='utf-8')
s = sub_once(s,
    r'(\s*StereoFailureWorldClassificationFailed = 17,\n\s*StereoFailureStencilUnsynchronized = 18,\n)',
    r'\1        StereoFailureOffscreenWorld = 19,\n        StereoFailureOcclusionQueryActive = 20,\n',
    'failure reasons')
s = sub_once(s,
    r'(\s*std::uint64_t GetBeginSceneCallCount\(\);\n)(\})',
    r'\1    void NotifyGamePresent();\n    void NotifyGameReset();\n\2',
    'renderer boundary declarations')
p.write_text(s, encoding='utf-8')

# Renderer: one immutable HMD sample for all BeginScene calls that feed one Present.
p = root / 'src/vr_renderer_probe.cpp'
s = p.read_text(encoding='utf-8')
s = sub_once(s,
    r'(\s*std::uint32_t LatchedPoseSequence = 0;\n)',
    r'\1\t\tbool PresentPoseLocked = false;\n',
    'present pose lock state')
s = sub_once(s,
    r'(\s*std::uint64_t UnsafeAddressRejects = 0;\n)',
    r'\1\t\tstd::uint64_t ReusedPoseSceneCalls = 0;\n',
    'pose reuse counter')
s = sub_once(s,
    r'(\t\tvoid LatchFramePose\(\)\n\t\t\{\n)\t\t\t\+\+BeginSceneCalls;\n',
    r'\1', 'move begin counter to hook')
insert_before_upload = '''\t\tvoid ReusePresentPoseForScene()\n\t\t{\n\t\t\t// Additional BeginScene calls before the same Present reuse the exact\n\t\t\t// pose chosen by the first scene. Only scene-local WVP classification\n\t\t\t// state is reset. This prevents mixed-pose geometry in one desktop frame.\n\t\t\t++ReusedPoseSceneCalls;\n\t\t\tInvalidateVerifiedWvp();\n\t\t\tRestoreCullingCamera();\n\t\t\tFrameTelemetryFlags = ClientHookAlive;\n\t\t\tif (LatchedPoseSequence != 0) FrameTelemetryFlags |= ClientHostPoseValid;\n\t\t\tif (Settings::VRAutoEnableWhenHostPresent) FrameTelemetryFlags |= ClientAutoEnabled;\n\t\t\tif (LatchedHeadInverseValid) ApplyCullingCameraSync();\n\t\t}\n\n'''
s = sub_once(s,
    r'(\t\tbool UploadContainsOutRunWvp\(UINT startRegister, UINT vector4fCount\)\n)',
    lambda m: insert_before_upload + m.group(1),
    'present pose reuse helper')
s = sub_once(s,
    r'\t\tHRESULT __stdcall BeginSceneDest\(IDirect3DDevice9\* device\)\n\t\t\{.*?\t\t\}\n\n\t\tHRESULT __stdcall EndSceneDest',
    '''\t\tHRESULT __stdcall BeginSceneDest(IDirect3DDevice9* device)\n\t\t{\n\t\t\tconst HRESULT result = BeginSceneHook.stdcall<HRESULT>(device);\n\t\t\tif (!IsGameDevice(device) || OutRunVRStereo::IsInternalStereoPassActive())\n\t\t\t\treturn result;\n\t\t\tif (SUCCEEDED(result))\n\t\t\t{\n\t\t\t\t++BeginSceneCalls;\n\t\t\t\tif (!PresentPoseLocked)\n\t\t\t\t{\n\t\t\t\t\tLatchFramePose();\n\t\t\t\t\tPresentPoseLocked = GameRendererIsActive();\n\t\t\t\t}\n\t\t\t\telse\n\t\t\t\t\tReusePresentPoseForScene();\n\t\t\t}\n\t\t\telse\n\t\t\t{\n\t\t\t\tPresentPoseLocked = false;\n\t\t\t\tResetFrameState();\n\t\t\t}\n\t\t\treturn result;\n\t\t}\n\n\t\tHRESULT __stdcall EndSceneDest''',
    'BeginScene present latch', flags=re.S)
s = sub_once(s,
    r'"VR renderer: beginScene=\{\} c64Candidate=\{\} verified=\{\} prepared=\{\} uploadOk=\{\} uploadFail=\{\} rejected=\{\} unsafe=\{\} latchedSeq=\{\} wvpGen=\{\}",\n\s*BeginSceneCalls, WvpCandidateCalls, WvpVerifiedCalls, WvpPreparedCalls,\n\s*WvpUploadSucceededCalls, WvpUploadFailedCalls, WvpRejectedCalls,\n\s*UnsafeAddressRejects, LatchedPoseSequence, LastVerifiedWvpGeneration\);',
    '"VR renderer: beginScene={} poseReuse={} c64Candidate={} verified={} prepared={} uploadOk={} uploadFail={} rejected={} unsafe={} latchedSeq={} wvpGen={} presentPoseLocked={}",\n\t\t\t\tBeginSceneCalls, ReusedPoseSceneCalls, WvpCandidateCalls, WvpVerifiedCalls, WvpPreparedCalls,\n\t\t\t\tWvpUploadSucceededCalls, WvpUploadFailedCalls, WvpRejectedCalls,\n\t\t\t\tUnsafeAddressRejects, LatchedPoseSequence, LastVerifiedWvpGeneration, PresentPoseLocked ? 1 : 0);',
    'renderer telemetry summary')
s = sub_once(s,
    r'(\tstd::uint64_t GetBeginSceneCallCount\(\)\n\t\{\n\t\treturn BeginSceneCalls;\n\t\}\n)',
    r'''\1
\tvoid NotifyGamePresent()
\t{
\t\tPresentPoseLocked = false;
\t\tInvalidateVerifiedWvp();
\t\tRestoreCullingCamera();
\t}

\tvoid NotifyGameReset()
\t{
\t\tPresentPoseLocked = false;
\t\tRestoreCullingCamera();
\t\tResetFrameState();
\t}
''',
    'present/reset renderer notifications')
p.write_text(s, encoding='utf-8')

# Stereo: classifier, offscreen correctness, occlusion-query protection and logs.
p = root / 'src/vr_stereo.cpp'
s = p.read_text(encoding='utf-8')
s = sub_once(s,
    r'(\t\tconstexpr std::size_t SetVertexShaderVtableIndex = 92;\n)',
    r'\1\t\tconstexpr std::size_t CreateQueryVtableIndex = 118;\n\t\tconstexpr std::size_t QueryIssueVtableIndex = 6;\n',
    'query vtable indices')
s = sub_once(s,
    r'(\t\tSafetyHookInline SetVertexShaderHook\{\};\n)',
    r'\1\t\tSafetyHookInline CreateQueryHook{};\n\t\tSafetyHookInline QueryIssueHook{};\n',
    'query hook objects')
s = sub_once(s,
    r'(\t\tstd::atomic<std::uint64_t> VertexShaderSerial\{ 0 \};\n)',
    r'\1\t\tstd::atomic<int> ActiveOcclusionQueries{ 0 };\n',
    'active occlusion count')
s = sub_once(s,
    r'(\t\tstd::uint64_t LastBeginSceneCountAtPresent = 0;\n)',
    r'\1\t\tstd::uint64_t FixedFunctionNonWorldDraws = 0;\n\t\tstd::uint64_t OcclusionQueriesCreated = 0;\n\t\tstd::uint64_t OcclusionQueryBegins = 0;\n\t\tstd::uint64_t OcclusionQueryEnds = 0;\n\t\tstd::uint64_t OcclusionStereoRejects = 0;\n',
    'new telemetry counters')
s = sub_once(s,
    r'(\t\tbool FirstClassificationFailureLogged = false;\n)',
    r'\1\t\tbool FirstOcclusionRejectLogged = false;\n',
    'occlusion first log')
# Distinguish a genuine fixed-function draw from unexpected shader-epoch read failure.
s = sub_once(s,
    r'\t\t\tstd::uintptr_t shaderIdentity = 0;\n\t\t\tstd::uint64_t shaderSerial = 0;\n\t\t\tif \(!GetCurrentShaderEpoch\(shaderIdentity, shaderSerial\)\)\n\t\t\t\treturn EyeBuildResult::NonWorld;',
    '''\t\t\tif (CurrentVertexShaderIdentity.load(std::memory_order_acquire) == 0)\n\t\t\t{\n\t\t\t\t++FixedFunctionNonWorldDraws;\n\t\t\t\treturn EyeBuildResult::NonWorld;\n\t\t\t}\n\t\t\tstd::uintptr_t shaderIdentity = 0;\n\t\t\tstd::uint64_t shaderSerial = 0;\n\t\t\tif (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))\n\t\t\t\treturn EyeBuildResult::FatalError;''',
    'fixed-function classifier')
s = sub_once(s,
    r'(\t\t\tif \(AnyAuxRenderTargetActive\(\)\)\{PoisonFrame\(OutRunVR::StereoFailureMrtActive\);\+\+MrtRejectedDraws;if\(!FirstMrtRejectLogged\)\{FirstMrtRejectLogged=true;spdlog::info\("VR stereo: auxiliary MRT active; current Present is marked incomplete"\);\}return false;\}\n)',
    r'\1\t\t\tif (ActiveOcclusionQueries.load(std::memory_order_acquire) > 0){++OcclusionStereoRejects;PoisonFrame(OutRunVR::StereoFailureOcclusionQueryActive);if(!FirstOcclusionRejectLogged){FirstOcclusionRejectLogged=true;spdlog::warn("VR stereo: active D3D9 occlusion query detected; right-eye draw suppressed so the game query remains single-render accurate");}return false;}\n',
    'occlusion draw gate')
s = sub_once(s,
    r'\t\t\t\tif \(CurrentDrawMatchesVerifiedWorld\(device\)\)\n\t\t\t\t\{\n\t\t\t\t\t\+\+OffscreenVerifiedWorldDraws;\n\t\t\t\t\tif \(!FirstOffscreenWorldLogged\)\n\t\t\t\t\t\{\n\t\t\t\t\t\tFirstOffscreenWorldLogged = true;\n\t\t\t\t\t\tspdlog::warn\("VR stereo: verified world geometry rendered to an offscreen RT; pass remains single-eye and is telemetry-only until its role is identified"\);\n\t\t\t\t\t\}\n\t\t\t\t\}',
    '''\t\t\t\tif (CurrentDrawMatchesVerifiedWorld(device))\n\t\t\t\t{\n\t\t\t\t\t++OffscreenVerifiedWorldDraws;\n\t\t\t\t\tPoisonFrame(OutRunVR::StereoFailureOffscreenWorld);\n\t\t\t\t\tif (!FirstOffscreenWorldLogged)\n\t\t\t\t\t{\n\t\t\t\t\t\tFirstOffscreenWorldLogged = true;\n\t\t\t\t\t\tD3DSURFACE_DESC rtDesc{}, depthDesc{};\n\t\t\t\t\t\tconst bool rtOk = TrackedRenderTarget && SUCCEEDED(TrackedRenderTarget->GetDesc(&rtDesc));\n\t\t\t\t\t\tconst bool depthOk = TrackedDepthStencil && SUCCEEDED(TrackedDepthStencil->GetDesc(&depthDesc));\n\t\t\t\t\t\tspdlog::warn("VR stereo: VERIFIED WORLD draw hit offscreen RT; Present forced to fallback. rt={}x{} fmt={} msaa={} depthFmt={} depthMsaa={}",\n\t\t\t\t\t\t\trtOk ? rtDesc.Width : 0u, rtOk ? rtDesc.Height : 0u, rtOk ? static_cast<int>(rtDesc.Format) : -1,\n\t\t\t\t\t\t\trtOk ? static_cast<int>(rtDesc.MultiSampleType) : -1, depthOk ? static_cast<int>(depthDesc.Format) : -1,\n\t\t\t\t\t\t\tdepthOk ? static_cast<int>(depthDesc.MultiSampleType) : -1);\n\t\t\t\t\t}\n\t\t\t\t}''',
    'offscreen verified world fail closed')
query_code = '''\t\tHRESULT __stdcall QueryIssueDest(IDirect3DQuery9* query, DWORD issueFlags)\n\t\t{\n\t\t\tconst HRESULT hr = QueryIssueHook.stdcall<HRESULT>(query, issueFlags);\n\t\t\tif (FAILED(hr) || !query || query->GetType() != D3DQUERYTYPE_OCCLUSION) return hr;\n\t\t\tIDirect3DDevice9* queryDevice = nullptr;\n\t\t\tif (FAILED(query->GetDevice(&queryDevice)) || !queryDevice) return hr;\n\t\t\tconst bool gameQuery = IsGameDevice(queryDevice);\n\t\t\tqueryDevice->Release();\n\t\t\tif (!gameQuery) return hr;\n\t\t\tif ((issueFlags & D3DISSUE_BEGIN) != 0)\n\t\t\t{\n\t\t\t\tActiveOcclusionQueries.fetch_add(1, std::memory_order_acq_rel);\n\t\t\t\t++OcclusionQueryBegins;\n\t\t\t}\n\t\t\tif ((issueFlags & D3DISSUE_END) != 0)\n\t\t\t{\n\t\t\t\tint current = ActiveOcclusionQueries.load(std::memory_order_acquire);\n\t\t\t\twhile (current > 0 && !ActiveOcclusionQueries.compare_exchange_weak(current, current - 1, std::memory_order_acq_rel, std::memory_order_acquire)) {}\n\t\t\t\t++OcclusionQueryEnds;\n\t\t\t}\n\t\t\treturn hr;\n\t\t}\n\n\t\tHRESULT __stdcall CreateQueryDest(IDirect3DDevice9* device, D3DQUERYTYPE type, IDirect3DQuery9** query)\n\t\t{\n\t\t\tconst HRESULT hr = CreateQueryHook.stdcall<HRESULT>(device, type, query);\n\t\t\tif (!IsGameDevice(device) || FAILED(hr) || type != D3DQUERYTYPE_OCCLUSION || !query || !*query) return hr;\n\t\t\t++OcclusionQueriesCreated;\n\t\t\tif (!QueryIssueHook)\n\t\t\t{\n\t\t\t\tvoid** queryVtable = *reinterpret_cast<void***>(*query);\n\t\t\t\tif (queryVtable) QueryIssueHook = safetyhook::create_inline(queryVtable[QueryIssueVtableIndex], QueryIssueDest);\n\t\t\t\tif (QueryIssueHook) spdlog::info("VR stereo: occlusion-query Issue hook armed; active queries fail closed instead of counting the right-eye duplicate");\n\t\t\t\telse spdlog::warn("VR stereo: failed to hook IDirect3DQuery9::Issue; query protection unavailable");\n\t\t\t}\n\t\t\treturn hr;\n\t\t}\n\n'''
s = sub_once(s,
    r'(\t\tHRESULT __stdcall SetVertexShaderDest\(IDirect3DDevice9\* device, IDirect3DVertexShader9\* shader\)\n)',
    lambda m: query_code + m.group(1),
    'query hook implementations')
# Telemetry string and arguments.
s = sub_once(s,
    r'"VR stereo: draws=\{\} world=\{\} ui/effect=\{\} offscreenWorld=\{\} classifyFail=\{\} composeOk=\{\} composeFail=\{\} rightFail=\{\} mrtReject=\{\} restoreFail=\{\} poseMismatchFrames=\{\} multiBeginPresent=\{\} maxBeginPerPresent=\{\} poseSeq=\{\} failures\[pose=\{\},res=\{\},mrt=\{\},viewport=\{\},classify=\{\},depth=\{\},stencil=\{\},clear=\{\},rightState=\{\},rightWvp=\{\},rightDraw=\{\},restore=\{\},compose=\{\},present=\{\},depthState=\{\},poseMismatch=\{\}\]",',
    '"VR stereo: draws={} world={} ui/effect={} fixedFn={} offscreenWorld={} classifyFail={} composeOk={} composeFail={} rightFail={} mrtReject={} restoreFail={} poseMismatchFrames={} multiBeginPresent={} maxBeginPerPresent={} poseSeq={} occ[created={},begin={},end={},active={},reject={}] failures[pose={},res={},mrt={},viewport={},classify={},depth={},stencil={},clear={},rightState={},rightWvp={},rightDraw={},restore={},compose={},present={},depthState={},poseMismatch={},offscreen={},occlusion={}]",',
    'summary format')
s = sub_once(s,
    r'DuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws, OffscreenVerifiedWorldDraws,\n\s*WorldClassificationFailures, StereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed \? 1 : 0,\n\s*MrtRejectedDraws, RestoreFailures, PoseSequenceMismatchFrames, MultiBeginScenePresents,\n\s*MaxBeginScenesPerPresent, FrameStereoPoseSequence,',
    'DuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws, FixedFunctionNonWorldDraws, OffscreenVerifiedWorldDraws,\n\t\t\t\tWorldClassificationFailures, StereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed ? 1 : 0,\n\t\t\t\tMrtRejectedDraws, RestoreFailures, PoseSequenceMismatchFrames, MultiBeginScenePresents,\n\t\t\t\tMaxBeginScenesPerPresent, FrameStereoPoseSequence,\n\t\t\t\tOcclusionQueriesCreated, OcclusionQueryBegins, OcclusionQueryEnds, ActiveOcclusionQueries.load(std::memory_order_acquire), OcclusionStereoRejects,',
    'summary head args')
s = sub_once(s,
    r'FailureCounts\[OutRunVR::StereoFailureDepthStateChanged\], FailureCounts\[OutRunVR::StereoFailurePoseSequenceMismatch\]\);',
    'FailureCounts[OutRunVR::StereoFailureDepthStateChanged], FailureCounts[OutRunVR::StereoFailurePoseSequenceMismatch],\n\t\t\t\tFailureCounts[OutRunVR::StereoFailureOffscreenWorld], FailureCounts[OutRunVR::StereoFailureOcclusionQueryActive]);',
    'summary tail args')
# Present/reset boundaries.
s = sub_once(s,
    r'spdlog::info\("VR stereo: SBS transport active; two-phase Present commit \+ effective eye pose published in Frame\.v1"\);',
    'spdlog::info("VR stereo: TRUE STEREO active; PC backbuffer is SBS transport {}x{} from the two eye renders; no third scene render", BackBufferDesc.Width, BackBufferDesc.Height);',
    'true stereo monitor log')
s = sub_once(s,
    r'(\t\t\tFrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FramePoseMismatchLogged=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata=\{\};return hr;)',
    r'\t\t\tOutRunVRRenderer::NotifyGamePresent();\n\1',
    'present unlock')
s = sub_once(s,
    r'(\t\t\tReleaseStereoResources\(\);\n\t\t\tAuxRenderTargetActive = \{\};)',
    r'\t\t\tOutRunVRRenderer::NotifyGameReset();\n\1\n\t\t\tActiveOcclusionQueries.store(0, std::memory_order_release);',
    'reset pose/query state')
# Install CreateQuery hook and proactively create one query to arm Issue hook.
s = sub_once(s,
    r'(\t\t\tSetVertexShaderHook = safetyhook::create_inline\(vtable\[SetVertexShaderVtableIndex\], SetVertexShaderDest\);\n)',
    r'\1\t\t\tCreateQueryHook = safetyhook::create_inline(vtable[CreateQueryVtableIndex], CreateQueryDest);\n',
    'CreateQuery hook install')
s = sub_once(s,
    r'!DrawPrimitiveUPHook \|\| !DrawIndexedPrimitiveUPHook \|\| !SetVertexShaderHook\)',
    '!DrawPrimitiveUPHook || !DrawIndexedPrimitiveUPHook || !SetVertexShaderHook || !CreateQueryHook)',
    'required CreateQuery hook')
s = sub_once(s,
    r'(\t\t\tInitializeAuxRenderTargetState\(device\);\n\t\t\tLastBeginSceneCountAtPresent = OutRunVRRenderer::GetBeginSceneCallCount\(\);)',
    r'\t\t\tIDirect3DQuery9* queryProbe = nullptr;\n\t\t\tif (SUCCEEDED(device->CreateQuery(D3DQUERYTYPE_OCCLUSION, &queryProbe)) && queryProbe) queryProbe->Release();\n\1',
    'query Issue probe')
s = sub_once(s,
    r'VR stereo: D3D9 full-eye renderer installed \(Reset/Present/RT/Depth/Clear/Draw\*/VS\)',
    'VR stereo: D3D9 full-eye renderer installed (Reset/Present/RT/Depth/Clear/Draw*/VS/CreateQuery)',
    'install log')
p.write_text(s, encoding='utf-8')

print('final VR hardening v2 applied')
