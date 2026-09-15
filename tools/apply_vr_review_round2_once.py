from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one match, got {count}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def require(path: str, marker: str) -> None:
    text = Path(path).read_text(encoding="utf-8")
    if marker not in text:
        raise RuntimeError(f"{path}: required marker missing after patch: {marker}")


# ---------------------------------------------------------------------------
# 1) Base D3D9 stereo: fail closed when occlusion-query tracking cannot arm,
#    and keep a ResetEx fallback in the base reset callback for promoted D3D9Ex
#    devices even if the later R13 overlay cannot install.
# ---------------------------------------------------------------------------
p = "src/vr/d3d9/stereo_renderer_r7.inc"
replace_once(
    p,
    "\t\tstd::atomic<int> ActiveOcclusionQueries{ 0 };\n",
    "\t\tstd::atomic<int> ActiveOcclusionQueries{ 0 };\n"
    "\t\tstd::atomic<bool> OcclusionQueryTrackingUnavailable{ false };\n",
)
replace_once(
    p,
    "\t\tbool FirstOcclusionRejectLogged = false;\n",
    "\t\tbool FirstOcclusionRejectLogged = false;\n"
    "\t\tbool FirstOcclusionTrackingUnavailableLogged = false;\n",
)
replace_once(
    p,
    "\t\t\tif(InternalStereoPass||!StereoWanted()||!TargetIsBackBuffer())return false;if(AnyAuxRenderTargetActive())",
    "\t\t\tif(InternalStereoPass||!StereoWanted()||!TargetIsBackBuffer())return false;"
    "if(OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire)){"
    "PoisonFrame(OutRunVR::StereoFailureOcclusionQueryActive);++OcclusionStereoRejects;"
    "if(!FirstOcclusionTrackingUnavailableLogged){FirstOcclusionTrackingUnavailableLogged=true;"
    "spdlog::error(\"VR stereo: occlusion-query Issue tracking unavailable; stereo duplication fails closed to single-execution mono until tracking recovers\");}"
    "return false;}if(AnyAuxRenderTargetActive())",
)
replace_once(
    p,
    "\t\t\tconst bool occlusionActive=ActiveOcclusionQueries.load(std::memory_order_acquire)>0;\n",
    "\t\t\tconst bool occlusionActive=ActiveOcclusionQueries.load(std::memory_order_acquire)>0||\n"
    "\t\t\t\tOcclusionQueryTrackingUnavailable.load(std::memory_order_acquire);\n",
)
old_create_query = "\t\tHRESULT __stdcall CreateQueryDest(IDirect3DDevice9*device,D3DQUERYTYPE type,IDirect3DQuery9**query){const HRESULT hr=CreateQueryHook.stdcall<HRESULT>(device,type,query);if(!IsGameDevice(device)||FAILED(hr)||type!=D3DQUERYTYPE_OCCLUSION||!query||!*query)return hr;++OcclusionQueriesCreated;if(!QueryIssueHook){void**queryVtable=*reinterpret_cast<void***>(*query);if(queryVtable)QueryIssueHook=safetyhook::create_inline(queryVtable[QueryIssueVtableIndex],QueryIssueDest);if(QueryIssueHook)spdlog::info(\"VR stereo: occlusion-query Issue hook armed; active query draws remain single-eye without invalidating stereo frames\");else spdlog::warn(\"VR stereo: failed to hook IDirect3DQuery9::Issue; query protection unavailable\");}return hr;}\n"
new_create_query = "\t\tHRESULT __stdcall CreateQueryDest(IDirect3DDevice9*device,D3DQUERYTYPE type,IDirect3DQuery9**query){const HRESULT hr=CreateQueryHook.stdcall<HRESULT>(device,type,query);if(!IsGameDevice(device)||FAILED(hr)||type!=D3DQUERYTYPE_OCCLUSION||!query||!*query)return hr;++OcclusionQueriesCreated;if(!QueryIssueHook){void**queryVtable=*reinterpret_cast<void***>(*query);if(queryVtable)QueryIssueHook=safetyhook::create_inline(queryVtable[QueryIssueVtableIndex],QueryIssueDest);if(QueryIssueHook){OcclusionQueryTrackingUnavailable.store(false,std::memory_order_release);spdlog::info(\"VR stereo: occlusion-query Issue hook armed; active query draws remain single-eye without invalidating stereo frames\");}else{OcclusionQueryTrackingUnavailable.store(true,std::memory_order_release);spdlog::error(\"VR stereo: failed to hook IDirect3DQuery9::Issue; stereo duplication disabled fail-closed for query safety\");}}return hr;}\n"
replace_once(p, old_create_query, new_create_query)
old_reset = "\t\tHRESULT __stdcall ResetDest(IDirect3DDevice9*device,D3DPRESENT_PARAMETERS*params){if(!IsGameDevice(device))return ResetHook.stdcall<HRESULT>(device,params);OutRunVRRenderer::NotifyGameReset();ReleaseStereoResources();AuxRenderTargetActive={};ActiveOcclusionQueries.store(0,std::memory_order_release);CurrentVertexShaderIdentity.store(0,std::memory_order_release);VertexShaderSerial.store(0,std::memory_order_release);LastStereoWanted=false;RightStencilSynchronized=true;FramePoseMismatchLogged=false;FirstMainDepthReuseLogged=false;FirstMainClearLogged=false;FirstDepthBootstrapLogged=false;PresentEpoch=1;LastMainDepthClearEpoch=0;LastMainDepthClearFlags=0;LastMainDepthClearZ=1.0f;LastMainDepthClearStencil=0;LastMainDepthClearDesc={};LastBeginSceneCountAtPresent=OutRunVRRenderer::GetBeginSceneCallCount();FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoMetadata={};PublishStereoState(OutRunVR::StereoDisabled,false,0,0);PublishRenderFrame(OutRunVR::StereoDisabled,0,0,0,OutRunVR::StereoFailureNone,nullptr);const HRESULT hr=ResetHook.stdcall<HRESULT>(device,params);if(SUCCEEDED(hr))EnsureStereoResources(device);return hr;}\n"
new_reset = "\t\tHRESULT __stdcall ResetDest(IDirect3DDevice9*device,D3DPRESENT_PARAMETERS*params){if(!IsGameDevice(device))return ResetHook.stdcall<HRESULT>(device,params);OutRunVRRenderer::NotifyGameReset();ReleaseStereoResources();AuxRenderTargetActive={};ActiveOcclusionQueries.store(0,std::memory_order_release);CurrentVertexShaderIdentity.store(0,std::memory_order_release);VertexShaderSerial.store(0,std::memory_order_release);LastStereoWanted=false;RightStencilSynchronized=true;FramePoseMismatchLogged=false;FirstMainDepthReuseLogged=false;FirstMainClearLogged=false;FirstDepthBootstrapLogged=false;PresentEpoch=1;LastMainDepthClearEpoch=0;LastMainDepthClearFlags=0;LastMainDepthClearZ=1.0f;LastMainDepthClearStencil=0;LastMainDepthClearDesc={};LastBeginSceneCountAtPresent=OutRunVRRenderer::GetBeginSceneCallCount();FrameStereoIncomplete=false;FrameFailureReason=OutRunVR::StereoFailureNone;FrameStereoMetadata={};PublishStereoState(OutRunVR::StereoDisabled,false,0,0);PublishRenderFrame(OutRunVR::StereoDisabled,0,0,0,OutRunVR::StereoFailureNone,nullptr);HRESULT hr=D3DERR_INVALIDCALL;if(OutRunVRD3D9ExUpgradeR13::IsCompatDevice(device)){if(!OutRunVRD3D9ExUpgradeR13::ResetCompatDevice(device,params,hr)){spdlog::error(\"VR stereo: promoted D3D9Ex device lost ResetEx fallback ownership\");return D3DERR_INVALIDCALL;}}else hr=ResetHook.stdcall<HRESULT>(device,params);if(SUCCEEDED(hr))EnsureStereoResources(device);return hr;}\n"
replace_once(p, old_reset, new_reset)
replace_once(p, "\t\t\tSleep(250);\n\t\t\tfor(int attempt=0;attempt<1200;++attempt)\n", "\t\t\t// No fixed startup delay: the promoted D3D9Ex Reset shim is handed off\n\t\t\t// to this base callback as soon as the game publishes its device.\n\t\t\tfor(int attempt=0;attempt<1200;++attempt)\n")

