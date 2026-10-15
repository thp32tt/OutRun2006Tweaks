#pragma once

#include "vr/ipc/protocol_v3.hpp"
#include "vr/ipc/win32_channel.hpp"

namespace OutRunVR::IpcV3
{
    class HostStateReader
    {
    public:
        bool Read(HostState& out) noexcept
        {
            // Never publish a partially copied seqlock snapshot, an invalid
            // protocol header, or a previous successful pose on failure.
            // A default HostState has structSize=0 and is not wire-valid.
            out = HostState{};
            if (!mapping_.EnsureOpen(HostStateName))
                return false;

            HostState snapshot{};
            if (!Ipc::StableRead(mapping_.Get(), snapshot) ||
                !HeaderValid(snapshot))
                return false;
            out = snapshot;
            return true;
        }

        void Reset() noexcept
        {
            mapping_.Reset();
        }

        bool IsOpen() const noexcept
        {
            return mapping_.IsOpen();
        }

        static bool HeaderValid(const HostState& state) noexcept
        {
            return state.magic == HostMagic &&
                state.version == ProtocolVersion &&
                state.structSize == sizeof(HostState);
        }

    private:
        Ipc::ReadOnlyMapping<HostState> mapping_{};
    };
}
