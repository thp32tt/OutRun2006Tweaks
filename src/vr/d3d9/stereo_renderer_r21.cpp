// R21 game-side host-death fail-closed overlay.
//
// R20/R13/R9 remain the renderer implementation. R21 adds a Present-boundary
// liveness check so a dead/stalled x64 OpenXR host cannot leave the game
// indefinitely attempting stereo with stale HostAlive state.
//
// Review hardening: SharedPoseState host fields are host-owned. The game no
// longer clears HostAlive/HostShouldRender in that shared seqlock domain. A
// stale/unreadable host instead closes the game-local R20 stereo eligibility
// gate. On the first stale Present, an already-complete mono shadow may still be
// restored; subsequent frames remain ordinary mono until a stable fresh host
// sample reopens the local gate.

#include "stereo_renderer_r20.cpp"

namespace OutRunVRStereo
{
    namespace
    {
        // Keep the frame-boundary eligibility decision aligned with the pose
        // reader's 250 ms freshness budget. R22 makes this local gate
        // authoritative for clear/draw callbacks for the entire following
        // Present interval.
        constexpr std::int64_t R21HostStaleMs = 250;

        SafetyHookInline R21PresentR9Hook{};
        std::atomic<bool> R21PresentGuardReady{false};
        bool R21HostFailClosed = false;
        std::uint32_t R21LastHealthyHostPid = 0;

        bool R21ComputeAgeMs(std::int64_t sampleQpc,
            std::int64_t& ageMs) noexcept
        {
            ageMs = INT64_MAX;
            if (sampleQpc <= 0)
                return false;
            LARGE_INTEGER now{};
            LARGE_INTEGER frequency{};
            if (!QueryPerformanceCounter(&now) ||
                !QueryPerformanceFrequency(&frequency) ||
                frequency.QuadPart <= 0 || now.QuadPart < sampleQpc)
                return false;
            const std::int64_t delta = now.QuadPart - sampleQpc;
            ageMs = (delta * 1000) / frequency.QuadPart;
            return true;
        }

        bool R21ReadHostFreshness(std::uint32_t& hostPid,
            std::uint32_t& flags, std::uint32_t& heartbeat,
            std::int64_t& sampleQpc, std::int64_t& ageMs) noexcept
        {
            hostPid = flags = heartbeat = 0;
            sampleQpc = 0;
            ageMs = INT64_MAX;

            if (!SharedState || SharedState->magic != OutRunVR::SharedMagic ||
                SharedState->protocolVersion != OutRunVR::SharedProtocolVersion ||
                SharedState->structSize != sizeof(OutRunVR::SharedPoseState))
                return false;

            hostPid = SharedState->hostPid;
            flags = SharedState->flags;
            heartbeat = SharedState->heartbeat;
            sampleQpc = SharedState->sampleQpc;
            R21ComputeAgeMs(sampleQpc, ageMs);

            for (int attempt = 0; attempt < 4; ++attempt)
            {
                const std::uint32_t before = SharedState->sequence;
                if (before & 1u)
                    continue;
                MemoryBarrier();
                const std::uint32_t pid = SharedState->hostPid;
                const std::uint32_t currentFlags = SharedState->flags;
                const std::uint32_t currentHeartbeat = SharedState->heartbeat;
                const std::int64_t currentSampleQpc = SharedState->sampleQpc;
                MemoryBarrier();
                const std::uint32_t after = SharedState->sequence;
                if (before != after || (after & 1u))
                    continue;

                hostPid = pid;
                flags = currentFlags;
                heartbeat = currentHeartbeat;
                sampleQpc = currentSampleQpc;

                if (!hostPid ||
                    (flags & (OutRunVR::HostAlive | OutRunVR::HostShouldRender)) !=
                        (OutRunVR::HostAlive | OutRunVR::HostShouldRender) ||
                    !R21ComputeAgeMs(sampleQpc, ageMs))
                    return false;

                return ageMs <= R21HostStaleMs;
            }
            return false;
        }