# R13 unsafe-transition policy must also fail closed if query tracking itself is unavailable.
p = "src/vr/d3d9/stereo_renderer_r13.cpp"
replace_once(
    p,
    "        const bool unsafeOcclusion = mainTarget &&\n                ActiveOcclusionQueries.load(std::memory_order_acquire) > 0;\n",
    "        const bool unsafeOcclusion = mainTarget &&\n                (ActiveOcclusionQueries.load(std::memory_order_acquire) > 0 ||\n                 OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire));\n",
)
replace_once(
    p,
    "        SafetyHookInline R13DrawIndexedPrimitiveUPR9Hook{};\n\n        std::uint64_t R13SafeAckBackpressure = 0;\n",
    "        SafetyHookInline R13DrawIndexedPrimitiveUPR9Hook{};\n\n"
    "        constexpr std::uint32_t R13InstallPending = 0;\n"
    "        constexpr std::uint32_t R13InstallReady = 1;\n"
    "        constexpr std::uint32_t R13InstallFailed = 2;\n"
    "        std::atomic<std::uint32_t> R13InstallState{R13InstallPending};\n\n"
    "        std::uint64_t R13SafeAckBackpressure = 0;\n",
)
replace_once(
    p,
    "        void R13RollbackOverlayHooks() noexcept\n        {\n            R13ResetR9Hook = {};\n",
    "        void R13RollbackOverlayHooks() noexcept\n        {\n            R13ResetR9Hook = {};\n",
)
replace_once(
    p,
    "            R13DrawIndexedPrimitiveUPR9Hook = {};\n        }\n\n        DWORD WINAPI R13StereoInstallThread(void*)\n",
    "            R13DrawIndexedPrimitiveUPR9Hook = {};\n"
    "            R13InstallState.store(R13InstallFailed, std::memory_order_release);\n"
    "        }\n\n        DWORD WINAPI R13StereoInstallThread(void*)\n",
)
replace_once(
    p,
    "        DWORD WINAPI R13StereoInstallThread(void*)\n        {\n            for (int attempt = 0; attempt < 4800; ++attempt)\n",
    "        DWORD WINAPI R13StereoInstallThread(void*)\n        {\n"
    "            R13InstallState.store(R13InstallPending, std::memory_order_release);\n"
    "            for (int attempt = 0; attempt < 4800; ++attempt)\n",
)
replace_once(
    p,
    "                    spdlog::error(\n                        \"VR R13: R9 callback transaction failed; hardening overlay not installed\");\n                    return 0;\n",
    "                    R13InstallState.store(R13InstallFailed, std::memory_order_release);\n"
    "                    spdlog::error(\n                        \"VR R13: R9 callback transaction failed; hardening overlay not installed\");\n                    return 0;\n",
)
replace_once(
    p,
    "                        spdlog::info(\n                            \"VR R13: stereo hardening ACTIVE; atomic R7/R9 install handoff + single ResetEx owner + GPU-completion direct-ring backpressure + single-execution MRT/occlusion fallback\");\n",
    "                        R13InstallState.store(R13InstallReady, std::memory_order_release);\n"
    "                        spdlog::info(\n                            \"VR R13: stereo hardening ACTIVE; transactional R13 install state=READY + atomic R7/R9 handoff + single ResetEx owner + GPU-completion direct-ring backpressure + single-execution MRT/occlusion fallback\");\n",
)
replace_once(
    p,
    "            spdlog::warn(\n                \"VR R13: R9 transactional install did not become ready; hardening overlay not installed\");\n            return 0;\n",
    "            R13InstallState.store(R13InstallFailed, std::memory_order_release);\n"
    "            spdlog::warn(\n                \"VR R13: R9 transactional install did not become ready; hardening overlay not installed\");\n            return 0;\n",
)
replace_once(
    p,
    "                if (!thread)\n                    return false;\n",
    "                if (!thread)\n                {\n                    R13InstallState.store(R13InstallFailed, std::memory_order_release);\n                    return false;\n                }\n",
)

