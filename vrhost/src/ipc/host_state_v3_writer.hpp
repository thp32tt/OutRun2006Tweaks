#pragma once

#include <Windows.h>

#include <cstdint>
#include <cstring>
#include <stdexcept>

#include "vr/ipc/protocol_v3.hpp"
#include "vr/ipc/win32_channel.hpp"

namespace OutRunVR::Host
{
    class HostStateV3Writer
    {
    public:
        HostStateV3Writer(std::uint32_t adapterLuidLow, std::int32_t adapterLuidHigh)
            : adapterLuidLow_(adapterLuidLow), adapterLuidHigh_(adapterLuidHigh)
        {
            mapping_ = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,
                static_cast<DWORD>(sizeof(IpcV3::HostState)), IpcV3::HostStateName);
            if (!mapping_)
                throw std::runtime_error("CreateFileMappingW HostState.v3 failed");

            const bool existed = GetLastError() == ERROR_ALREADY_EXISTS;
            state_ = static_cast<IpcV3::HostState*>(MapViewOfFile(
                mapping_, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(IpcV3::HostState)));
            if (!state_)
            {
                CloseHandle(mapping_);
                mapping_ = nullptr;
                throw std::runtime_error("MapViewOfFile HostState.v3 failed");
            }

            if (!existed)
            {
                std::memset(state_, 0, sizeof(*state_));
                state_->version = IpcV3::ProtocolVersion;
                state_->structSize = sizeof(*state_);
                MemoryBarrier();
                state_->magic = IpcV3::HostMagic;
            }
            else
            {
                for (int i = 0; i < 200 && !HeaderValid(*state_); ++i)
                    Sleep(10);
                if (!HeaderValid(*state_))
                    throw std::runtime_error("existing HostState.v3 mapping is not ready");
            }

            AcquireOwnership();
            referenceSpaceGeneration_ = state_->referenceSpaceGeneration + 1u;
            if (referenceSpaceGeneration_ == 0)
                referenceSpaceGeneration_ = 1;

            IpcV3::HostState initial{};
            IpcV3::InitializeWireState(initial);
            initial.hostPid = GetCurrentProcessId();
            initial.referenceSpaceGeneration = referenceSpaceGeneration_;
            initial.adapterLuidLow = adapterLuidLow_;
            initial.adapterLuidHigh = adapterLuidHigh_;
            Publish(initial);
        }

        HostStateV3Writer(const HostStateV3Writer&) = delete;
        HostStateV3Writer& operator=(const HostStateV3Writer&) = delete;

        ~HostStateV3Writer()
        {
            if (state_)
            {
                if (owns_ && state_->hostPid == GetCurrentProcessId())
                {
                    const std::uint32_t odd = Ipc::BeginSeqlockWrite(state_->sequence);
                    state_->sequence = odd;
                    state_->flags = 0;
                    state_->hostPid = 0;
                    Ipc::EndSeqlockWrite(state_->sequence);
                }
                UnmapViewOfFile(state_);
                state_ = nullptr;
            }
            if (mapping_)
            {
                CloseHandle(mapping_);
                mapping_ = nullptr;
            }
        }

        void ReferenceSpaceChanged() noexcept
        {
            if (++referenceSpaceGeneration_ == 0)
                referenceSpaceGeneration_ = 1;
        }

        std::uint32_t ReferenceSpaceGeneration() const noexcept
        {
            return referenceSpaceGeneration_;
        }

        std::uint32_t Publish(IpcV3::HostState next) noexcept
        {
            if (!state_ || !owns_)
                return 0;

            next.magic = IpcV3::HostMagic;
            next.version = IpcV3::ProtocolVersion;
            next.structSize = sizeof(IpcV3::HostState);
            next.hostPid = GetCurrentProcessId();
            next.referenceSpaceGeneration = referenceSpaceGeneration_;
            next.adapterLuidLow = adapterLuidLow_;
            next.adapterLuidHigh = adapterLuidHigh_;

            const std::uint32_t odd = Ipc::BeginSeqlockWrite(state_->sequence);
            next.sequence = odd;
            std::memcpy(state_, &next, sizeof(next));
            MemoryBarrier();
            return Ipc::EndSeqlockWrite(state_->sequence);
        }

    private:
        static bool HeaderValid(const IpcV3::HostState& state) noexcept
        {
            return state.magic == IpcV3::HostMagic &&
                state.version == IpcV3::ProtocolVersion &&
                state.structSize == sizeof(IpcV3::HostState);
        }

        static bool ProcessAlive(DWORD pid) noexcept
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

        void AcquireOwnership()
        {
            const LONG self = static_cast<LONG>(GetCurrentProcessId());
            for (int i = 0; i < 100; ++i)
            {
                const LONG observed = static_cast<LONG>(state_->hostPid);
                if (observed == self)
                {
                    owns_ = true;
                    return;
                }
                if (observed != 0 && ProcessAlive(static_cast<DWORD>(observed)))
                    throw std::runtime_error("another outrun-vr-host owns HostState.v3");
                if (InterlockedCompareExchange(
                    reinterpret_cast<volatile LONG*>(&state_->hostPid), self, observed) == observed)
                {
                    owns_ = true;
                    return;
                }
                Sleep(1);
            }
            throw std::runtime_error("failed to acquire HostState.v3 ownership");
        }

        HANDLE mapping_ = nullptr;
        IpcV3::HostState* state_ = nullptr;
        bool owns_ = false;
        std::uint32_t referenceSpaceGeneration_ = 1;
        std::uint32_t adapterLuidLow_ = 0;
        std::int32_t adapterLuidHigh_ = 0;
    };
}
