from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, data: str) -> None:
    (ROOT / path).write_text(data, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    data = read(path)
    count = data.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one replacement anchor, found {count}")
    write(path, data.replace(old, new, 1))


def insert_after(path: str, anchor: str, extra: str) -> None:
    data = read(path)
    count = data.count(anchor)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one insertion anchor, found {count}")
    write(path, data.replace(anchor, anchor + extra, 1))


# 1) Host DirectGPU lifetime: stage each accepted producer frame into a host-owned
# texture pair before projection rendering. Grace re-renders never sample a slot
# after its producer ACK has made that slot reusable.
insert_after(
    "vrhost/src/main_r23.cpp",
    "    ULONGLONG R23LastTheaterRefreshLogMs = 0;\n",
    r'''

    struct R23DirectHoldState
    {
        ID3D11Texture2D* eye[2]{};
        ID3D11ShaderResourceView* srv[2]{};
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        UINT width = 0;
        UINT height = 0;
        UINT mipLevels = 0;
        UINT arraySize = 0;
        std::uint32_t frameId = 0;
        std::uint32_t generation = 0;
        bool valid = false;

        ~R23DirectHoldState()
        {
            for (int eyeIndex = 0; eyeIndex < 2; ++eyeIndex)
            {
                if (srv[eyeIndex]) srv[eyeIndex]->Release();
                if (eye[eyeIndex]) eye[eyeIndex]->Release();
            }
        }
    };
    R23DirectHoldState R23DirectHold{};
    bool R23FirstDirectHoldLogged = false;

    void R23ReleaseDirectHoldResources() noexcept
    {
        for (int eye = 0; eye < 2; ++eye)
        {
            ReleaseCom(R23DirectHold.srv[eye]);
            ReleaseCom(R23DirectHold.eye[eye]);
        }
        R23DirectHold.format = DXGI_FORMAT_UNKNOWN;
        R23DirectHold.width = 0;
        R23DirectHold.height = 0;
        R23DirectHold.mipLevels = 0;
        R23DirectHold.arraySize = 0;
        R23DirectHold.frameId = 0;
        R23DirectHold.generation = 0;
        R23DirectHold.valid = false;
    }

    void R23InvalidateDirectHold() noexcept
    {
        R23DirectHold.frameId = 0;
        R23DirectHold.generation = 0;
        R23DirectHold.valid = false;
    }

    bool R23StageDirectHold(StereoCompositor& c,
        const OutRunVR::SharedRenderFrameState& frame)
    {
        const std::uint32_t slot =
            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];
        const std::uint32_t generation =
            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
        if (!c.context_ || !c.device_ || slot >= OutRunVR::RenderFrameRingSize ||
            !frame.frameId || !generation || !c.directLeft_[slot] ||
            !c.directRight_[slot])
            return false;

        D3D11_TEXTURE2D_DESC left{};
        D3D11_TEXTURE2D_DESC right{};
        c.directLeft_[slot]->GetDesc(&left);
        c.directRight_[slot]->GetDesc(&right);
        if (!left.Width || !left.Height || left.Width != right.Width ||
            left.Height != right.Height || left.MipLevels != right.MipLevels ||
            left.ArraySize != right.ArraySize || left.Format != right.Format ||
            left.SampleDesc.Count != 1 || right.SampleDesc.Count != 1 ||
            left.Width != frame.backbufferWidth ||
            left.Height != frame.backbufferHeight)
            return false;

        const bool recreate =
            !R23DirectHold.eye[0] || !R23DirectHold.eye[1] ||
            !R23DirectHold.srv[0] || !R23DirectHold.srv[1] ||
            R23DirectHold.width != left.Width ||
            R23DirectHold.height != left.Height ||
            R23DirectHold.mipLevels != left.MipLevels ||
            R23DirectHold.arraySize != left.ArraySize ||
            R23DirectHold.format != left.Format;
        if (recreate)
        {
            R23ReleaseDirectHoldResources();
            D3D11_TEXTURE2D_DESC hold = left;
            hold.Usage = D3D11_USAGE_DEFAULT;
            hold.BindFlags = D3D11_BIND_SHADER_RESOURCE;
            hold.CPUAccessFlags = 0;
            hold.MiscFlags = 0;
            for (int eye = 0; eye < 2; ++eye)
            {
                if (FAILED(c.device_->CreateTexture2D(
                        &hold, nullptr, &R23DirectHold.eye[eye])) ||
                    !R23DirectHold.eye[eye] ||
                    FAILED(c.device_->CreateShaderResourceView(
                        R23DirectHold.eye[eye], nullptr,
                        &R23DirectHold.srv[eye])) ||
                    !R23DirectHold.srv[eye])
                {
                    R23ReleaseDirectHoldResources();
                    return false;
                }
            }
            R23DirectHold.width = left.Width;
            R23DirectHold.height = left.Height;
            R23DirectHold.mipLevels = left.MipLevels;
            R23DirectHold.arraySize = left.ArraySize;
            R23DirectHold.format = left.Format;
        }

        // Immediate-context ordering guarantees that both copies execute before
        // the following projection draw samples this host-owned pair. The R32
        // EVENT fence then covers the copy + projection work before producer ACK.
        c.context_->CopyResource(R23DirectHold.eye[0], c.directLeft_[slot]);
        c.context_->CopyResource(R23DirectHold.eye[1], c.directRight_[slot]);
        R23DirectHold.frameId = frame.frameId;
        R23DirectHold.generation = generation;
        R23DirectHold.valid = true;
        if (!R23FirstDirectHoldLogged)
        {
            R23FirstDirectHoldLogged = true;
            std::cout
                << "DirectGPU host-owned hold active; grace projection no longer samples ACK-reusable producer slots.\n";
        }
        return true;
    }
''')

replace_once(
    "vrhost/src/main_r23.cpp",
    '''    void R23InvalidateDirect(StereoCompositor& c)\n    {\n        c.directFrameValid_ = false;\n        c.directTransportReady_ = false;\n    }\n''',
    '''    void R23InvalidateDirect(StereoCompositor& c)\n    {\n        c.directFrameValid_ = false;\n        c.directTransportReady_ = false;\n        R23InvalidateDirectHold();\n    }\n''')

replace_once(
    "vrhost/src/main_r23.cpp",
    '''    bool R23CommitDirectAfterValidation(StereoCompositor& c,\n        const OutRunVR::SharedRenderFrameState& frame)\n    {\n        if (!c.CommitDirectStereoSource(frame) || !R23ValidateDirectResourceSize(c, frame))\n        {\n            R23InvalidateDirect(c);\n            return false;\n        }\n        c.directTransportReady_ = true;\n        c.directFrameValid_ = true;\n        c.stereoSourceValid_ = false;\n        return true;\n    }\n''',
    '''    bool R23CommitDirectAfterValidation(StereoCompositor& c,\n        const OutRunVR::SharedRenderFrameState& frame)\n    {\n        if (!c.CommitDirectStereoSource(frame) ||\n            !R23ValidateDirectResourceSize(c, frame) ||\n            !R23StageDirectHold(c, frame))\n        {\n            R23InvalidateDirect(c);\n            return false;\n        }\n        c.directTransportReady_ = true;\n        c.directFrameValid_ = true;\n        c.stereoSourceValid_ = false;\n        return true;\n    }\n''')

replace_once(
    "vrhost/src/main_r23.cpp",
    '''        if (c.directFrameValid_ && c.directActiveSlot_ < OutRunVR::RenderFrameRingSize &&\n            c.directLeftSrv_[c.directActiveSlot_] && c.directRightSrv_[c.directActiveSlot_])\n        {\n            eyes[0] = eyes[1] = { 0.f, 0.f, 1.f, 1.f };\n            srv[0] = c.directLeftSrv_[c.directActiveSlot_];\n            srv[1] = c.directRightSrv_[c.directActiveSlot_];\n            fmt[0] = fmt[1] = c.directFormat_[c.directActiveSlot_];\n        }\n''',
    '''        if (c.directFrameValid_ && R23DirectHold.valid &&\n            R23DirectHold.srv[0] && R23DirectHold.srv[1])\n        {\n            eyes[0] = eyes[1] = { 0.f, 0.f, 1.f, 1.f };\n            srv[0] = R23DirectHold.srv[0];\n            srv[1] = R23DirectHold.srv[1];\n            fmt[0] = fmt[1] = R23DirectHold.format;\n        }\n''')

# 2) R32 host ACKs: once a producer frame has been ACKed, grace frames use the
# host-owned hold and must not re-arm/publish an older frame ID for that slot.
insert_after(
    "vrhost/src/runtime/r32_direct_submit.hpp",
    "    inline std::array<PendingAck, OutRunVR::RenderFrameRingSize> Pending{};\n",
    "    inline std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> AckedFrame{};\n"
    "    inline std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> AckedGeneration{};\n")

replace_once(
    "vrhost/src/runtime/r32_direct_submit.hpp",
    '''            pending.armed = false;\n            pending.flushIssued = false;\n            pending.frame = {};\n        }\n    }\n''',
    '''            pending.armed = false;\n            pending.flushIssued = false;\n            pending.frame = {};\n        }\n        AckedFrame.fill(0);\n        AckedGeneration.fill(0);\n    }\n''')

replace_once(
    "vrhost/src/runtime/r32_direct_submit.hpp",
    '''            if (!OutRunVrD3D9ExDirectPassthrough::PublishCompletedFrame(\n                    pending.frame))\n            {\n                ++AckPublishRetry;\n                continue;\n            }\n            pending.armed = false;\n            pending.flushIssued = false;\n            pending.frame = {};\n            ++AckCompleted;\n''',
    '''            if (!OutRunVrD3D9ExDirectPassthrough::PublishCompletedFrame(\n                    pending.frame))\n            {\n                ++AckPublishRetry;\n                continue;\n            }\n            const std::uint32_t slot =\n                pending.frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];\n            const std::uint32_t generation =\n                pending.frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];\n            if (slot < AckedFrame.size())\n            {\n                AckedFrame[slot] = pending.frame.frameId;\n                AckedGeneration[slot] = generation;\n            }\n            pending.armed = false;\n            pending.flushIssued = false;\n            pending.frame = {};\n            ++AckCompleted;\n''')

replace_once(
    "vrhost/src/runtime/r32_direct_submit.hpp",
    '''        const std::uint32_t slot =\n            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];\n        if (slot >= Pending.size() || !EnsureFence(slot))\n            return false;\n\n        auto& pending = Pending[slot];\n''',
    '''        const std::uint32_t slot =\n            frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];\n        const std::uint32_t generation =\n            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];\n        if (slot >= Pending.size() || !generation || !EnsureFence(slot))\n            return false;\n\n        if (AckedGeneration[slot] == generation &&\n            AckedFrame[slot] == frame.frameId)\n            return true;\n        if (AckedGeneration[slot] != 0 && AckedGeneration[slot] != generation)\n        {\n            AckedGeneration[slot] = 0;\n            AckedFrame[slot] = 0;\n        }\n\n        auto& pending = Pending[slot];\n''')

replace_once(
    "vrhost/src/runtime/r32_direct_submit.hpp",
    '''            if (pending.armed)\n            {\n                ++AckSlotBusy;\n                return false;\n            }\n        }\n\n        OutRunVrFinalTest::Context->End(pending.fence);\n''',
    '''            if (pending.armed)\n            {\n                ++AckSlotBusy;\n                return false;\n            }\n        }\n\n        if (AckedGeneration[slot] == generation &&\n            AckedFrame[slot] == frame.frameId)\n            return true;\n\n        OutRunVrFinalTest::Context->End(pending.fence);\n''')

# 3) R33 cache generations: a partial setter must not make a stale StateBlock
# snapshot current. Current caches stay current naturally because these
# generations are unchanged by SetRenderState itself.
replace_once(
    "src/vr/d3d9/stereo_renderer_r33.cpp",
    '''            bool tracked = true;\n            switch (state)\n            {\n            case D3DRS_ZENABLE:\n                R33DepthStencilState.zEnable = value;\n                break;\n            case D3DRS_ZWRITEENABLE:\n                R33DepthStencilState.zWrite = value;\n                break;\n            case D3DRS_STENCILENABLE:\n                R33DepthStencilState.stencilEnable = value;\n                break;\n            case D3DRS_STENCILWRITEMASK:\n                R33DepthStencilState.stencilWriteMask = value;\n                break;\n            case D3DRS_STENCILFAIL:\n                R33DepthStencilState.stencilFail = value;\n                break;\n            case D3DRS_STENCILZFAIL:\n                R33DepthStencilState.stencilZFail = value;\n                break;\n            case D3DRS_STENCILPASS:\n                R33DepthStencilState.stencilPass = value;\n                break;\n            case D3DRS_TWOSIDEDSTENCILMODE:\n                R33DepthStencilState.twoSided = value;\n                break;\n            case D3DRS_CCW_STENCILFAIL:\n                R33DepthStencilState.ccwStencilFail = value;\n                break;\n            case D3DRS_CCW_STENCILZFAIL:\n                R33DepthStencilState.ccwStencilZFail = value;\n                break;\n            case D3DRS_CCW_STENCILPASS:\n                R33DepthStencilState.ccwStencilPass = value;\n                break;\n            default:\n                tracked = false;\n                break;\n            }\n\n            if (tracked)\n            {\n                R33DepthStencilState.depthGeneration = R9MainDepthGeneration;\n                R33DepthStencilState.stateBlockRecordings =\n                    R31StateBlockRecordings;\n                R33DepthStencilState.stateBlockApplies = R31StateBlockApplies;\n            }\n            return hr;\n''',
    '''            switch (state)\n            {\n            case D3DRS_ZENABLE:\n                R33DepthStencilState.zEnable = value;\n                break;\n            case D3DRS_ZWRITEENABLE:\n                R33DepthStencilState.zWrite = value;\n                break;\n            case D3DRS_STENCILENABLE:\n                R33DepthStencilState.stencilEnable = value;\n                break;\n            case D3DRS_STENCILWRITEMASK:\n                R33DepthStencilState.stencilWriteMask = value;\n                break;\n            case D3DRS_STENCILFAIL:\n                R33DepthStencilState.stencilFail = value;\n                break;\n            case D3DRS_STENCILZFAIL:\n                R33DepthStencilState.stencilZFail = value;\n                break;\n            case D3DRS_STENCILPASS:\n                R33DepthStencilState.stencilPass = value;\n                break;\n            case D3DRS_TWOSIDEDSTENCILMODE:\n                R33DepthStencilState.twoSided = value;\n                break;\n            case D3DRS_CCW_STENCILFAIL:\n                R33DepthStencilState.ccwStencilFail = value;\n                break;\n            case D3DRS_CCW_STENCILZFAIL:\n                R33DepthStencilState.ccwStencilZFail = value;\n                break;\n            case D3DRS_CCW_STENCILPASS:\n                R33DepthStencilState.ccwStencilPass = value;\n                break;\n            default:\n                break;\n            }\n\n            // Do not rewrite depth/state-block generations here. If a StateBlock\n            // made this snapshot stale, changing one tracked render state cannot\n            // make the untouched fields authoritative again.\n            return hr;\n''')

replace_once(
    "src/vr/d3d9/stereo_renderer_r33.cpp",
    '''            if (telemetry)\n                ++R31Frame.fallback;\n            return R32LowerFailClosed(device,\n                std::forward<LowerR29Draw>(lowerR29Draw));\n''',
    '''            // Preserve R31's fail-closed boundary when StateBlock tracking\n            // is unreliable. Otherwise stale R29 effect/shadow caches can\n            // reclassify a draw that R33 already rejected using live state.\n            R31DiscardUnreliableDrawCaches();\n            if (telemetry)\n                ++R31Frame.fallback;\n            return R32LowerFailClosed(device,\n                std::forward<LowerR29Draw>(lowerR29Draw));\n''')

# 4) R14 mip safety: DISCARD is safe only for a one-level texture. On a mip chain
# use a normal lock so restoring one level cannot invalidate untouched levels.
replace_once(
    "src/vr/d3d9/ex_device_upgrade_r14.cpp",
    '''            hr = R14TextureLockR13Hook.stdcall<HRESULT>(\n                entry.gpu, level, &destination, nullptr, D3DLOCK_DISCARD);\n            if (FAILED(hr))\n            {\n                hr = R14TextureLockR13Hook.stdcall<HRESULT>(\n                    entry.gpu, level, &destination, nullptr, 0);\n            }\n''',
    '''            const bool singleLevelTexture = entry.gpu->GetLevelCount() <= 1;\n            const DWORD destinationFlags =\n                singleLevelTexture ? D3DLOCK_DISCARD : 0;\n            hr = R14TextureLockR13Hook.stdcall<HRESULT>(\n                entry.gpu, level, &destination, nullptr, destinationFlags);\n            if (FAILED(hr) && destinationFlags != 0)\n            {\n                hr = R14TextureLockR13Hook.stdcall<HRESULT>(\n                    entry.gpu, level, &destination, nullptr, 0);\n            }\n''')

# 5) D3D9 producer wait budget: QPC covers the initial FLUSH GetData call too.
replace_once(
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    '''        bool R32WaitProducerFence(IDirect3DQuery9* query) noexcept\n        {\n            if (!query)\n                return false;\n            HRESULT ready = query->GetData(nullptr, 0, D3DGETDATA_FLUSH);\n            if (ready == S_OK)\n            {\n                ++R32DirectFenceSuccess;\n                return true;\n            }\n            if (ready != S_FALSE)\n                return false;\n\n            const ULONGLONG deadline = GetTickCount64() +\n                OutRunVR::R32::ProducerFenceBudgetMs;\n            for (;;)\n            {\n                ready = query->GetData(nullptr, 0, 0);\n                if (ready == S_OK)\n                {\n                    ++R32DirectFenceSuccess;\n                    return true;\n                }\n                if (ready != S_FALSE || GetTickCount64() >= deadline)\n                {\n                    ++R32DirectFenceBudgetFallbacks;\n                    ++DirectTransportFenceTimeouts;\n                    if (!R32FirstFenceBudgetLogged)\n                    {\n                        R32FirstFenceBudgetLogged = true;\n                        spdlog::warn(\n                            "VR R32 D3D9Ex: producer copy fence exceeded {}ms; falling back to SBS instead of stalling up to 12ms",\n                            OutRunVR::R32::ProducerFenceBudgetMs);\n                    }\n                    return false;\n                }\n                SwitchToThread();\n            }\n        }\n''',
    '''        bool R32WaitProducerFence(IDirect3DQuery9* query) noexcept\n        {\n            if (!query)\n                return false;\n\n            LARGE_INTEGER frequency{};\n            LARGE_INTEGER start{};\n            const bool highResolutionClock =\n                QueryPerformanceFrequency(&frequency) != FALSE &&\n                frequency.QuadPart > 0 &&\n                QueryPerformanceCounter(&start) != FALSE;\n            const ULONGLONG fallbackDeadline = highResolutionClock ? 0 :\n                GetTickCount64() + OutRunVR::R32::ProducerFenceBudgetMs;\n            const LONGLONG budgetTicks = highResolutionClock\n                ? (frequency.QuadPart *\n                    static_cast<LONGLONG>(OutRunVR::R32::ProducerFenceBudgetMs) +\n                    999) / 1000\n                : 0;\n\n            // Budget starts before the FLUSH request so a slow first GetData is\n            // accounted for instead of being hidden outside the 2 ms window.\n            HRESULT ready = query->GetData(nullptr, 0, D3DGETDATA_FLUSH);\n            if (ready == S_OK)\n            {\n                ++R32DirectFenceSuccess;\n                return true;\n            }\n            if (ready != S_FALSE)\n                return false;\n\n            for (;;)\n            {\n                ready = query->GetData(nullptr, 0, 0);\n                if (ready == S_OK)\n                {\n                    ++R32DirectFenceSuccess;\n                    return true;\n                }\n\n                bool expired = ready != S_FALSE;\n                if (!expired && highResolutionClock)\n                {\n                    LARGE_INTEGER now{};\n                    expired = QueryPerformanceCounter(&now) == FALSE ||\n                        now.QuadPart - start.QuadPart >= budgetTicks;\n                }\n                else if (!expired)\n                {\n                    expired = GetTickCount64() >= fallbackDeadline;\n                }\n\n                if (expired)\n                {\n                    ++R32DirectFenceBudgetFallbacks;\n                    ++DirectTransportFenceTimeouts;\n                    if (!R32FirstFenceBudgetLogged)\n                    {\n                        R32FirstFenceBudgetLogged = true;\n                        spdlog::warn(\n                            "VR R32 D3D9Ex: producer copy fence exceeded {}ms; falling back to SBS instead of stalling up to 12ms",\n                            OutRunVR::R32::ProducerFenceBudgetMs);\n                    }\n                    return false;\n                }\n                SwitchToThread();\n            }\n        }\n''')

replace_once(
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    '''            ++R32BatchWvpUploads;\n            const HRESULT hr = device->SetVertexShaderConstantF(\n''',
    '''            if (Settings::VRTelemetry)\n                ++R32BatchWvpUploads;\n            const HRESULT hr = device->SetVertexShaderConstantF(\n''')
replace_once(
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    '''            if (!R32FirstBatchWvpLogged)\n            {\n                R32FirstBatchWvpLogged = true;\n''',
    '''            if (Settings::VRTelemetry && !R32FirstBatchWvpLogged)\n            {\n                R32FirstBatchWvpLogged = true;\n''')

# 6) Sync the generated CMake ownership block with cmake.toml so builds that skip
# cmkr generation do not compile the obsolete R13 source graph.
replace_once(
    "CMakeLists.txt",
    '''# R13 keeps the validated R9/R12 implementation files intact and compiles\n# wrapper translation units that include them plus narrowly scoped hardening.\nset_source_files_properties(\n    src/vr/d3d9/ex_device_upgrade.cpp\n    src/vr/d3d9/stereo_renderer.cpp\n    src/vr/game/outrun_renderer.cpp\n    PROPERTIES HEADER_FILE_ONLY TRUE)\n''',
    '''# R33/R14 keep the validated R32/R31/R30/R29/R26/R23/R22/R21/R20/R13/R9/R12\n# implementation chains intact and compile only the final game/stereo/Ex wrapper\n# TUs. Included implementation files are header-only here so no hook body is\n# linked twice.\nset(OUTRUN_VR_INCLUDED_IMPL_TUS\n    src/vr/d3d9/ex_device_upgrade.cpp\n    src/vr/d3d9/ex_device_upgrade_r13.cpp\n    src/vr/d3d9/stereo_renderer.cpp\n    src/vr/d3d9/stereo_renderer_r13.cpp\n    src/vr/d3d9/stereo_renderer_r20.cpp\n    src/vr/d3d9/stereo_renderer_r21.cpp\n    src/vr/d3d9/stereo_renderer_r22.cpp\n    src/vr/d3d9/stereo_renderer_r23.cpp\n    src/vr/d3d9/stereo_renderer_r26.cpp\n    src/vr/d3d9/stereo_renderer_r29.cpp\n    src/vr/d3d9/stereo_renderer_r30.cpp\n    src/vr/d3d9/stereo_renderer_r31.cpp\n    src/vr/d3d9/stereo_renderer_r32.cpp\n    src/vr/game/outrun_renderer.cpp\n    src/vr/game/outrun_renderer_r13.cpp\n    src/vr/game/outrun_renderer_r23.cpp)\nset_source_files_properties(${OUTRUN_VR_INCLUDED_IMPL_TUS}\n    PROPERTIES HEADER_FILE_ONLY TRUE)\n\nset(OUTRUN_VR_FINAL_TUS\n    src/vr/d3d9/ex_device_upgrade_r14.cpp\n    src/vr/d3d9/stereo_renderer_r33.cpp\n    src/vr/game/outrun_renderer_r29.cpp)\nforeach(_vr_source IN LISTS OUTRUN_VR_INCLUDED_IMPL_TUS OUTRUN_VR_FINAL_TUS)\n    if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${_vr_source}")\n        message(FATAL_ERROR "VR source graph references missing TU: ${_vr_source}")\n    endif()\nendforeach()\nforeach(_vr_source IN LISTS OUTRUN_VR_INCLUDED_IMPL_TUS)\n    get_source_file_property(_vr_header_only "${_vr_source}" HEADER_FILE_ONLY)\n    if(NOT _vr_header_only)\n        message(FATAL_ERROR "VR included implementation TU must be HEADER_FILE_ONLY: ${_vr_source}")\n    endif()\nendforeach()\nforeach(_vr_source IN LISTS OUTRUN_VR_FINAL_TUS)\n    get_source_file_property(_vr_header_only "${_vr_source}" HEADER_FILE_ONLY)\n    if(_vr_header_only)\n        message(FATAL_ERROR "VR final wrapper TU must compile normally: ${_vr_source}")\n    endif()\nendforeach()\nunset(_vr_source)\nunset(_vr_header_only)\n''')

# 7) Update the review verifier for list-based ownership and add regression
# markers for each correctness fix.
replace_once(
    "tools/verify_vr_r32_review.py",
    '''    "R32WaitProducerFence",\n    "R32ProducerFencePending",\n''',
    '''    "R32WaitProducerFence",\n    "QueryPerformanceCounter",\n    "Budget starts before the FLUSH request",\n    "R32ProducerFencePending",\n''')
replace_once(
    "tools/verify_vr_r32_review.py",
    '''    "R32LowerFailClosed",\n    "R30DrawPrimitiveR29Hook",\n''',
    '''    "R32LowerFailClosed",\n    "R31DiscardUnreliableDrawCaches();",\n    "changing one tracked render state cannot",\n    "R30DrawPrimitiveR29Hook",\n''')
replace_once(
    "tools/verify_vr_r32_review.py",
    '''    "PublishCompletedFrame",\n    "R32 direct PERF 5s",\n''',
    '''    "PublishCompletedFrame",\n    "AckedFrame",\n    "AckedGeneration",\n    "R32 direct PERF 5s",\n''')
insert_after(
    "tools/verify_vr_r32_review.py",
    '''if "Context->End(pending.fence);\\n        OutRunVrFinalTest::Context->Flush();" in host_direct:\n    raise SystemExit("R32 host must not Flush every direct frame")\n''',
    '''\nrequire(\n    "vrhost/src/main_r23.cpp",\n    "R23DirectHoldState",\n    "R23StageDirectHold",\n    "grace projection no longer samples ACK-reusable producer slots",\n    "srv[0] = R23DirectHold.srv[0]",\n)\n\nrequire(\n    "src/vr/d3d9/ex_device_upgrade_r14.cpp",\n    "singleLevelTexture",\n    "entry.gpu->GetLevelCount() <= 1",\n)\n''')

replace_once(
    "tools/verify_vr_r32_review.py",
    '''vr_start = cmake.find(\n    "set_source_files_properties(\\n    src/vr/d3d9/ex_device_upgrade.cpp")\nvr_end = cmake.find("PROPERTIES HEADER_FILE_ONLY TRUE", vr_start)\nif vr_start < 0 or vr_end < 0:\n    raise SystemExit("could not locate VR HEADER_FILE_ONLY ownership block")\nheader_section = cmake[vr_start:vr_end]\nif "stereo_renderer_r31.cpp" not in header_section or \\\n        "stereo_renderer_r32.cpp" not in header_section:\n    raise SystemExit("R31/R32 must be include-only implementation TUs")\nif "stereo_renderer_r33.cpp" in header_section:\n    raise SystemExit("R33 final TU must remain independently compiled")\n''',
    '''included_start = cmake.find("set(OUTRUN_VR_INCLUDED_IMPL_TUS")\nincluded_end = cmake.find(\n    "set_source_files_properties(${OUTRUN_VR_INCLUDED_IMPL_TUS}",\n    included_start)\nfinal_start = cmake.find("set(OUTRUN_VR_FINAL_TUS", included_end)\nfinal_end = cmake.find("foreach(_vr_source", final_start)\nif min(included_start, included_end, final_start, final_end) < 0:\n    raise SystemExit("could not locate list-based VR source ownership blocks")\nheader_section = cmake[included_start:included_end]\nfinal_section = cmake[final_start:final_end]\nif "stereo_renderer_r31.cpp" not in header_section or \\\n        "stereo_renderer_r32.cpp" not in header_section:\n    raise SystemExit("R31/R32 must be include-only implementation TUs")\nif "stereo_renderer_r33.cpp" in header_section:\n    raise SystemExit("R33 final TU must not be include-only")\nif "stereo_renderer_r33.cpp" not in final_section or \\\n        "ex_device_upgrade_r14.cpp" not in final_section or \\\n        "outrun_renderer_r29.cpp" not in final_section:\n    raise SystemExit("final VR wrapper TU list is incomplete")\n\ngenerated = require(\n    "CMakeLists.txt",\n    "set(OUTRUN_VR_INCLUDED_IMPL_TUS",\n    "set(OUTRUN_VR_FINAL_TUS",\n    "stereo_renderer_r33.cpp",\n    "ex_device_upgrade_r14.cpp",\n    "outrun_renderer_r29.cpp",\n)\nfor source in (\n    "src/vr/d3d9/stereo_renderer_r31.cpp",\n    "src/vr/d3d9/stereo_renderer_r32.cpp",\n    "src/vr/d3d9/stereo_renderer_r33.cpp",\n    "src/vr/d3d9/ex_device_upgrade_r14.cpp",\n    "src/vr/game/outrun_renderer_r29.cpp",\n):\n    if source not in generated:\n        raise SystemExit(f"generated CMakeLists is stale: missing {source}")\n''')

print("Applied VR review correctness/performance fixes")