# ---------------------------------------------------------------------------
# 2) Renderer hook publication: never poll/unhook SafetyHookInline cross-thread.
# ---------------------------------------------------------------------------
p = "src/vr/game/outrun_renderer.cpp"
replace_once(
    p,
    "\t\tSafetyHookInline SetVertexShaderConstantFHook{};\n\n\t\tHANDLE SharedMapping = nullptr;\n",
    "\t\tSafetyHookInline SetVertexShaderConstantFHook{};\n\n"
    "\t\tconstexpr std::uint32_t RendererInstallPending = 0;\n"
    "\t\tconstexpr std::uint32_t RendererInstallReady = 1;\n"
    "\t\tconstexpr std::uint32_t RendererInstallFailed = 2;\n"
    "\t\tstd::atomic<std::uint32_t> RendererInstallState{RendererInstallPending};\n"
    "\t\tstd::atomic<bool> RendererInjectionAllowed{true};\n\n"
    "\t\tHANDLE SharedMapping = nullptr;\n",
)
replace_once(
    p,
    "\t\t\tif (!LatchedHeadInverseValid || !GameRendererIsActive())\n\t\t\t\treturn false;\n",
    "\t\t\tif (!RendererInjectionAllowed.load(std::memory_order_acquire) ||\n"
    "\t\t\t\t!LatchedHeadInverseValid || !GameRendererIsActive())\n\t\t\t\treturn false;\n",
)
replace_once(
    p,
    "\t\t\tBeginSceneHook = safetyhook::create_inline(vtable[BeginSceneVtableIndex], BeginSceneDest);\n",
    "\t\t\tRendererInstallState.store(RendererInstallPending, std::memory_order_release);\n"
    "\t\t\tRendererInjectionAllowed.store(true, std::memory_order_release);\n"
    "\t\t\tBeginSceneHook = safetyhook::create_inline(vtable[BeginSceneVtableIndex], BeginSceneDest);\n",
)
replace_once(
    p,
    "\t\t\t\tSetVertexShaderConstantFHook = {};\n\t\t\t\tspdlog::error(\"VR renderer: failed to hook D3D9 renderer boundary\");\n\t\t\t\treturn false;\n",
    "\t\t\t\tSetVertexShaderConstantFHook = {};\n"
    "\t\t\t\tRendererInjectionAllowed.store(false, std::memory_order_release);\n"
    "\t\t\t\tRendererInstallState.store(RendererInstallFailed, std::memory_order_release);\n"
    "\t\t\t\tspdlog::error(\"VR renderer: failed to hook D3D9 renderer boundary; transactional rollback completed\");\n\t\t\t\treturn false;\n",
)
replace_once(
    p,
    "\t\t\tEnsureSharedState();\n\t\t\tspdlog::info(\"VR renderer: D3D9 hooks installed; v3-primary/v2-fallback frame-latched c64 WVP injection armed (vtbl 41/42/94)\");\n",
    "\t\t\tEnsureSharedState();\n"
    "\t\t\tRendererInstallState.store(RendererInstallReady, std::memory_order_release);\n"
    "\t\t\tspdlog::info(\"VR renderer: D3D9 hooks installed; atomic renderer install state=READY; v3-primary/v2-fallback frame-latched c64 WVP injection armed (vtbl 41/42/94)\");\n",
)
replace_once(
    p,
    "\t\t\tspdlog::warn(\"VR renderer: D3D9 device did not appear; renderer hook not installed\");\n\t\t\treturn 0;\n",
    "\t\t\tRendererInjectionAllowed.store(false, std::memory_order_release);\n"
    "\t\t\tRendererInstallState.store(RendererInstallFailed, std::memory_order_release);\n"
    "\t\t\tspdlog::warn(\"VR renderer: D3D9 device did not appear; renderer hook not installed\");\n\t\t\treturn 0;\n",
)
replace_once(
    p,
    "\t\t\tif (!thread)\n\t\t\t{\n\t\t\t\tspdlog::error(\"VR renderer: failed to create installer thread: {}\", GetLastError());\n\t\t\t\treturn false;\n\t\t\t}\n",
    "\t\t\tif (!thread)\n\t\t\t{\n"
    "\t\t\t\tRendererInjectionAllowed.store(false, std::memory_order_release);\n"
    "\t\t\t\tRendererInstallState.store(RendererInstallFailed, std::memory_order_release);\n"
    "\t\t\t\tspdlog::error(\"VR renderer: failed to create installer thread: {}\", GetLastError());\n\t\t\t\treturn false;\n\t\t\t}\n",
)

