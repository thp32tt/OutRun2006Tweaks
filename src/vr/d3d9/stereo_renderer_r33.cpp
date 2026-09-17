// R33 final dispatch accounting overlay.
//
// R32 owns all correctness/performance changes from the two 10-pass reviews.
// This final thin layer fixes one integration detail: if an R32 fast candidate
// fell through to the R31 function body, R31ObserveDraw would count the same
// top-level game draw a second time. Reuse the R32 fast paths, but dispatch a
// rejected candidate directly to the exact R30/R29 lower path R31 would have
// selected after its own fallback decision.

#include "stereo_renderer_r32.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R33DrawPrimitiveR32Hook{};
        SafetyHookInline R33DrawIndexedPrimitiveR32Hook{};
        SafetyHookInline R33DrawPrimitiveUPR32Hook{};
        SafetyHookInline R33DrawIndexedPrimitiveUPR32Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R33InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        template <typename ActualDraw, typename LowerR29Draw>
        HRESULT R33Dispatch(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, LowerR29Draw&& lowerR29Draw,
            const char* site) noexcept
        {
            R31ObserveDraw(device);

            if (R31StateBlockRecording)
            {
                ++R31Frame.fallback;
                return actualDraw();
            }

            if (R30CurrentPassIsScreenSpace2D())
            {
                const auto hud = R32TryHud(device,
                    std::forward<ActualDraw>(actualDraw), site);
                if (hud.handled)
                    return hud.hr;
            }
            else
            {
                const auto fast = R32TryFastWorld(device,
                    std::forward<ActualDraw>(actualDraw), site);
                if (fast.handled)
                    return fast.hr;
            }

            ++R31Frame.fallback;
            return R32LowerFailClosed(device,
                std::forward<LowerR29Draw>(lowerR29Draw));
        }

        HRESULT __stdcall DrawPrimitiveDestR33(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto lower = [&]() {
                return R30DrawPrimitiveR29Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R33Dispatch(device, actual, lower, "R33/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR33(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto lower = [&]() {
                return R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>(device,
                    type, baseVertexIndex, minVertexIndex, numVertices,
                    startIndex, primitiveCount);
            };
            return R33Dispatch(device, actual, lower,
                "R33/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR33(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data,
            UINT stride)
        {
            auto actual = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto lower = [&]() {
                return R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R33Dispatch(device, actual, lower, "R33/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR33(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveUPHook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            auto lower = [&]() {
                return R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>(device,
                    type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride);
            };
            return R33Dispatch(device, actual, lower,
                "R33/DrawIndexedPrimitiveUP");
        }

        void R33RollbackHooks() noexcept
        {
            R33DrawIndexedPrimitiveUPR32Hook = {};
            R33DrawPrimitiveUPR32Hook = {};
            R33DrawIndexedPrimitiveR32Hook = {};
            R33DrawPrimitiveR32Hook = {};
        }

        bool R33EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R33DrawPrimitiveR32Hook,
                &R33DrawIndexedPrimitiveR32Hook,
                &R33DrawPrimitiveUPR32Hook,
                &R33DrawIndexedPrimitiveUPR32Hook
            };
            for (auto* hook : hooks)
                if (!*hook || !hook->enable().has_value())
                    return false;
            return true;
        }

        DWORD WINAPI R33InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R33InstallState.store(State::Pending, std::memory_order_release);
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r32 = R32InstallState.load(std::memory_order_acquire);
                if (r32 == State::Failed)
                {
                    R33InstallState.store(State::Failed, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR33Dispatch", false);
                    return 0;
                }
                if (r32 == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R33DrawPrimitiveR32Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR32),
                        DrawPrimitiveDestR33, disabled);
                    R33DrawIndexedPrimitiveR32Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR32),
                        DrawIndexedPrimitiveDestR33, disabled);
                    R33DrawPrimitiveUPR32Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR32),
                        DrawPrimitiveUPDestR33, disabled);
                    R33DrawIndexedPrimitiveUPR32Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR32),
                        DrawIndexedPrimitiveUPDestR33, disabled);

                    if (!R33EnableHooks())
                    {
                        R33RollbackHooks();
                        R33InstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult(
                            "OpenXRVRStereoR33Dispatch", false);
                        spdlog::error(
                            "VR R33: dispatch hook transaction was partial; R32 remains authoritative");
                        return 0;
                    }

                    R33InstallState.store(State::Ready, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR33Dispatch", true);
                    spdlog::info(
                        "VR R33 DISPATCH: R32 fast paths + direct R29 fallback READY; top-level draw telemetry is counted exactly once");
                    return 0;
                }
                Sleep(25);
            }

            R33InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRStereoR33Dispatch", false);
            return 0;
        }

        class VRStereoR33DispatchHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR33Dispatch";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, R33InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R33InstallState.store(
                        OutRunVR::RuntimeEligibility::InstallState::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR33DispatchHook instance;
        };

        VRStereoR33DispatchHook VRStereoR33DispatchHook::instance;
    }
}
