from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, new: str, label: str) -> str:
    i = text.find(start)
    if i < 0:
        raise RuntimeError(f"{label}: start marker missing")
    j = text.find(end, i)
    if j < 0:
        raise RuntimeError(f"{label}: end marker missing")
    return text[:i] + new + text[j:]


# 1) R7: transactional hook install + atomic publication for dependent installers.
path = "src/vr/d3d9/stereo_renderer_r7.inc"
text = read(path)
r7_start = "\t\tbool InstallStereoHooks(IDirect3DDevice9*device)"
r7_end = "\n\t}\n\n\tbool IsInternalStereoPassActive"
r7_block = r'''\t\tconstexpr std::uint32_t StereoInstallPending = 0;
\t\tconstexpr std::uint32_t StereoInstallReady = 1;
\t\tconstexpr std::uint32_t StereoInstallFailed = 2;
\t\tstd::atomic<std::uint32_t> StereoInstallState{StereoInstallPending};
\t\tstd::atomic<IDirect3DDevice9*> StereoInstalledDevice{nullptr};

\t\tvoid RollbackStereoHooks() noexcept
\t\t{
\t\t\tQueryIssueHook = {};
\t\t\tCreateQueryHook = {};
\t\t\tSetVertexShaderHook = {};
\t\t\tDrawIndexedPrimitiveUPHook = {};
\t\t\tDrawPrimitiveUPHook = {};
\t\t\tDrawIndexedPrimitiveHook = {};
\t\t\tDrawPrimitiveHook = {};
\t\t\tClearHook = {};
\t\t\tSetDepthStencilSurfaceHook = {};
\t\t\tSetRenderTargetHook = {};
\t\t\tPresentHook = {};
\t\t\tResetHook = {};
\t\t\tStereoInstalledDevice.store(nullptr, std::memory_order_release);
\t\t}

\t\tbool InstallStereoHooks(IDirect3DDevice9*device)
\t\t{
\t\t\tif(!device)
\t\t\t{
\t\t\t\tStereoInstallState.store(StereoInstallFailed,std::memory_order_release);
\t\t\t\treturn false;
\t\t\t}
\t\t\tvoid**vtable=*reinterpret_cast<void***>(device);
\t\t\tif(!vtable)
\t\t\t{
\t\t\t\tStereoInstallState.store(StereoInstallFailed,std::memory_order_release);
\t\t\t\treturn false;
\t\t\t}
\t\t\tStereoInstallState.store(StereoInstallPending,std::memory_order_release);
\t\t\tResetHook=safetyhook::create_inline(vtable[ResetVtableIndex],ResetDest);
\t\t\tPresentHook=safetyhook::create_inline(vtable[PresentVtableIndex],PresentDest);
\t\t\tSetRenderTargetHook=safetyhook::create_inline(vtable[SetRenderTargetVtableIndex],SetRenderTargetDest);
\t\t\tSetDepthStencilSurfaceHook=safetyhook::create_inline(vtable[SetDepthStencilSurfaceVtableIndex],SetDepthStencilSurfaceDest);
\t\t\tClearHook=safetyhook::create_inline(vtable[ClearVtableIndex],ClearDest);
\t\t\tDrawPrimitiveHook=safetyhook::create_inline(vtable[DrawPrimitiveVtableIndex],DrawPrimitiveDest);
\t\t\tDrawIndexedPrimitiveHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveVtableIndex],DrawIndexedPrimitiveDest);
\t\t\tDrawPrimitiveUPHook=safetyhook::create_inline(vtable[DrawPrimitiveUPVtableIndex],DrawPrimitiveUPDest);
\t\t\tDrawIndexedPrimitiveUPHook=safetyhook::create_inline(vtable[DrawIndexedPrimitiveUPVtableIndex],DrawIndexedPrimitiveUPDest);
\t\t\tSetVertexShaderHook=safetyhook::create_inline(vtable[SetVertexShaderVtableIndex],SetVertexShaderDest);
\t\t\tCreateQueryHook=safetyhook::create_inline(vtable[CreateQueryVtableIndex],CreateQueryDest);
\t\t\tif(!ResetHook||!PresentHook||!SetRenderTargetHook||!SetDepthStencilSurfaceHook||!ClearHook||!DrawPrimitiveHook||!DrawIndexedPrimitiveHook||!DrawPrimitiveUPHook||!DrawIndexedPrimitiveUPHook||!SetVertexShaderHook||!CreateQueryHook)
\t\t\t{
\t\t\t\tRollbackStereoHooks();
\t\t\t\tStereoInstallState.store(StereoInstallFailed,std::memory_order_release);
\t\t\t\tspdlog::error("VR stereo: D3D9 hook transaction was partial; all base hooks rolled back immediately");
\t\t\t\treturn false;
\t\t\t}
\t\t\tIDirect3DVertexShader9*shader=nullptr;
\t\t\tif(SUCCEEDED(device->GetVertexShader(&shader))&&shader)
\t\t\t{
\t\t\t\tCurrentVertexShaderIdentity.store(reinterpret_cast<std::uintptr_t>(shader),std::memory_order_release);
\t\t\t\tVertexShaderSerial.store(1,std::memory_order_release);
\t\t\t\tshader->Release();
\t\t\t}
\t\t\tIDirect3DQuery9*queryProbe=nullptr;
\t\t\tif(SUCCEEDED(device->CreateQuery(D3DQUERYTYPE_OCCLUSION,&queryProbe))&&queryProbe)queryProbe->Release();
\t\t\tInitializeAuxRenderTargetState(device);
\t\t\tLastBeginSceneCountAtPresent=OutRunVRRenderer::GetBeginSceneCallCount();
\t\t\tEnsureSharedState();
\t\t\tEnsureRenderFrameState();
\t\t\tEnsureStereoResources(device);
\t\t\tStereoInstalledDevice.store(device,std::memory_order_release);
\t\t\tStereoInstallState.store(StereoInstallReady,std::memory_order_release);
\t\t\tspdlog::info("VR stereo: D3D9 full-eye renderer installed (Reset/Present/RT/Depth/Clear/Draw*/VS/CreateQuery); transactional install state=READY");
\t\t\treturn true;
\t\t}

\t\tDWORD WINAPI StereoInstallThread(void*)
\t\t{
\t\t\tSleep(250);
\t\t\tfor(int attempt=0;attempt<1200;++attempt)
\t\t\t{
\t\t\t\tif(Game::D3DDevice_ptr&&*Game::D3DDevice_ptr)
\t\t\t\t{
\t\t\t\t\tif(!InstallStereoHooks(*Game::D3DDevice_ptr))
\t\t\t\t\t\tspdlog::error("VR stereo: renderer hook installation failed closed");
\t\t\t\t\treturn 0;
\t\t\t\t}
\t\t\t\tSleep(100);
\t\t\t}
\t\t\tStereoInstallState.store(StereoInstallFailed,std::memory_order_release);
\t\t\tspdlog::warn("VR stereo: D3D9 device did not appear; stereo hooks not installed");
\t\t\treturn 0;
\t\t}
'''
text = replace_between(text, r7_start, r7_end, r7_block, "R7 transactional install")
text = replace_once(
    text,
    'if(!thread){spdlog::error("VR stereo: failed to create installer thread: {}",GetLastError());return false;}',
    'if(!thread){StereoInstallState.store(StereoInstallFailed,std::memory_order_release);spdlog::error("VR stereo: failed to create installer thread: {}",GetLastError());return false;}',
    "R7 thread-create failure state")