        void R21ApplyHostFailClosedAtPresent() noexcept
        {
            std::uint32_t hostPid = 0;
            std::uint32_t flags = 0;
            std::uint32_t heartbeat = 0;
            std::int64_t sampleQpc = 0;
            std::int64_t ageMs = INT64_MAX;
            const bool fresh = R21ReadHostFreshness(
                hostPid, flags, heartbeat, sampleQpc, ageMs);

            if (fresh)
            {
                R21LastHealthyHostPid = hostPid;
                const bool wasClosed = R21HostFailClosed ||
                    !R20StereoEligibilityGate.load(std::memory_order_acquire);
                R20StereoEligibilityGate.store(true, std::memory_order_release);
                if (wasClosed)
                {
                    // Recovery becomes eligible only for the following frame.
                    // Never carry a pre-stall seed across the transition.
                    R9StereoSeeded = false;
                    R9MonoSeeded = false;
                    R9MonoBackupGap = false;
                    R21HostFailClosed = false;
                    spdlog::info(
                        "VR R21: fresh stable host pose recovered pid={} heartbeat={}; game-local stereo gate reopened for next frame with a new baseline required",
                        hostPid, heartbeat);
                }
                return;
            }

            R20StereoEligibilityGate.store(false, std::memory_order_release);

            if (R9MonoSeeded && !R9MonoBackupGap)
            {
                R9StereoSeeded = false;
            }
            else
            {
                R9StereoSeeded = false;
                R9MonoSeeded = false;
            }

            if (!R21HostFailClosed)
            {
                R21HostFailClosed = true;
                spdlog::warn(
                    "VR R21 FAIL-CLOSED: OpenXR host pose stale/unavailable at Present (lastPid={} currentPid={} heartbeat={} flags=0x{:08x} ageMs={}); game-local stereo gate closed without modifying host-owned SharedPoseState",
                    R21LastHealthyHostPid, hostPid, heartbeat,
                    static_cast<unsigned>(flags),
                    ageMs == INT64_MAX ? -1 : ageMs);
            }
        }

        HRESULT __stdcall PresentDestR21(IDirect3DDevice9* device,
            const RECT* sourceRect, const RECT* destRect,
            HWND destWindowOverride, const RGNDATA* dirtyRegion)
        {
            if (IsGameDevice(device))
                R21ApplyHostFailClosedAtPresent();
            return R21PresentR9Hook.stdcall<HRESULT>(device, sourceRect,
                destRect, destWindowOverride, dirtyRegion);
        }

        DWORD WINAPI R21GameInstallThread(void*)
        {
            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                const std::uint32_t r9 =
                    R9InstallState.load(std::memory_order_acquire);
                const std::uint32_t r13 =
                    R13InstallState.load(std::memory_order_acquire);

                if (r9 == R9InstallFailed || r13 == R13InstallFailed)
                {
                    spdlog::error(
                        "VR R21: base R9/R13 transaction failed; host-death Present guard not installed");
                    return 0;
                }

                if (r9 == R9InstallReady && r13 == R13InstallReady)
                {
                    R21PresentR9Hook = safetyhook::create_inline(
                        reinterpret_cast<void*>(&PresentDestR9), PresentDestR21);
                    if (!R21PresentR9Hook)
                    {
                        spdlog::error(
                            "VR R21: failed to hook R9 Present for host-death fail-closed guard");
                        return 0;
                    }
                    R21PresentGuardReady.store(true, std::memory_order_release);
                    spdlog::info(
                        "VR R21 GAME: host-death mono fail-closed guard ACTIVE threshold={}ms; game-local eligibility gate only, host-owned seqlock is never written",
                        R21HostStaleMs);
                    return 0;
                }
                Sleep(25);
            }

            spdlog::warn(
                "VR R21: timed out waiting for R9/R13 renderer transaction; host-death guard not installed");
            return 0;
        }

        class VRHostDeathFailClosedR21Hook : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRHostDeathFailClosedR21";
            }

            bool validate() override { return true; }

            bool apply() override
            {
                HANDLE thread = CreateThread(
                    nullptr, 0, R21GameInstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    spdlog::error(
                        "VR R21: failed to create host-death guard installer thread: {}",
                        GetLastError());
                    return false;
                }
                CloseHandle(thread);
                return true;
            }

            static VRHostDeathFailClosedR21Hook instance;
        };

        VRHostDeathFailClosedR21Hook VRHostDeathFailClosedR21Hook::instance;
    }
}
