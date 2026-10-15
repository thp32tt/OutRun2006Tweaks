#pragma once

// Cross-process F10 recenter request channel shared by the 32-bit game hook and
// the 64-bit OpenXR host. This is intentionally independent of the v2/v3 pose
// ABI so a user-input control message cannot perturb render metadata layout.

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <Windows.h>
#include <cstdint>

namespace OutRunVR::RecenterIpc
{
    inline constexpr wchar_t MappingName[] =
        L"Local\\OutRun2006Tweaks.VR.Recenter.v1";
    inline constexpr std::uint32_t Magic = 0x5243564Fu; // 'OVCR'
    inline constexpr std::uint32_t Version = 1;

    struct State
    {
        std::uint32_t magic = 0;
        std::uint32_t version = 0;
        std::uint32_t structSize = 0;
        volatile LONG requestId = 0;
        volatile LONG receivedId = 0;
        volatile LONG appliedId = 0;
        volatile LONG requesterPid = 0;
    };
    static_assert(sizeof(State) == 28);

    class Channel
    {
    public:
        bool Ensure() noexcept
        {
            if (state_)
                return state_->magic == Magic && state_->version == Version &&
                    state_->structSize == sizeof(State);

            HANDLE mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr,
                PAGE_READWRITE, 0, static_cast<DWORD>(sizeof(State)), MappingName);
            if (!mapping)
                return false;
            const bool created = GetLastError() != ERROR_ALREADY_EXISTS;

            auto* state = static_cast<State*>(MapViewOfFile(mapping,
                FILE_MAP_ALL_ACCESS, 0, 0, sizeof(State)));
            if (!state)
            {
                CloseHandle(mapping);
                return false;
            }

            if (created)
            {
                ZeroMemory(state, sizeof(State));
                state->magic = Magic;
                state->version = Version;
                state->structSize = sizeof(State);
                MemoryBarrier();
            }
            else if (state->magic != Magic || state->version != Version ||
                state->structSize != sizeof(State))
            {
                UnmapViewOfFile(state);
                CloseHandle(mapping);
                return false;
            }

            mapping_ = mapping;
            state_ = state;
            return true;
        }

        LONG Publish() noexcept
        {
            if (!Ensure())
                return 0;

            // requesterPid=0 is a publication sentinel. It closes the window
            // where a restarting game could expose the previous requestId with
            // the replacement process PID, causing the host to accept a mixed
            // request identity and then process the new F10 a second time.
            InterlockedExchange(&state_->requesterPid, 0);
            MemoryBarrier();
            const LONG requestId = InterlockedIncrement(&state_->requestId);
            MemoryBarrier();
            InterlockedExchange(&state_->requesterPid,
                static_cast<LONG>(GetCurrentProcessId()));
            return requestId;
        }

        bool Pending(LONG& requestId, DWORD& requesterPid) noexcept
        {
            requestId = 0;
            requesterPid = 0;
            if (!Ensure())
                return false;
            const LONG requested = InterlockedCompareExchange(
                &state_->requestId, 0, 0);
            const LONG received = InterlockedCompareExchange(
                &state_->receivedId, 0, 0);
            if (requested == 0 || requested == received)
                return false;
            const DWORD publishedPid = static_cast<DWORD>(
                InterlockedCompareExchange(&state_->requesterPid, 0, 0));
            if (publishedPid == 0)
                return false;

            // Pair requestId with requesterPid from one stable publication.
            // A replacement game can begin publishing after the first requestId
            // read; reject that mixed snapshot if the sequence changed while we
            // sampled requesterPid.
            const LONG requestedAfter = InterlockedCompareExchange(
                &state_->requestId, 0, 0);
            if (requestedAfter != requested)
                return false;

            // A new publisher can clear requesterPid to zero after the first
            // PID sample but before advancing requestId. Observe the sentinel
            // again before handing the snapshot to OpenXR. A changed PID also
            // rejects a cross-process/reconnect mixed publication.
            const DWORD publishedPidAfter = static_cast<DWORD>(
                InterlockedCompareExchange(&state_->requesterPid, 0, 0));
            if (publishedPidAfter == 0 || publishedPidAfter != publishedPid)
                return false;

            requestId = requested;
            requesterPid = publishedPid;
            return true;
        }

        void MarkReceived(LONG requestId) noexcept
        {
            if (requestId != 0 && Ensure())
                InterlockedExchange(&state_->receivedId, requestId);
        }

        bool RequeueReceived(LONG requestId) noexcept
        {
            if (requestId == 0 || !Ensure())
                return false;

            const LONG requested = InterlockedCompareExchange(
                &state_->requestId, 0, 0);
            if (requested != requestId)
                return false;

            return InterlockedCompareExchange(
                &state_->receivedId, 0, requestId) == requestId;
        }

        void MarkApplied(LONG requestId) noexcept
        {
            if (requestId != 0 && Ensure())
                InterlockedExchange(&state_->appliedId, requestId);
        }

        LONG AppliedId() noexcept
        {
            return Ensure() ?
                InterlockedCompareExchange(&state_->appliedId, 0, 0) : 0;
        }

    private:
        HANDLE mapping_ = nullptr;
        State* state_ = nullptr;
    };

    inline Channel& SharedChannel() noexcept
    {
        static Channel channel;
        return channel;
    }
}