write(path, text)


# 2) R9: immediate rollback and acquire/release synchronization with R7 state.
path = "src/vr/d3d9/stereo_renderer.cpp"
text = read(path)
text = replace_once(
    text,
    "\t\tSafetyHookInline R9DrawIndexedPrimitiveUPCallbackHook{};\n",
    "\t\tSafetyHookInline R9DrawIndexedPrimitiveUPCallbackHook{};\n\n"
    "\t\tconstexpr std::uint32_t R9InstallPending = 0;\n"
    "\t\tconstexpr std::uint32_t R9InstallReady = 1;\n"
    "\t\tconstexpr std::uint32_t R9InstallFailed = 2;\n"
    "\t\tstd::atomic<std::uint32_t> R9InstallState{R9InstallPending};\n",
    "R9 install state declaration")
start = "\t\tbool R9InstallCallbackPolicy(IDirect3DDevice9* device)"
end = "\n\t\tclass VRFinalTestR9Hook"
r9_block = r'''\t\tvoid R9RollbackCallbackPolicy() noexcept
\t\t{
\t\t\tR9DrawIndexedPrimitiveUPCallbackHook = {};
\t\t\tR9DrawPrimitiveUPCallbackHook = {};
\t\t\tR9DrawIndexedPrimitiveCallbackHook = {};
\t\t\tR9DrawPrimitiveCallbackHook = {};
\t\t\tR9ClearCallbackHook = {};
\t\t\tR9SetDepthCallbackHook = {};
\t\t\tR9SetRenderTargetCallbackHook = {};
\t\t\tR9PresentCallbackHook = {};
\t\t\tR9ResetCallbackHook = {};
\t\t\tR9InstallState.store(R9InstallFailed, std::memory_order_release);
\t\t}

\t\tbool R9InstallCallbackPolicy(IDirect3DDevice9* device)
\t\t{
\t\t\tif (!device)
\t\t\t{
\t\t\t\tR9InstallState.store(R9InstallFailed, std::memory_order_release);
\t\t\t\treturn false;
\t\t\t}
\t\t\tR9InstallState.store(R9InstallPending, std::memory_order_release);
\t\t\tR9ResetCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&ResetDest), ResetDestR9);
\t\t\tR9PresentCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&PresentDest), PresentDestR9);
\t\t\tR9SetRenderTargetCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&SetRenderTargetDest), SetRenderTargetDestR9);
\t\t\tR9SetDepthCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&SetDepthStencilSurfaceDest), SetDepthStencilSurfaceDestR9);
\t\t\tR9ClearCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&ClearDest), ClearDestR9);
\t\t\tR9DrawPrimitiveCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&DrawPrimitiveDest), DrawPrimitiveDestR9);
\t\t\tR9DrawIndexedPrimitiveCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&DrawIndexedPrimitiveDest), DrawIndexedPrimitiveDestR9);
\t\t\tR9DrawPrimitiveUPCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&DrawPrimitiveUPDest), DrawPrimitiveUPDestR9);
\t\t\tR9DrawIndexedPrimitiveUPCallbackHook = safetyhook::create_inline(reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDest), DrawIndexedPrimitiveUPDestR9);
\t\t\tif (!R9ResetCallbackHook || !R9PresentCallbackHook || !R9SetRenderTargetCallbackHook ||
\t\t\t\t!R9SetDepthCallbackHook || !R9ClearCallbackHook || !R9DrawPrimitiveCallbackHook ||
\t\t\t\t!R9DrawIndexedPrimitiveCallbackHook || !R9DrawPrimitiveUPCallbackHook ||
\t\t\t\t!R9DrawIndexedPrimitiveUPCallbackHook)
\t\t\t{
\t\t\t\tR9RollbackCallbackPolicy();
\t\t\t\tspdlog::error("VR R9 FINAL TEST: callback policy transaction was partial; all R9 callback hooks rolled back immediately");
\t\t\t\treturn false;
\t\t\t}

\t\t\tif (TrackedDepthStencil)
\t\t\t\tR9CaptureMainDepth(TrackedDepthStencil, "policy-install");
\t\t\telse
\t\t\t\tR9MainDepthKnown = false;
\t\t\tR9InstallState.store(R9InstallReady, std::memory_order_release);
\t\t\tspdlog::info(
\t\t\t\t"VR R9 FINAL TEST: callback policy ACTIVE build={} depthHook=detour-callback monoFallback=shadow fullClearSeed=required nullDepth=mirrored transactional=READY",
\t\t\t\tR9BuildId);
\t\t\tR9LogSurface("initial RT", TrackedRenderTarget);
\t\t\tR9LogSurface("initial DS", TrackedDepthStencil);
\t\t\treturn true;
\t\t}

\t\tDWORD WINAPI R9InstallThread(void*)
\t\t{
\t\t\tfor (int attempt = 0; attempt < 4800; ++attempt)
\t\t\t{
\t\t\t\tconst std::uint32_t baseState = StereoInstallState.load(std::memory_order_acquire);
\t\t\t\tif (baseState == StereoInstallFailed)
\t\t\t\t{
\t\t\t\t\tR9InstallState.store(R9InstallFailed, std::memory_order_release);
\t\t\t\t\tspdlog::error("VR R9 FINAL TEST: R7 base hook transaction failed; callback policy not attempted");
\t\t\t\t\treturn 0;
\t\t\t\t}
\t\t\t\tif (baseState == StereoInstallReady)
\t\t\t\t{
\t\t\t\t\tIDirect3DDevice9* const device = StereoInstalledDevice.load(std::memory_order_acquire);
\t\t\t\t\tif (device && R9InstallCallbackPolicy(device))
\t\t\t\t\t\treturn 0;
\t\t\t\t\tif (R9InstallState.load(std::memory_order_acquire) != R9InstallFailed)
\t\t\t\t\t\tR9InstallState.store(R9InstallFailed, std::memory_order_release);
\t\t\t\t\tspdlog::error("VR R9 FINAL TEST: failed to install callback policy; fail-closed rollback complete");
\t\t\t\t\treturn 0;
\t\t\t\t}
\t\t\t\tSleep(25);
\t\t\t}
\t\t\tR9InstallState.store(R9InstallFailed, std::memory_order_release);
\t\t\tspdlog::warn("VR R9 FINAL TEST: R7 transactional install did not become ready; policy not installed");
\t\t\treturn 0;
\t\t}
'''
text = replace_between(text, start, end, r9_block, "R9 transaction/state-machine")
text = replace_once(
    text,
    'spdlog::error("VR R9 FINAL TEST: failed to create policy installer thread: {}", GetLastError());\n\t\t\t\t\treturn false;',
    'R9InstallState.store(R9InstallFailed, std::memory_order_release);\n\t\t\t\t\tspdlog::error("VR R9 FINAL TEST: failed to create policy installer thread: {}", GetLastError());\n\t\t\t\t\treturn false;',
    "R9 thread-create failure state")