p = "src/vr/game/outrun_renderer_r13.cpp"
old_thread = '''        DWORD WINAPI R13RendererInstallThread(void*)
        {
            for (int attempt = 0; attempt < 1200; ++attempt)
            {
                if (SetVertexShaderConstantFHook)
                {
                    R13WvpCallbackHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&SetVertexShaderConstantFDest),
                        SetVertexShaderConstantFDestR13);
                    if (R13WvpCallbackHook)
                    {
                        spdlog::info("VR R13: renderer WVP target-classification guard armed");
                    }
                    else
                    {
                        // The offscreen guard is a correctness boundary, not an
                        // optional diagnostic. If it cannot be installed, remove
                        // the base c64 injection hook instead of allowing HMD WVP
                        // transforms to leak into reflection/shadow targets.
                        SetVertexShaderConstantFHook = {};
                        InvalidateVerifiedWvp();
                        spdlog::error(
                            "VR R13: failed to hook renderer c64 callback; base WVP injection removed to fail closed");
                    }
                    return 0;
                }
                Sleep(25);
            }
            spdlog::warn(
                "VR R13: renderer c64 callback did not become ready; target-classification guard not installed");
            return 0;
        }
'''
new_thread = '''        DWORD WINAPI R13RendererInstallThread(void*)
        {
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const std::uint32_t rendererState =
                    RendererInstallState.load(std::memory_order_acquire);
                if (rendererState == RendererInstallFailed)
                {
                    RendererInjectionAllowed.store(false, std::memory_order_release);
                    InvalidateVerifiedWvp();
                    spdlog::error(
                        "VR R13: base renderer hook transaction failed; WVP injection remains disabled");
                    return 0;
                }
                if (rendererState == RendererInstallReady)
                {
                    R13WvpCallbackHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&SetVertexShaderConstantFDest),
                        SetVertexShaderConstantFDestR13);
                    if (R13WvpCallbackHook)
                    {
                        spdlog::info(
                            "VR R13: renderer WVP target-classification guard armed via atomic renderer install handoff");
                    }
                    else
                    {
                        // Do not mutate a SafetyHookInline owned by another thread.
                        // The base callback stays installed but becomes a stock-WVP
                        // pass-through through this release/acquire policy flag.
                        RendererInjectionAllowed.store(false, std::memory_order_release);
                        InvalidateVerifiedWvp();
                        spdlog::error(
                            "VR R13: failed to hook renderer c64 callback; WVP injection disabled atomically to fail closed");
                    }
                    return 0;
                }
                Sleep(25);
            }
            RendererInjectionAllowed.store(false, std::memory_order_release);
            InvalidateVerifiedWvp();
            spdlog::warn(
                "VR R13: renderer transaction did not become ready; WVP injection disabled fail-closed");
            return 0;
        }
'''
replace_once(p, old_thread, new_thread)

