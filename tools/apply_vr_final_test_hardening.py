from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 match, got {n}")
    return text.replace(old, new, 1)

root = Path('.')

# ---- shared protocol / interfaces (ABI sizes unchanged) ----
p = root / 'src/vr_shared.hpp'
s = p.read_text(encoding='utf-8')
s = replace_once(s,
'''        StereoFailureWorldClassificationFailed = 17,
        StereoFailureStencilUnsynchronized = 18,
''',
'''        StereoFailureWorldClassificationFailed = 17,
        StereoFailureStencilUnsynchronized = 18,
        StereoFailureOffscreenWorld = 19,
        StereoFailureOcclusionQueryActive = 20,
''', 'shared failure reasons')
s = replace_once(s,
'''    std::uint64_t GetBeginSceneCallCount();
}
''',
'''    std::uint64_t GetBeginSceneCallCount();
    void NotifyGamePresent();
    void NotifyGameReset();
}
''', 'renderer present/reset declarations')
p.write_text(s, encoding='utf-8')

# ---- renderer: lock one pose for the whole D3D9 Present ----
p = root / 'src/vr_renderer_probe.cpp'
s = p.read_text(encoding='utf-8')
s = replace_once(s,
'''\t\tstd::uint32_t LatchedPoseSequence = 0;

\t\tfloat LastVerifiedWvp[16]{};
''',
'''\t\tstd::uint32_t LatchedPoseSequence = 0;
\t\tbool PresentPoseLocked = false;

\t\tfloat LastVerifiedWvp[16]{};
''', 'present pose lock state')
s = replace_once(s,
'''\t\tstd::uint64_t UnsafeAddressRejects = 0;
''',
'''\t\tstd::uint64_t UnsafeAddressRejects = 0;
\t\tstd::uint64_t ReusedPoseSceneCalls = 0;
''', 'pose reuse telemetry')
s = replace_once(s,
'''\t\tvoid LatchFramePose()
\t\t{
\t\t\t++BeginSceneCalls;
\t\t\tResetFrameState();
''',
'''\t\tvoid LatchFramePose()
\t\t{
\t\t\tResetFrameState();
''', 'remove begin count from latch')
needle = '''\t\tbool UploadContainsOutRunWvp(UINT startRegister, UINT vector4fCount)
'''
insert = '''\t\tvoid ReusePresentPoseForScene()
\t\t{
\t\t\t// A single D3D9 Present must never contain geometry built from two
\t\t\t// different HMD samples. Additional BeginScene calls reuse the first
\t\t\t// scene's pose but start with a clean per-scene WVP verification marker.
\t\t\t++ReusedPoseSceneCalls;
\t\t\tInvalidateVerifiedWvp();
\t\t\tRestoreCullingCamera();
\t\t\tFrameTelemetryFlags = ClientHookAlive;
\t\t\tif (LatchedPoseSequence != 0) FrameTelemetryFlags |= ClientHostPoseValid;
\t\t\tif (Settings::VRAutoEnableWhenHostPresent) FrameTelemetryFlags |= ClientAutoEnabled;
\t\t\tif (LatchedHeadInverseValid) ApplyCullingCameraSync();
\t\t}

'''
s = replace_once(s, needle, insert + needle, 'insert pose reuse helper')
s = replace_once(s,
'''\t\t\tspdlog::info(
\t\t\t\t"VR renderer: beginScene={} c64Candidate={} verified={} prepared={} uploadOk={} uploadFail={} rejected={} unsafe={} latchedSeq={} wvpGen={}",
\t\t\t\tBeginSceneCalls, WvpCandidateCalls, WvpVerifiedCalls, WvpPreparedCalls,
\t\t\t\tWvpUploadSucceededCalls, WvpUploadFailedCalls, WvpRejectedCalls,
\t\t\t\tUnsafeAddressRejects, LatchedPoseSequence, LastVerifiedWvpGeneration);
''',
'''\t\t\tspdlog::info(
\t\t\t\t"VR renderer: beginScene={} poseReuse={} c64Candidate={} verified={} prepared={} uploadOk={} uploadFail={} rejected={} unsafe={} latchedSeq={} wvpGen={} presentPoseLocked={}",
\t\t\t\tBeginSceneCalls, ReusedPoseSceneCalls, WvpCandidateCalls, WvpVerifiedCalls, WvpPreparedCalls,
\t\t\t\tWvpUploadSucceededCalls, WvpUploadFailedCalls, WvpRejectedCalls,
\t\t\t\tUnsafeAddressRejects, LatchedPoseSequence, LastVerifiedWvpGeneration, PresentPoseLocked ? 1 : 0);
''', 'renderer summary')
s = replace_once(s,
'''\t\tHRESULT __stdcall BeginSceneDest(IDirect3DDevice9* device)
\t\t{
\t\t\tconst HRESULT result = BeginSceneHook.stdcall<HRESULT>(device);
\t\t\tif (!IsGameDevice(device) || OutRunVRStereo::IsInternalStereoPassActive())
\t\t\t\treturn result;
\t\t\tif (SUCCEEDED(result))
\t\t\t\tLatchFramePose();
\t\t\telse
\t\t\t\tResetFrameState();
\t\t\treturn result;
\t\t}
''',
'''\t\tHRESULT __stdcall BeginSceneDest(IDirect3DDevice9* device)
\t\t{
\t\t\tconst HRESULT result = BeginSceneHook.stdcall<HRESULT>(device);
\t\t\tif (!IsGameDevice(device) || OutRunVRStereo::IsInternalStereoPassActive())
\t\t\t\treturn result;
\t\t\tif (SUCCEEDED(result))
\t\t\t{
\t\t\t\t++BeginSceneCalls;
\t\t\t\tif (!PresentPoseLocked)
\t\t\t\t{
\t\t\t\t\tLatchFramePose();
\t\t\t\t\tPresentPoseLocked = GameRendererIsActive();
\t\t\t\t}
\t\t\t\telse
\t\t\t\t\tReusePresentPoseForScene();
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tPresentPoseLocked = false;
\t\t\t\tResetFrameState();
\t\t\t}
\t\t\treturn result;
\t\t}
''', 'begin scene present latch')
s = replace_once(s,
'''\tstd::uint64_t GetBeginSceneCallCount()
\t{
\t\treturn BeginSceneCalls;
\t}

''',
'''\tstd::uint64_t GetBeginSceneCallCount()
\t{
\t\treturn BeginSceneCalls;
\t}

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

''', 'renderer present/reset exports')
p.write_text(s, encoding='utf-8')