write(path, text)


# 3) R13: consume only the atomic R9 install state, never poll SafetyHookInline objects cross-thread.
path = "src/vr/d3d9/stereo_renderer_r13.cpp"
text = read(path)
start = "        void R13RollbackPartialR9Policy() noexcept"
end = "\n        class VRStereoR13HardeningHook"
r13_block = r'''        DWORD WINAPI R13StereoInstallThread(void*)
        {
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const std::uint32_t r9State = R9InstallState.load(std::memory_order_acquire);
                if (r9State == R9InstallFailed)
                {
                    spdlog::error(
                        "VR R13: R9 callback transaction failed; hardening overlay not installed");
                    return 0;
                }
                if (r9State == R9InstallReady)
                {
                    R13ResetR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResetDestR9), ResetDestR13);
                    R13ResolveDirectHook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&ResolveDirectTransport),
                        ResolveDirectTransportR13);
                    R13PresentR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&PresentDestR9), PresentDestR13);
                    R13DrawPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR9),
                        DrawPrimitiveDestR13);
                    R13DrawIndexedPrimitiveR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR9),
                        DrawIndexedPrimitiveDestR13);
                    R13DrawPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR9),
                        DrawPrimitiveUPDestR13);
                    R13DrawIndexedPrimitiveUPR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR9),
                        DrawIndexedPrimitiveUPDestR13);

                    if (R13ResetR9Hook && R13ResolveDirectHook &&
                        R13PresentR9Hook && R13DrawPrimitiveR9Hook &&
                        R13DrawIndexedPrimitiveR9Hook && R13DrawPrimitiveUPR9Hook &&
                        R13DrawIndexedPrimitiveUPR9Hook)
                    {
                        spdlog::info(
                            "VR R13: stereo hardening ACTIVE; atomic R7/R9 install handoff + single ResetEx owner + GPU-completion direct-ring backpressure + single-execution MRT/occlusion fallback");
                    }
                    else
                    {
                        R13RollbackOverlayHooks();
                        spdlog::error(
                            "VR R13: overlay hook installation was partial; all R13 overlay hooks rolled back immediately");
                    }
                    return 0;
                }
                Sleep(25);
            }

            spdlog::warn(
                "VR R13: R9 transactional install did not become ready; hardening overlay not installed");
            return 0;
        }
'''
text = replace_between(text, start, end, r13_block, "R13 atomic handoff")
write(path, text)