# ---------------------------------------------------------------------------
# 3) Primary IPC ownership must distinguish dead from unknown/unqueryable PIDs.
# ---------------------------------------------------------------------------
p = "vrhost/src/ipc/host_state_v3_writer.hpp"
old_liveness = '''        static bool ProcessAlive(DWORD pid) noexcept
        {
            if (!pid)
                return false;
            HANDLE process = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
            if (!process)
                return false;
            const bool alive = WaitForSingleObject(process, 0) == WAIT_TIMEOUT;
            CloseHandle(process);
            return alive;
        }
'''
new_liveness = '''        enum class ProcessLiveness : std::uint8_t
        {
            Dead,
            Alive,
            Unknown
        };

        static ProcessLiveness QueryProcessLiveness(DWORD pid) noexcept
        {
            if (!pid)
                return ProcessLiveness::Dead;
            HANDLE process = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
            if (!process)
                return GetLastError() == ERROR_INVALID_PARAMETER
                    ? ProcessLiveness::Dead
                    : ProcessLiveness::Unknown;
            const DWORD wait = WaitForSingleObject(process, 0);
            CloseHandle(process);
            if (wait == WAIT_TIMEOUT)
                return ProcessLiveness::Alive;
            if (wait == WAIT_OBJECT_0)
                return ProcessLiveness::Dead;
            return ProcessLiveness::Unknown;
        }
'''
replace_once(p, old_liveness, new_liveness)
replace_once(
    p,
    "                if (observed != 0 && ProcessAlive(static_cast<DWORD>(observed)))\n                    throw std::runtime_error(\"another outrun-vr-host owns HostState.v3\");\n",
    "                if (observed != 0 &&\n"
    "                    QueryProcessLiveness(static_cast<DWORD>(observed)) != ProcessLiveness::Dead)\n"
    "                    throw std::runtime_error(\"another or unverified outrun-vr-host owns HostState.v3\");\n",
)