# ---- stereo: fixed-function classification, offscreen fail-closed, occlusion guard, telemetry ----
p = root / 'src/vr_stereo.cpp'
s = p.read_text(encoding='utf-8')
s = replace_once(s,
'''#include <cstring>
''',
'''#include <cstring>
''', 'keep include anchor')
s = replace_once(s,
'''\t\tconstexpr std::size_t SetVertexShaderVtableIndex = 92;
''',
'''\t\tconstexpr std::size_t SetVertexShaderVtableIndex = 92;
\t\tconstexpr std::size_t CreateQueryVtableIndex = 118;
\t\tconstexpr std::size_t QueryIssueVtableIndex = 6;
''', 'query vtable indices')
s = replace_once(s,
'''\t\tSafetyHookInline SetVertexShaderHook{};
''',
'''\t\tSafetyHookInline SetVertexShaderHook{};
\t\tSafetyHookInline CreateQueryHook{};
\t\tSafetyHookInline QueryIssueHook{};
''', 'query hooks')
s = replace_once(s,
'''\t\tstd::atomic<std::uint64_t> VertexShaderSerial{ 0 };
''',
'''\t\tstd::atomic<std::uint64_t> VertexShaderSerial{ 0 };
\t\tstd::atomic<int> ActiveOcclusionQueries{ 0 };
''', 'active occlusion count')
s = replace_once(s,
'''\t\tstd::uint64_t MaxBeginScenesPerPresent = 0;
\t\tstd::uint64_t LastBeginSceneCountAtPresent = 0;
''',
'''\t\tstd::uint64_t MaxBeginScenesPerPresent = 0;
\t\tstd::uint64_t LastBeginSceneCountAtPresent = 0;
\t\tstd::uint64_t FixedFunctionNonWorldDraws = 0;
\t\tstd::uint64_t OcclusionQueriesCreated = 0;
\t\tstd::uint64_t OcclusionQueryBegins = 0;
\t\tstd::uint64_t OcclusionQueryEnds = 0;
\t\tstd::uint64_t OcclusionStereoRejects = 0;
''', 'new telemetry counters')
s = replace_once(s,
'''\t\tbool FirstClassificationFailureLogged = false;
''',
'''\t\tbool FirstClassificationFailureLogged = false;
\t\tbool FirstOcclusionRejectLogged = false;
''', 'occlusion first log flag')
# null VS: fixed-function/non-shader work is non-world, not a fatal classifier error.
s = replace_once(s,
'''\t\t\tstd::uintptr_t shaderIdentity = 0;
\t\t\tstd::uint64_t shaderSerial = 0;
\t\t\tif (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))
\t\t\t\treturn EyeBuildResult::FatalError;
''',
'''\t\t\tif (CurrentVertexShaderIdentity.load(std::memory_order_acquire) == 0)
\t\t\t{
\t\t\t\t++FixedFunctionNonWorldDraws;
\t\t\t\treturn EyeBuildResult::NonWorld;
\t\t\t}
\t\t\tstd::uintptr_t shaderIdentity = 0;
\t\t\tstd::uint64_t shaderSerial = 0;
\t\t\tif (!GetCurrentShaderEpoch(shaderIdentity, shaderSerial))
\t\t\t\treturn EyeBuildResult::FatalError;
''', 'fixed function classification')
# occlusion active gate before any duplicate draw.
s = replace_once(s,
'''\t\t\tif (AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);++MrtRejectedDraws;if(!FirstMrtRejectLogged){FirstMrtRejectLogged=true;spdlog::info("VR stereo: auxiliary MRT active; current Present is marked incomplete");}return false;}
''',
'''\t\t\tif (AnyAuxRenderTargetActive()){PoisonFrame(OutRunVR::StereoFailureMrtActive);++MrtRejectedDraws;if(!FirstMrtRejectLogged){FirstMrtRejectLogged=true;spdlog::info("VR stereo: auxiliary MRT active; current Present is marked incomplete");}return false;}
\t\t\tif (ActiveOcclusionQueries.load(std::memory_order_acquire) > 0){++OcclusionStereoRejects;PoisonFrame(OutRunVR::StereoFailureOcclusionQueryActive);if(!FirstOcclusionRejectLogged){FirstOcclusionRejectLogged=true;spdlog::warn("VR stereo: active D3D9 occlusion query detected; right-eye draw suppressed so game query results remain single-render accurate");}return false;}
''', 'occlusion duplicate guard')
# offscreen verified world becomes explicit fail-closed, with first detailed RT log.
s = replace_once(s,
'''\t\t\t\tif (CurrentDrawMatchesVerifiedWorld(device))
\t\t\t\t{
\t\t\t\t\t++OffscreenVerifiedWorldDraws;
\t\t\t\t\tif (!FirstOffscreenWorldLogged)
\t\t\t\t\t{
\t\t\t\t\t\tFirstOffscreenWorldLogged = true;
\t\t\t\t\t\tspdlog::warn("VR stereo: verified world geometry rendered to an offscreen RT; pass remains single-eye and is telemetry-only until its role is identified");
\t\t\t\t\t}
\t\t\t\t}
''',
'''\t\t\t\tif (CurrentDrawMatchesVerifiedWorld(device))
\t\t\t\t{
\t\t\t\t\t++OffscreenVerifiedWorldDraws;
\t\t\t\t\tPoisonFrame(OutRunVR::StereoFailureOffscreenWorld);
\t\t\t\t\tif (!FirstOffscreenWorldLogged)
\t\t\t\t\t{
\t\t\t\t\t\tFirstOffscreenWorldLogged = true;
\t\t\t\t\t\tD3DSURFACE_DESC rtDesc{}, depthDesc{};
\t\t\t\t\t\tconst bool rtOk = TrackedRenderTarget && SUCCEEDED(TrackedRenderTarget->GetDesc(&rtDesc));
\t\t\t\t\t\tconst bool depthOk = TrackedDepthStencil && SUCCEEDED(TrackedDepthStencil->GetDesc(&depthDesc));
\t\t\t\t\t\tspdlog::warn("VR stereo: VERIFIED WORLD draw hit offscreen RT; Present forced to mono fallback. rt={}x{} fmt={} msaa={} depthFmt={} depthMsaa={}",
\t\t\t\t\t\t\trtOk ? rtDesc.Width : 0u, rtOk ? rtDesc.Height : 0u, rtOk ? static_cast<int>(rtDesc.Format) : -1,
\t\t\t\t\t\t\trtOk ? static_cast<int>(rtDesc.MultiSampleType) : -1,
\t\t\t\t\t\t\tdepthOk ? static_cast<int>(depthDesc.Format) : -1,
\t\t\t\t\t\t\tdepthOk ? static_cast<int>(depthDesc.MultiSampleType) : -1);
\t\t\t\t\t}
\t\t\t\t}
''', 'offscreen world fail closed')
# Add query hook functions before SetVertexShaderDest.
needle = '''\t\tHRESULT __stdcall SetVertexShaderDest(IDirect3DDevice9* device, IDirect3DVertexShader9* shader)
'''
query_code = r'''\t\tHRESULT __stdcall QueryIssueDest(IDirect3DQuery9* query, DWORD issueFlags)
\t\t{
\t\t\tconst HRESULT hr = QueryIssueHook.stdcall<HRESULT>(query, issueFlags);
\t\t\tif (FAILED(hr) || !query || query->GetType() != D3DQUERYTYPE_OCCLUSION) return hr;
\t\t\tIDirect3DDevice9* device = nullptr;
\t\t\tif (FAILED(query->GetDevice(&device)) || !device) return hr;
\t\t\tconst bool gameQuery = IsGameDevice(device);
\t\t\tdevice->Release();
\t\t\tif (!gameQuery) return hr;
\t\t\tif ((issueFlags & D3DISSUE_BEGIN) != 0)
\t\t\t{
\t\t\t\tActiveOcclusionQueries.fetch_add(1, std::memory_order_acq_rel);
\t\t\t\t++OcclusionQueryBegins;
\t\t\t}
\t\t\tif ((issueFlags & D3DISSUE_END) != 0)
\t\t\t{
\t\t\t\tint current = ActiveOcclusionQueries.load(std::memory_order_acquire);
\t\t\t\twhile (current > 0 && !ActiveOcclusionQueries.compare_exchange_weak(
\t\t\t\t\tcurrent, current - 1, std::memory_order_acq_rel, std::memory_order_acquire)) {}
\t\t\t\t++OcclusionQueryEnds;
\t\t\t}
\t\t\treturn hr;
\t\t}

\t\tHRESULT __stdcall CreateQueryDest(IDirect3DDevice9* device, D3DQUERYTYPE type, IDirect3DQuery9** query)
\t\t{
\t\t\tconst HRESULT hr = CreateQueryHook.stdcall<HRESULT>(device, type, query);
\t\t\tif (!IsGameDevice(device) || FAILED(hr) || type != D3DQUERYTYPE_OCCLUSION || !query || !*query) return hr;
\t\t\t++OcclusionQueriesCreated;
\t\t\tif (!QueryIssueHook)
\t\t\t{
\t\t\t\tvoid** vtable = *reinterpret_cast<void***>(*query);
\t\t\t\tif (vtable) QueryIssueHook = safetyhook::create_inline(vtable[QueryIssueVtableIndex], QueryIssueDest);
\t\t\t\tif (QueryIssueHook) spdlog::info("VR stereo: D3D9 occlusion-query Issue hook armed; active queries will fail closed instead of double-counting right-eye samples");
\t\t\t\telse spdlog::warn("VR stereo: could not hook IDirect3DQuery9::Issue; occlusion-query protection unavailable");
\t\t\t}
\t\t\treturn hr;
\t\t}

'''.replace('\\t','\t')
s = replace_once(s, needle, query_code + needle, 'query hooks implementation')
# Expanded summary + new failures.
s = replace_once(s,
'''\t\t\tspdlog::info("VR stereo: draws={} world={} ui/effect={} offscreenWorld={} classifyFail={} composeOk={} composeFail={} rightFail={} mrtReject={} restoreFail={} poseMismatchFrames={} multiBeginPresent={} maxBeginPerPresent={} poseSeq={} failures[pose={},res={},mrt={},viewport={},classify={},depth={},stencil={},clear={},rightState={},rightWvp={},rightDraw={},restore={},compose={},present={},depthState={},poseMismatch={}]",
''',
'''\t\t\tspdlog::info("VR stereo: draws={} world={} ui/effect={} fixedFn={} offscreenWorld={} classifyFail={} composeOk={} composeFail={} rightFail={} mrtReject={} restoreFail={} poseMismatchFrames={} multiBeginPresent={} maxBeginPerPresent={} poseSeq={} occ[created={},begin={},end={},active={},reject={}] failures[pose={},res={},mrt={},viewport={},classify={},depth={},stencil={},clear={},rightState={},rightWvp={},rightDraw={},restore={},compose={},present={},depthState={},poseMismatch={},offscreen={},occlusion={}]",
''', 'summary format')
s = replace_once(s,
'''\t\t\t\tDuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws, OffscreenVerifiedWorldDraws,
\t\t\t\tWorldClassificationFailures, StereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed ? 1 : 0,
\t\t\t\tMrtRejectedDraws, RestoreFailures, PoseSequenceMismatchFrames, MultiBeginScenePresents,
\t\t\t\tMaxBeginScenesPerPresent, FrameStereoPoseSequence,
''',
'''\t\t\t\tDuplicatedDraws, WorldStereoDraws, NonWorldDuplicatedDraws, FixedFunctionNonWorldDraws, OffscreenVerifiedWorldDraws,
\t\t\t\tWorldClassificationFailures, StereoComposeSuccess, StereoComposeFailure, FrameRightDrawFailed ? 1 : 0,
\t\t\t\tMrtRejectedDraws, RestoreFailures, PoseSequenceMismatchFrames, MultiBeginScenePresents,
\t\t\t\tMaxBeginScenesPerPresent, FrameStereoPoseSequence,
\t\t\t\tOcclusionQueriesCreated, OcclusionQueryBegins, OcclusionQueryEnds, ActiveOcclusionQueries.load(std::memory_order_acquire), OcclusionStereoRejects,
''', 'summary args head')
s = replace_once(s,
'''\t\t\t\tFailureCounts[OutRunVR::StereoFailureDepthStateChanged], FailureCounts[OutRunVR::StereoFailurePoseSequenceMismatch]);
''',
'''\t\t\t\tFailureCounts[OutRunVR::StereoFailureDepthStateChanged], FailureCounts[OutRunVR::StereoFailurePoseSequenceMismatch],
\t\t\t\tFailureCounts[OutRunVR::StereoFailureOffscreenWorld], FailureCounts[OutRunVR::StereoFailureOcclusionQueryActive]);
''', 'summary args tail')
# Present boundary unlock + explicit transport log.
s = replace_once(s,
'''\t\t\tif(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete){PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,pendingFrameId);PublishRenderFrame(OutRunVR::StereoSbsActive,pendingFrameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata);if(!FirstStereoActiveLogged){FirstStereoActiveLogged=true;spdlog::info("VR stereo: SBS transport active; two-phase Present commit + effective eye pose published in Frame.v1");}}
''',
'''\t\t\tif(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete){PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,pendingFrameId);PublishRenderFrame(OutRunVR::StereoSbsActive,pendingFrameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata);if(!FirstStereoActiveLogged){FirstStereoActiveLogged=true;spdlog::info("VR stereo: TRUE STEREO active; PC backbuffer is an SBS transport {}x{} composed from the two eye renders (no third scene render)",BackBufferDesc.Width,BackBufferDesc.Height);}}
''', 'active transport log')
s = replace_once(s,
'''\t\t\tFrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FramePoseMismatchLogged=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;
''',
'''\t\t\tOutRunVRRenderer::NotifyGamePresent();FrameHadDuplicatedDraw=false;FrameHadWorldStereo=false;FrameRightDrawFailed=false;FrameStereoIncomplete=false;FramePoseMismatchLogged=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoPoseSequence=0;FrameStereoMetadata={};return hr;
''', 'present boundary notify')
# Reset renderer pose lock and query state.
s = replace_once(s,
'''\t\t\tReleaseStereoResources();
\t\t\tAuxRenderTargetActive = {};
''',
'''\t\t\tOutRunVRRenderer::NotifyGameReset();
\t\t\tReleaseStereoResources();
\t\t\tAuxRenderTargetActive = {};
\t\t\tActiveOcclusionQueries.store(0, std::memory_order_release);
''', 'reset renderer/query state')
# Install CreateQuery hook and include in required hook set.
s = replace_once(s,
'''\t\t\tSetVertexShaderHook = safetyhook::create_inline(vtable[SetVertexShaderVtableIndex], SetVertexShaderDest);
''',
'''\t\t\tSetVertexShaderHook = safetyhook::create_inline(vtable[SetVertexShaderVtableIndex], SetVertexShaderDest);
\t\t\tCreateQueryHook = safetyhook::create_inline(vtable[CreateQueryVtableIndex], CreateQueryDest);
''', 'create query hook install')
s = replace_once(s,
'''\t\t\t\t!ClearHook || !DrawPrimitiveHook || !DrawIndexedPrimitiveHook ||
\t\t\t\t!DrawPrimitiveUPHook || !DrawIndexedPrimitiveUPHook || !SetVertexShaderHook)
''',
'''\t\t\t\t!ClearHook || !DrawPrimitiveHook || !DrawIndexedPrimitiveHook ||
\t\t\t\t!DrawPrimitiveUPHook || !DrawIndexedPrimitiveUPHook || !SetVertexShaderHook || !CreateQueryHook)
''', 'required query hook')
# Create a harmless probe query so the shared Query::Issue vtable hook is armed even if the game created its queries before our installer ran.
s = replace_once(s,
'''\t\t\tInitializeAuxRenderTargetState(device);
\t\t\tLastBeginSceneCountAtPresent = OutRunVRRenderer::GetBeginSceneCallCount();
''',
'''\t\t\tIDirect3DQuery9* queryProbe = nullptr;
\t\t\tif (SUCCEEDED(device->CreateQuery(D3DQUERYTYPE_OCCLUSION, &queryProbe)) && queryProbe) queryProbe->Release();
\t\t\tInitializeAuxRenderTargetState(device);
\t\t\tLastBeginSceneCountAtPresent = OutRunVRRenderer::GetBeginSceneCallCount();
''', 'query issue probe')
s = replace_once(s,
'''\t\t\tspdlog::info("VR stereo: D3D9 full-eye renderer installed (Reset/Present/RT/Depth/Clear/Draw*/VS)");
''',
'''\t\t\tspdlog::info("VR stereo: D3D9 full-eye renderer installed (Reset/Present/RT/Depth/Clear/Draw*/VS/CreateQuery)");
''', 'install log')
p.write_text(s, encoding='utf-8')

print('final VR test hardening patch applied')