# 4) OpenXR swapchain call order: retry timeout, and release after successful wait when index validation fails.
path = "vrhost/src/runtime/sbs_capture_override.hpp"
text = read(path)
start = "    inline bool Acquire(XrSwapchain swapchain, std::uint32_t& image)"
end = "\n    inline void Release(XrSwapchain swapchain)"
acquire_block = r'''    inline bool Acquire(XrSwapchain swapchain, std::uint32_t& image)
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
'''
text = replace_between(text, start, end, acquire_block, "OpenXR acquire/wait")
text = replace_once(
    text,
    "        if (!Acquire(Projection.handle, image) || image >= Projection.rtvs.size())\n            return false;",
    "        if (!Acquire(Projection.handle, image))\n            return false;\n        if (image >= Projection.rtvs.size())\n        {\n            Release(Projection.handle);\n            return false;\n        }",
    "projection invalid acquired index release")
text = replace_once(
    text,
    "        if (!Acquire(Theater.handle, image) || image >= Theater.rtvs.size())\n            return false;",
    "        if (!Acquire(Theater.handle, image))\n            return false;\n        if (image >= Theater.rtvs.size())\n        {\n            Release(Theater.handle);\n            return false;\n        }",
    "theater invalid acquired index release")
write(path, text)

path = "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp"
text = read(path)
text = replace_once(
    text,
    "        if (!Acquire(Projection.handle, image) || image >= Projection.rtvs.size())\n            return false;",
    "        if (!Acquire(Projection.handle, image))\n            return false;\n        if (image >= Projection.rtvs.size())\n        {\n            Release(Projection.handle);\n            return false;\n        }",
    "direct projection invalid acquired index release")