p = "vrhost/src/main.cpp"
old_main_liveness = '''    bool IsProcessAlive(DWORD pid)
    {
        if (!pid) return false;
        HANDLE p = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
        if (!p) return false;
        const bool alive = WaitForSingleObject(p, 0) == WAIT_TIMEOUT;
        CloseHandle(p);
        return alive;
    }
'''
new_main_liveness = '''    enum class ProcessLiveness : std::uint8_t
    {
        Dead,
        Alive,
        Unknown
    };

    ProcessLiveness QueryProcessLiveness(DWORD pid)
    {
        if (!pid) return ProcessLiveness::Dead;
        HANDLE p = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
        if (!p)
            return GetLastError() == ERROR_INVALID_PARAMETER
                ? ProcessLiveness::Dead
                : ProcessLiveness::Unknown;
        const DWORD wait = WaitForSingleObject(p, 0);
        CloseHandle(p);
        if (wait == WAIT_TIMEOUT) return ProcessLiveness::Alive;
        if (wait == WAIT_OBJECT_0) return ProcessLiveness::Dead;
        return ProcessLiveness::Unknown;
    }
'''
replace_once(p, old_main_liveness, new_main_liveness)
replace_once(
    p,
    "                if (observed != 0 && IsProcessAlive(static_cast<DWORD>(observed)))\n                    throw std::runtime_error(\"another outrun-vr-host already owns the bridge\");\n",
    "                if (observed != 0 &&\n"
    "                    QueryProcessLiveness(static_cast<DWORD>(observed)) != ProcessLiveness::Dead)\n"
    "                    throw std::runtime_error(\"another or unverified outrun-vr-host already owns the bridge\");\n",
)

