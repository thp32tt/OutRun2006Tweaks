// R26 tracked-occlusion correction overlay.
//
// R23 remains the recovery/baseline authority. This final game-side wrapper
// restores the renderer policy that tracked D3D9 occlusion-query draws execute
// exactly once against the real game target without poisoning the whole Present.
// MRT hazards and unavailable query tracking still flow through the existing
// R13/R23 fail-closed chain unchanged.

#include "stereo_renderer_r23.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        SafetyHookInline R26DrawPrimitiveR23Hook{};
        SafetyHookInline R26DrawIndexedPrimitiveR23Hook{};
        SafetyHookInline R26DrawPrimitiveUPR23Hook{};
        SafetyHookInline R26DrawIndexedPrimitiveUPR23Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R26InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint64_t R26TrackedOcclusionSingleExec = 0;
        bool R26FirstTrackedOcclusionLogged = false;

        bool R26TrackedOcclusionNeedsSingleExecution(
            IDirect3DDevice9* device) noexcept
        {
            if (!IsGameDevice(device) || InternalStereoPass ||
                !TargetIsBackBuffer())
                return false;

            // Never bypass the existing fail-closed paths. MRT remains a frame
            // hazard, failed query tracking remains a frame hazard, and a prior
            // unsafe transition keeps ownership of the mono-shadow remainder.
            if (AnyAuxRenderTargetActive() || R13ForceMonoShadow ||
                OcclusionQueryTrackingUnavailable.load(std::memory_order_acquire))
                return false;

            if (!StereoWanted() || !R9StereoSeeded)
                return false;

            return ActiveOcclusionQueries.load(std::memory_order_acquire) > 0;
        }

        template <typename ActualDraw, typename NormalR23Draw>
        HRESULT R26GuardTrackedOcclusion(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, NormalR23Draw&& normalR23Draw,
            const char* site)
        {
            if (!R26TrackedOcclusionNeedsSingleExecution(device))
                return normalR23Draw();

            // R23 normally owns this top-level boundary. Because this one draw
            // intentionally bypasses the R23->R22->R13->R9 replay chain, keep
            // its draw serial/live-state accounting explicitly in sync.
            R23BeforeTopLevelDraw(device);

            ++R26TrackedOcclusionSingleExec;
            ++OcclusionStereoRejects;
            if (!R26FirstTrackedOcclusionLogged)
            {
                R26FirstTrackedOcclusionLogged = true;
                spdlog::info(
                    "VR R26 occlusion: tracked active query draw executes once on the real game target; no R9 mono replay, no R13 frame poison, stereo Present remains eligible");
            }

            // Draw through the original D3D9 trampoline exactly once. This is
            // the same single-eye policy used by the base renderer for a known
            // active query, but it also avoids R9's independent mono-shadow
            // replay from perturbing the query result.
            const HRESULT hr = actualDraw();
            if (FAILED(hr))
                R9Poison(OutRunVR::StereoFailureLeftDrawFailed, site, hr);
            return hr;
        }

        HRESULT __stdcall DrawPrimitiveDestR26(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawPrimitiveHook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            auto normal = [&]() {
                return R26DrawPrimitiveR23Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R26/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR26(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, INT baseVertexIndex, UINT minVertexIndex,
            UINT numVertices, UINT startIndex, UINT primitiveCount)
        {
            auto actual = [&]() {
                return DrawIndexedPrimitiveHook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto normal = [&]() {
                return R26DrawIndexedPrimitiveR23Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R26/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR26(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT primitiveCount, const void* data,
            UINT stride)
        {
            auto actual = [&]() {
                return DrawPrimitiveUPHook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            auto normal = [&]() {
                return R26DrawPrimitiveUPR23Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R26/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR26(
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
            auto normal = [&]() {
                return R26DrawIndexedPrimitiveUPR23Hook.stdcall<HRESULT>(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            return R26GuardTrackedOcclusion(
                device, actual, normal, "R26/DrawIndexedPrimitiveUP");
        }

        void R26RollbackHooks() noexcept
        {
            R26DrawIndexedPrimitiveUPR23Hook = {};
            R26DrawPrimitiveUPR23Hook = {};
            R26DrawIndexedPrimitiveR23Hook = {};
            R26DrawPrimitiveR23Hook = {};
        }

        bool R26EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R26DrawPrimitiveR23Hook,
                &R26DrawIndexedPrimitiveR23Hook,
                &R26DrawPrimitiveUPR23Hook,
                &R26DrawIndexedPrimitiveUPR23Hook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R26OcclusionInstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R26InstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const auto r23 = R23InstallState.load(std::memory_order_acquire);
                if (r23 == State::Failed)
                {
                    R26InstallState.store(State::Failed, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVROcclusionR26", false);
                    spdlog::error(
                        "VR R26 occlusion: R23 prerequisite failed; correction overlay not installed");
                    return 0;
                }

                if (r23 == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R26DrawPrimitiveR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveDestR23),
                        DrawPrimitiveDestR26, disabled);
                    R26DrawIndexedPrimitiveR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR23),
                        DrawIndexedPrimitiveDestR26, disabled);
                    R26DrawPrimitiveUPR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawPrimitiveUPDestR23),
                        DrawPrimitiveUPDestR26, disabled);
                    R26DrawIndexedPrimitiveUPR23Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR23),
                        DrawIndexedPrimitiveUPDestR26, disabled);

                    if (!R26EnableHooks())
                    {
                        R26RollbackHooks();
                        R26InstallState.store(State::Failed, std::memory_order_release);
                        HookManager::ReportAsyncResult("OpenXRVROcclusionR26", false);
                        spdlog::error(
                            "VR R26 occlusion: disabled-first draw transaction failed; R23 remains active");
                        return 0;
                    }

                    R26InstallState.store(State::Ready, std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVROcclusionR26", true);
                    spdlog::info(
                        "VR R26 GAME: tracked occlusion single-execution correction ACTIVE; MRT and query-tracking-unavailable paths remain fail-closed");
                    return 0;
                }
                Sleep(25);
            }

            R26InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVROcclusionR26", false);
            spdlog::error(
                "VR R26 occlusion: timed out waiting for R23; correction overlay not installed");
            return 0;
        }

        class VROcclusionR26Hook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVROcclusionR26";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R26InstallState.store(State::Pending, std::memory_order_release);
                HANDLE thread = CreateThread(nullptr, 0,
                    R26OcclusionInstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R26InstallState.store(State::Failed, std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VROcclusionR26Hook instance;
        };

        VROcclusionR26Hook VROcclusionR26Hook::instance;
    }
}