write(path, text)


# 5) IPC owner takeover: steal only when the old PID is positively known dead.
process_old = r'''        bool ProcessAlive(DWORD pid) noexcept
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
process_new = r'''        enum class ProcessLiveness : std::uint8_t
        {
            Dead,
            Alive,
            Unknown
        };

        ProcessLiveness QueryProcessLiveness(DWORD pid) noexcept
        {
            if (!pid)
                return ProcessLiveness::Dead;
            HANDLE process = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
            if (!process)
            {
                // ERROR_INVALID_PARAMETER is the normal signal for a PID that no
                // longer exists. Any permission/transient failure is fail-closed:
                // do not steal ownership from a process we cannot prove dead.
                return GetLastError() == ERROR_INVALID_PARAMETER
                    ? ProcessLiveness::Dead
                    : ProcessLiveness::Unknown;
            }
            const DWORD wait = WaitForSingleObject(process, 0);
            CloseHandle(process);
            if (wait == WAIT_TIMEOUT)
                return ProcessLiveness::Alive;
            if (wait == WAIT_OBJECT_0)
                return ProcessLiveness::Dead;
            return ProcessLiveness::Unknown;
        }
'''

path = "src/vr/ipc/v3_game_shadow_bridge.cpp"
text = read(path)
text = replace_once(text, process_old, process_new, "game IPC process liveness")
owner_old = "                    if (observed != 0 && ProcessAlive(static_cast<DWORD>(observed)))\n                        return false;"
owner_new = "                    if (observed != 0 &&\n                        QueryProcessLiveness(static_cast<DWORD>(observed)) != ProcessLiveness::Dead)\n                        return false;"
if text.count(owner_old) != 2:
    raise RuntimeError(f"game IPC owner guards: expected 2, found {text.count(owner_old)}")
text = text.replace(owner_old, owner_new)

# 6) Game-side v3 bridge lifetime: tracked thread, interruptible waits, process-lifetime module pin.
text = replace_once(text, "#include <algorithm>\n", "#include <algorithm>\n#include <atomic>\n", "game shadow atomic include")
insert_after = process_new
lifecycle = r'''
        std::atomic<bool> ShadowBridgeStop{false};
        HANDLE ShadowBridgeStopEvent = nullptr;
        HANDLE ShadowBridgeThreadHandle = nullptr;

        bool ShadowBridgeWait(DWORD timeoutMs) noexcept
        {
            if (ShadowBridgeStop.load(std::memory_order_acquire))
                return true;
            if (!ShadowBridgeStopEvent)
            {
                Sleep(timeoutMs);
                return ShadowBridgeStop.load(std::memory_order_acquire);
            }
            return WaitForSingleObject(ShadowBridgeStopEvent, timeoutMs) == WAIT_OBJECT_0;
        }