# ---------------------------------------------------------------------------
# 4) D3D9Ex SafeEye cache is keyed by transport generation + frame id.
# ---------------------------------------------------------------------------
p = "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp"
replace_once(
    p,
    "    inline std::uint32_t SafeFrameId = 0;\n",
    "    inline std::uint32_t SafeFrameId = 0;\n"
    "    inline std::uint32_t SafeTransportGeneration = 0;\n",
)
replace_once(
    p,
    "        SafeFrameId = 0;\n",
    "        SafeFrameId = 0;\n"
    "        SafeTransportGeneration = 0;\n",
)
replace_once(
    p,
    "        SafeFrameId = frame.frameId;\n        ++SafeCopySuccess;\n",
    "        SafeFrameId = frame.frameId;\n"
    "        SafeTransportGeneration =\n"
    "            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];\n"
    "        ++SafeCopySuccess;\n",
)
old_ensure = '''    inline bool EnsureSafeFrame(std::uint32_t frameId) noexcept
    {
        if (frameId && SafeFrameId == frameId && SafeEyeSrv[0] && SafeEyeSrv[1])
            return true;
        OutRunVR::SharedRenderFrameState frame{};
        return ReadFrameById(frameId, frame) &&
            CopySharedFrameToSafeEyes(frame);
    }
'''
new_ensure = '''    inline bool EnsureSafeFrame(std::uint32_t frameId) noexcept
    {
        OutRunVR::SharedRenderFrameState frame{};
        if (!ReadFrameById(frameId, frame))
            return false;
        const std::uint32_t generation =
            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
        if (frameId && generation && SafeFrameId == frameId &&
            SafeTransportGeneration == generation &&
            SafeEyeSrv[0] && SafeEyeSrv[1])
            return true;
        return CopySharedFrameToSafeEyes(frame);
    }
'''
replace_once(p, old_ensure, new_ensure)

# ---------------------------------------------------------------------------
# 5) OpenXR swapchain call-order state, following the explicit acquired-image
#    lifecycle used by mature emulator VR backends. A failed wait keeps the
#    same acquired image pending; the next frame waits that image again instead
#    of illegally acquiring another one.
# ---------------------------------------------------------------------------
p = "vrhost/src/runtime/sbs_capture_override.hpp"
replace_once(
    p,
    "        std::vector<std::array<ID3D11RenderTargetView*, 2>> rtvs;\n\n        void Destroy()\n",
    "        std::vector<std::array<ID3D11RenderTargetView*, 2>> rtvs;\n"
    "        bool acquired = false;\n"
    "        bool waited = false;\n"
    "        std::uint32_t acquiredImage = 0;\n\n"
    "        void Destroy()\n",
)
replace_once(
    p,
    "            width = height = 0;\n            arraySize = 1;\n            format = DXGI_FORMAT_UNKNOWN;\n",
    "            width = height = 0;\n"
    "            arraySize = 1;\n"
    "            format = DXGI_FORMAT_UNKNOWN;\n"
    "            acquired = false;\n"
    "            waited = false;\n"
    "            acquiredImage = 0;\n",
)
old_acquire = '''    inline bool Acquire(XrSwapchain swapchain, std::uint32_t& image)
    {
        XrSwapchainImageAcquireInfo acquire{ XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO };
        if (XR_FAILED(::xrAcquireSwapchainImage(swapchain, &acquire, &image)))
            return false;
        XrSwapchainImageWaitInfo wait{ XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO };
        wait.timeout = XR_INFINITE_DURATION;
        for (;;)
        {
            const XrResult result = ::xrWaitSwapchainImage(swapchain, &wait);
            if (result == XR_TIMEOUT_EXPIRED)
                continue; // The same acquired image must be waited again; it cannot be released yet.
            return XR_SUCCEEDED(result);
        }
    }

    inline void Release(XrSwapchain swapchain)
    {
        XrSwapchainImageReleaseInfo release{ XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO };
        ::xrReleaseSwapchainImage(swapchain, &release);
    }
'''
new_acquire = '''    inline bool Acquire(Swapchain& swapchain, std::uint32_t& image)
    {
        if (!swapchain.acquired)
        {
            XrSwapchainImageAcquireInfo acquire{ XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO };
            if (XR_FAILED(::xrAcquireSwapchainImage(
                    swapchain.handle, &acquire, &swapchain.acquiredImage)))
                return false;
            swapchain.acquired = true;
            swapchain.waited = false;
        }
        image = swapchain.acquiredImage;
        if (swapchain.waited)
            return true;

        XrSwapchainImageWaitInfo wait{ XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO };
        wait.timeout = XR_INFINITE_DURATION;
        for (;;)
        {
            const XrResult result = ::xrWaitSwapchainImage(swapchain.handle, &wait);
            if (result == XR_TIMEOUT_EXPIRED)
                continue; // The same acquired image must be waited again; it cannot be released yet.
            if (XR_FAILED(result))
            {
                // Preserve acquiredImage. A later attempt must wait this oldest
                // acquired image again instead of violating acquire/wait order.
                return false;
            }
            swapchain.waited = true;
            return true;
        }
    }

    inline bool Release(Swapchain& swapchain)
    {
        if (!swapchain.acquired || !swapchain.waited)
            return false;
        XrSwapchainImageReleaseInfo release{ XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO };
        const XrResult result = ::xrReleaseSwapchainImage(swapchain.handle, &release);
        if (XR_SUCCEEDED(result))
        {
            swapchain.acquired = false;
            swapchain.waited = false;
            swapchain.acquiredImage = 0;
            return true;
        }
        return false;
    }
'''
replace_once(p, old_acquire, new_acquire)
for old, new in [
    ("Acquire(Projection.handle, image)", "Acquire(Projection, image)"),
    ("Release(Projection.handle);", "Release(Projection);"),
    ("Acquire(Theater.handle, image)", "Acquire(Theater, image)"),
    ("Release(Theater.handle);", "Release(Theater);"),
]:
    text = Path(p).read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"{p}: callsite marker missing: {old}")
    Path(p).write_text(text.replace(old, new), encoding="utf-8")

