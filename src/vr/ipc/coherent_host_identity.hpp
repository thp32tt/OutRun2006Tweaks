#pragma once
// Snapshot the DirectGPU host process and adapter as ONE SharedPoseState
// generation. Portable barrier injection permits deterministic racing-writer
// smoke tests; the Windows D3D9 reader supplies MemoryBarrier.
#include "protocol.hpp"
#include <cstdint>

namespace OutRunVR::HostIdentity
{
    struct Snapshot
    {
        std::uint32_t hostPid{};
        std::uint32_t adapterLuidLow{};
        std::uint32_t adapterLuidHigh{};
    };

    template <typename Barrier>
    inline bool TryRead(const SharedPoseState* shared, Snapshot& out,
        Barrier&& barrier) noexcept
    {
        out = {};
        if (!shared)
            return false;

        for (unsigned attempt = 0; attempt < 4u; ++attempt)
        {
            const std::uint32_t before = shared->sequence;
            if (before & 1u)
                continue;
            barrier();
            const std::uint32_t magic = shared->magic;
            const std::uint32_t protocol = shared->protocolVersion;
            const std::uint32_t size = shared->structSize;
            const std::uint32_t pid = shared->hostPid;
            const std::uint32_t flags = shared->flags;
            const std::uint32_t low = shared->hostAdapterLuidLow;
            const std::uint32_t high = shared->hostAdapterLuidHigh;
            barrier();
            const std::uint32_t after = shared->sequence;
            if (before != after || (after & 1u))
                continue;

            // Do not admit stale host ownership or an uninitialized adapter.
            // Successful interop probing alone cannot validate a new writer.
            if (magic != SharedMagic || protocol != SharedProtocolVersion ||
                size != sizeof(SharedPoseState) || pid == 0 ||
                (flags & (HostAlive | HostAdapterLuidValid)) !=
                    (HostAlive | HostAdapterLuidValid))
                return false;
            out = {pid, low, high};
            return true;
        }
        return false;
    }
}