'''
text = replace_once(text, insert_after, insert_after + lifecycle, "game shadow lifetime state")
text = replace_once(text, "            for (;;)\n            {", "            while (!ShadowBridgeStop.load(std::memory_order_acquire))\n            {", "game shadow stop-aware loop")
text = replace_once(
    text,
    "                if (!legacyPoseMapping.EnsureOpen(SharedMemoryName))\n                {\n                    Sleep(100);\n                    continue;\n                }",
    "                if (!legacyPoseMapping.EnsureOpen(SharedMemoryName))\n                {\n                    if (ShadowBridgeWait(100))\n                        break;\n                    continue;\n                }",
    "game shadow missing-pose wait")
text = replace_once(
    text,
    "                if (!ShadowV2::StableReadPose(legacyPoseMapping.Get(), pose))\n                {\n                    Sleep(2);\n                    continue;\n                }",
    "                if (!ShadowV2::StableReadPose(legacyPoseMapping.Get(), pose))\n                {\n                    if (ShadowBridgeWait(2))\n                        break;\n                    continue;\n                }",
    "game shadow unstable-pose wait")
text = replace_once(
    text,
    "                Sleep(2);\n            }\n        }\n\n        class VRV3ShadowHook final : public Hook",
    "                if (ShadowBridgeWait(2))\n                    break;\n            }\n            return 0;\n        }\n\n        class VRV3ShadowHook final : public Hook",
    "game shadow loop exit")
apply_old = r'''            bool apply() override
            {
                HANDLE thread = CreateThread(nullptr, 0, ShadowBridgeThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    spdlog::error("VR v3 shadow: failed to create bridge thread: {}", GetLastError());
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
'''
apply_new = r'''            bool apply() override
            {
                if (ShadowBridgeThreadHandle)
                    return true;
                if (!ShadowBridgeStopEvent)
                    ShadowBridgeStopEvent = CreateEventW(nullptr, TRUE, FALSE, nullptr);
                if (!ShadowBridgeStopEvent)
                {
                    spdlog::error("VR v3 shadow: failed to create stop event: {}", GetLastError());
                    return false;
                }
                ShadowBridgeStop.store(false, std::memory_order_release);
                ResetEvent(ShadowBridgeStopEvent);

                // The bridge executes plugin code for the entire game process.
                // Pin the module so an unexpected FreeLibrary cannot unload code
                // underneath the worker; normal process shutdown still receives
                // DLL_PROCESS_DETACH and signals the stop event.
                HMODULE pinnedModule = nullptr;
                if (!GetModuleHandleExW(
                        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                        reinterpret_cast<LPCWSTR>(&ShadowBridgeStop), &pinnedModule))
                {
                    spdlog::error("VR v3 shadow: failed to pin plugin module: {}", GetLastError());
                    return false;
                }

                HANDLE thread = CreateThread(nullptr, 0, ShadowBridgeThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    spdlog::error("VR v3 shadow: failed to create bridge thread: {}", GetLastError());
                    return false;
                }
                ShadowBridgeThreadHandle = thread;
                spdlog::info("VR v3 shadow: process-lifetime worker tracked with stop event; plugin module pinned");
                return true;
            }
'''
text = replace_once(text, apply_old, apply_new, "game shadow tracked apply")
tail_old = r'''        VRV3ShadowHook VRV3ShadowHook::instance;
    }
}
'''
tail_new = r'''        VRV3ShadowHook VRV3ShadowHook::instance;
    }

    void RequestShadowBridgeStop() noexcept
    {
        ShadowBridgeStop.store(true, std::memory_order_release);
        if (ShadowBridgeStopEvent)
            SetEvent(ShadowBridgeStopEvent);
        if (ShadowBridgeThreadHandle)
        {
            CloseHandle(ShadowBridgeThreadHandle);
            ShadowBridgeThreadHandle = nullptr;
        }
    }
}
'''
text = replace_once(text, tail_old, tail_new, "game shadow stop API")
write(path, text)

path = "vrhost/src/ipc/v3_shadow_bridge.cpp"
text = read(path)
text = replace_once(text, process_old, process_new, "host IPC process liveness")
text = replace_once(text, owner_old, owner_new, "host IPC owner guard")
write(path, text)


# 7) DLL detach signals the tracked game-side bridge. Module pin prevents an unsafe dynamic unload race.
path = "src/dllmain.cpp"
text = read(path)
text = replace_once(
    text,
    "void InitExceptionHandler(); // hooks_exceptions.cpp\n",
    "void InitExceptionHandler(); // hooks_exceptions.cpp\nnamespace OutRunVR::IpcV3 { void RequestShadowBridgeStop() noexcept; }\n",
    "shadow stop forward declaration")
text = replace_once(
    text,
    "\telse if (ul_reason_for_call == DLL_PROCESS_DETACH)\n\t{\n\t\tproxy::on_detach();\n\t}",
    "\telse if (ul_reason_for_call == DLL_PROCESS_DETACH)\n\t{\n\t\tOutRunVR::IpcV3::RequestShadowBridgeStop();\n\t\tproxy::on_detach();\n\t}",
    "shadow stop on detach")
write(path, text)


# Basic postconditions. These markers are also useful for binary/CI verification later.
checks = {
    "src/vr/d3d9/stereo_renderer_r7.inc": [
        "transaction was partial; all base hooks rolled back immediately",
        "StereoInstallState.store(StereoInstallReady",
    ],
    "src/vr/d3d9/stereo_renderer.cpp": [
        "callback policy transaction was partial",
        "StereoInstallState.load(std::memory_order_acquire)",
        "R9InstallState.store(R9InstallReady",
    ],
    "src/vr/d3d9/stereo_renderer_r13.cpp": [
        "atomic R7/R9 install handoff",
        "R9InstallState.load(std::memory_order_acquire)",
    ],
    "vrhost/src/runtime/sbs_capture_override.hpp": [
        "The same acquired image must be waited again",
        "Release(Projection.handle);",
        "Release(Theater.handle);",
    ],
    "src/vr/ipc/v3_game_shadow_bridge.cpp": [
        "ProcessLiveness::Unknown",
        "process-lifetime worker tracked with stop event",
        "RequestShadowBridgeStop",
    ],
    "vrhost/src/ipc/v3_shadow_bridge.cpp": [
        "ProcessLiveness::Unknown",
    ],
}
for file, markers in checks.items():
    body = read(file)
    for marker in markers:
        if marker not in body:
            raise RuntimeError(f"postcondition missing {marker!r} in {file}")

print("remaining VR review hardening patches applied successfully")