# Direct passthrough shares the same Swapchain/Acquire/Release helpers.
p = "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp"
replace_once(p, "Acquire(Projection.handle, image)", "Acquire(Projection, image)")
text = Path(p).read_text(encoding="utf-8")
if "Release(Projection.handle);" not in text:
    raise RuntimeError(f"{p}: Release projection callsite missing")
Path(p).write_text(text.replace("Release(Projection.handle);", "Release(Projection);"), encoding="utf-8")

# ---------------------------------------------------------------------------
# Contract markers - fail the one-shot patch rather than silently committing a
# partial hardening pass.
# ---------------------------------------------------------------------------
checks = {
    "src/vr/d3d9/stereo_renderer_r7.inc": [
        "OcclusionQueryTrackingUnavailable",
        "promoted D3D9Ex device lost ResetEx fallback ownership",
        "No fixed startup delay",
    ],
    "src/vr/d3d9/stereo_renderer_r13.cpp": [
        "R13InstallState",
        "transactional R13 install state=READY",
    ],
    "src/vr/game/outrun_renderer.cpp": [
        "RendererInstallState",
        "RendererInjectionAllowed",
        "atomic renderer install state=READY",
    ],
    "src/vr/game/outrun_renderer_r13.cpp": [
        "atomic renderer install handoff",
        "WVP injection disabled atomically to fail closed",
    ],
    "vrhost/src/ipc/host_state_v3_writer.hpp": [
        "ProcessLiveness::Unknown",
        "another or unverified outrun-vr-host owns HostState.v3",
    ],
    "vrhost/src/main.cpp": [
        "ProcessLiveness::Unknown",
        "another or unverified outrun-vr-host already owns the bridge",
    ],
    "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp": [
        "SafeTransportGeneration",
        "SafeTransportGeneration == generation",
        "Acquire(Projection, image)",
    ],
    "vrhost/src/runtime/sbs_capture_override.hpp": [
        "bool acquired = false",
        "Preserve acquiredImage",
        "Acquire(Projection, image)",
        "Acquire(Theater, image)",
    ],
}
for path, markers in checks.items():
    for marker in markers:
        require(path, marker)

print("VR review round-2 hardening patch applied successfully")
